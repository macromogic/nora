"""Create collections and classify items, optionally finishing their inbox triage."""
import json
import re
import secrets
import urllib.parse
import uuid

from . import zotero as z, zotero_scope
from .zotero_audit import _atomic, _locked, collection_paths, display, now


def add_parser(commands):
    create = commands.add_parser('create', help='preview/create one collection')
    create.add_argument('--name', required=True)
    create.add_argument('--parent', default='root', help='existing parent key or root')
    members = commands.add_parser('add-items', help='preview/append membership without removing existing memberships')
    inbox_mode = members.add_mutually_exclusive_group()
    inbox_mode.add_argument('--finish-inbox', action='store_true', help='remove inbox memberships after assigning a topic')
    inbox_mode.add_argument('--flatten-inbox', action='store_true', help='move inbox descendants to the top-level _inbox destination')
    members.add_argument('key', help='existing destination collection key')
    members.add_argument('--item', action='append', required=True, help='bibliographic item key; repeat up to 50 times')
    for child in (create, members):
        child.add_argument('--apply', action='store_true')
        child.add_argument('--expect-library-version', type=int)


def new_key():
    return ''.join(secrets.choice('23456789ABCDEFGHIJKLMNPQRSTUVWXYZ') for _ in range(8))


def selected_items(config, keys, version):
    keys = sorted(set(keys))
    if not 1 <= len(keys) <= 50 or any(not re.fullmatch(r'[A-Z0-9]{8}', k) for k in keys):
        raise z.ZoteroError('Select 1 to 50 valid item keys.')
    query = urllib.parse.urlencode({'itemKey': ','.join(keys), 'format': 'json', 'limit': 100})
    items, headers = z._get(z.Client(config).base + '/items?' + query, config.api_key)
    if z._header_int(headers, 'last-modified-version') != version:
        raise z.ZoteroError('Library changed during preview/verification; inspect current state.')
    z.validate_objects(items, 'items')
    if {i['key'] for i in items} != set(keys) or any(i['version'] > version for i in items):
        raise z.ZoteroError('Some selected items are missing or invalid; no membership plan accepted.')
    return items


def membership_plan(config, collections, items, destination, finish_inbox=False, flatten_inbox=False):
    paths, warnings = collection_paths(collections)
    if warnings or destination not in paths:
        raise z.ZoteroError('Invalid collection tree or destination.')
    scoped = zotero_scope.scope({'collections': collections, 'items': items}, config)
    if destination in scoped['_excluded_collections'] or scoped['_excluded_items']:
        raise z.ZoteroError('Selection includes an ignored collection or item; no changes planned.')
    inbox = {c['key'] for c in collections if c['data'].get('name') == '_inbox'}
    while True:
        children = {c['key'] for c in collections if c['data'].get('parentCollection') in inbox}
        if children <= inbox:
            break
        inbox |= children
    if flatten_inbox and (finish_inbox or paths[destination] != '_inbox'):
        raise z.ZoteroError('Flattening requires the top-level _inbox destination and cannot finish inbox.')
    if finish_inbox and destination in inbox:
        raise z.ZoteroError('Finishing inbox requires a destination outside the inbox subtree.')
    changes = []
    for item in sorted(items, key=lambda i: i['key']):
        data = item['data']
        if data['itemType'] in {'attachment', 'note', 'annotation'} or data.get('parentItem'):
            raise z.ZoteroError('Only top-level bibliographic items can be added.')
        before = list(data.get('collections', []))
        after = before + ([destination] if destination not in before else [])
        if finish_inbox:
            after = [key for key in after if key not in inbox]
        if flatten_inbox:
            after = [key for key in after if key == destination or not paths.get(key, '').startswith('_inbox/')]
        if after != before:
            changes.append(dict(key=item['key'], version=item['version'], title=data.get('title', ''),
                                before=before, after=after))
    return changes


def create_plan(config, collections, version, name, parent):
    from .zotero_collections import plan
    parent = False if parent == 'root' else parent
    paths, warnings = collection_paths(collections)
    if warnings:
        raise z.ZoteroError('Invalid collection tree.')
    existing = [c for c in collections if c['data']['name'] == name
                and (c['data'].get('parentCollection') or False) == parent]
    if len(existing) > 1:
        raise z.ZoteroError('Multiple collections have this name; choose an existing key explicitly.')
    if existing:
        key = existing[0]['key']
        plan(config, collections, version, key, name=name, parent=parent or 'root')
        return key, None
    key = new_key()
    while key in paths:
        key = new_key()
    temporary = collections + [dict(key=key, version=version, data=dict(name=name, parentCollection=False))]
    change = plan(config, temporary, version, key, name=name, parent=parent or 'root')
    return key, dict(key=key, **change['after'])


def run(config, args):
    from .zotero_collections import post
    if args.apply and args.expect_library_version is None:
        raise z.ZoteroError('--apply requires --expect-library-version from a reviewed preview.')
    client = z.Client(config)
    collections, version = client.all('collections')
    if args.expect_library_version is not None and args.expect_library_version != version:
        raise z.ZoteroError('Library changed since preview; no write attempted.')
    print(f'Library: {config.identity}; version: {version}')
    creating = args.collection_command == 'create'
    if creating:
        key, payload = create_plan(config, collections, version, args.name, args.parent)
        if payload is None:
            print(f'Already exists: {display(args.name)} [{key}]; no write needed.')
            return 0
        resource, payloads = 'collections', [payload]
        changes = [dict(key=key, before=None, after=payload)]
        print(f'Create collection: {display(args.name)}; parent: {display(args.parent)}')
    else:
        key = args.key
        items = selected_items(config, args.item, version)
        changes = membership_plan(config, collections, items, key, getattr(args, 'finish_inbox', False), getattr(args, 'flatten_inbox', False))
        resource = 'items'
        payloads = [dict(key=i['key'], version=i['version'], collections=i['after']) for i in changes]
        for change in changes:
            removed = sorted(set(change['before']) - set(change['after']))
            suffix = f"; remove inbox memberships: {', '.join(removed)}" if removed else "; existing memberships retained"
            print(f"Classify {change['key']} under {key}: {display(change['title'])}{suffix}")
        if not changes:
            print('All memberships already match the requested classification; no write needed.')
            return 0
    if not args.apply:
        print(f'Preview only. Add --apply --expect-library-version {version} to execute.')
        return 0
    with _locked(config):
        directory = config.state_dir / 'collection_operations'
        directory.mkdir(exist_ok=True, mode=0o700)
        path = directory / (uuid.uuid4().hex + '.json')
        journal = dict(library=config.identity, library_version=version, operation=args.collection_command,
                       collection_key=key, changes=changes, status='attempting', started_at=now())
        def save():
            _atomic(path, json.dumps(journal, ensure_ascii=False, indent=2) + '\n')
        save()
        print(f'Operation journal: {path}')
        try:
            post(config, resource, payloads, version)
            verified_collections, new_version = client.all('collections')
            if creating:
                remote = next((c for c in verified_collections if c['key'] == key), None)
                if remote is None or any((remote['data'].get(k) or False) != v for k, v in payload.items() if k != 'key'):
                    raise z.ZoteroError('Created collection differs on read-back.')
            else:
                remote = {i['key']: i for i in selected_items(config, [i['key'] for i in changes], new_version)}
                if any(set(remote[i['key']]['data'].get('collections', [])) != set(i['after']) for i in changes):
                    raise z.ZoteroError('Memberships differ on read-back.')
            journal.update(status='verified', verified_library_version=new_version, finished_at=now())
            save()
        except (z.ZoteroError, OSError, UnicodeError) as exc:
            journal.update(status='needs_review', finished_at=now())
            try:
                save()
            except OSError:
                pass
            reason = str(exc) if isinstance(exc, z.ZoteroError) else 'Local journal access failed.'
            raise z.ZoteroError(reason + f' Remote changes may be partial or complete. Inspect {path} before retrying.') from None
    print(f'Applied and verified: {args.collection_command}; collection {key}; objects changed: {len(changes)}; library version: {new_version}.')
    print('Existing audit snapshots are now stale. No automatic retries or rollback.')
    return 0
