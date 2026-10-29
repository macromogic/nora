"""Preview-first, version-guarded rename/reparent of one existing collection."""
import copy
import json
import re
import urllib.error
import urllib.request
import uuid

from . import zotero as z
from . import zotero_scope
from .zotero_audit import _atomic, _locked, collection_paths, display, now


def add_parser(sub):
    parser = sub.add_parser('collection', help='preview or apply an existing collection rename/move')
    commands = parser.add_subparsers(dest='collection_command')
    from .zotero_collection_members import add_parser as add_members_parser
    add_members_parser(commands)
    delete = commands.add_parser('delete-empty', help='delete only an empty leaf collection')
    delete.add_argument('key')
    delete.add_argument('--apply', action='store_true')
    delete.add_argument('--expect-library-version', type=int)
    edit = commands.add_parser('edit')
    edit.add_argument('key', help='existing collection key')
    edit.add_argument('--name', help='new name (one path component)')
    edit.add_argument('--parent', help='existing parent collection key, or root')
    edit.add_argument('--apply', action='store_true', help='write the previewed change to Zotero')
    edit.add_argument('--expect-library-version', type=int, help='required with --apply; version from preview')


def plan(config, collections, version, key, name=None, parent=None):
    if not re.fullmatch(r'[A-Z0-9]{8}', key):
        raise z.ZoteroError('Invalid collection key.')
    by_key = {c['key']: c for c in collections}
    if key not in by_key:
        raise z.ZoteroError('Collection not found.')
    if name is None and parent is None:
        raise z.ZoteroError('Specify --name and/or --parent.')
    paths, warnings = collection_paths(collections)
    if warnings:
        raise z.ZoteroError('Collection hierarchy is invalid; resolve it before editing.')
    before = {k: by_key[key]['data'].get(k, False) for k in ('name', 'parentCollection')}
    before['parentCollection'] = before['parentCollection'] or False
    after = dict(before)
    if name is not None:
        if not name.strip() or name != name.strip() or '/' in name or any(ord(c) < 32 or ord(c) == 127 for c in name):
            raise z.ZoteroError('Name must be a nonempty path component without surrounding whitespace or controls.')
        after['name'] = name
    if parent is not None:
        if parent != 'root' and parent not in by_key:
            raise z.ZoteroError('Parent collection not found; use a key or root.')
        after['parentCollection'] = False if parent == 'root' else parent
    if any(c['key'] != key and c['data'].get('name') == after['name']
           and (c['data'].get('parentCollection') or False) == after['parentCollection'] for c in collections):
        raise z.ZoteroError('A collection with this name already exists under the destination parent.')
    updated = copy.deepcopy(collections)
    next(c for c in updated if c['key'] == key)['data'].update(after)
    new_paths, warnings = collection_paths(updated)
    if warnings:
        raise z.ZoteroError('Move would create an invalid collection hierarchy (possibly a cycle).')
    for tree in (collections, updated):
        scoped = zotero_scope.scope({'collections': tree, 'items': []}, config)
        if key in scoped['_excluded_collections']:
            raise z.ZoteroError('Source or destination is excluded by the collection ignore policy.')
    return dict(library=config.identity, library_version=version, key=key,
                object_version=by_key[key]['version'], before=before, after=after,
                old_path=paths[key], new_path=new_paths[key])


def write(config, change):
    """Single-object partial POST; library precondition also guards the parent tree."""
    payload = dict(key=change['key'], version=change['object_version'], **change['after'])
    post(config, 'collections', [payload], change['library_version'])


def post(config, resource, payloads, library_version):
    if resource not in {'items', 'collections'} or not 1 <= len(payloads) <= 50:
        raise z.ZoteroError('Invalid write batch.')
    if not config.api_key:
        raise z.ZoteroError('Collection writes require an API key with library write access.')
    request = urllib.request.Request(
        z.Client(config).base + '/' + resource, method='POST',
        data=json.dumps(payloads).encode('utf-8'),
        headers={'Zotero-API-Key': config.api_key, 'Zotero-API-Version': '3',
                 'Content-Type': 'application/json', 'Accept': 'application/json',
                 'If-Unmodified-Since-Version': str(library_version)})
    try:
        with urllib.request.build_opener(z._NoRedirect()).open(request, timeout=15) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        message = {403: 'Write access denied.', 401: 'Authentication failed.',
                   409: 'Library locked.', 412: 'Version conflict; obtain a new preview.',
                   429: 'Rate limited; stop and retry later.'}.get(exc.code, 'Write request failed.')
        raise z.ZoteroError(f'Zotero HTTP {exc.code}: {message} Inspect remote state before retrying; no automatic retries.') from None
    except (OSError, urllib.error.URLError, ValueError):
        raise z.ZoteroError('Write outcome unknown (network/TLS/timeout). Inspect remote state and journal before retrying.') from None
    try:
        result = json.loads(body)
        if (not isinstance(result, dict) or result.get('failed')
                or any(not (result.get('successful', {}).get(str(n), {}).get('key') == payload['key']
                            or result.get('unchanged', {}).get(str(n)) == payload['key'])
                       for n, payload in enumerate(payloads))):
            raise ValueError()
    except (ValueError, TypeError, AttributeError, UnicodeError):
        raise z.ZoteroError('Write response did not confirm success. Inspect remote state and journal before retrying.') from None


def run(config, args):
    if args.collection_command == 'delete-empty':
        from .zotero_collection_delete import run as delete_empty
        return delete_empty(config, args)
    if args.collection_command in {'create', 'add-items'}:
        from .zotero_collection_members import run as run_members
        return run_members(config, args)
    if not args.collection_command:
        print('Use: nora zotero collection edit KEY --name NAME --parent KEY|root')
        return 0
    if args.apply and args.expect_library_version is None:
        raise z.ZoteroError('--apply requires --expect-library-version from a reviewed preview.')
    client = z.Client(config)
    collections, version = client.all('collections')
    change = plan(config, collections, version, args.key, args.name, args.parent)
    print(f"Library: {config.identity}; version: {version}; collection: {change['key']}")
    print(f"{display(change['old_path'])} -> {display(change['new_path'])}")
    if args.expect_library_version is not None and version != args.expect_library_version:
        raise z.ZoteroError('Library version changed since preview; no write attempted. Review a fresh preview.')
    if change['before'] == change['after']:
        print('Already matches; no write needed.')
        return 0
    if not args.apply:
        print(f'Preview only. Apply with the same arguments plus --apply --expect-library-version {version}.')
        return 0
    with _locked(config):
        directory = config.state_dir / 'collection_operations'
        directory.mkdir(exist_ok=True, mode=0o700)
        path = directory / (uuid.uuid4().hex + '.json')
        journal = dict(change, status='attempting', started_at=now())
        _atomic(path, json.dumps(journal, ensure_ascii=False, indent=2) + '\n')
        print(f'Operation journal: {path}')
        try:
            write(config, change)
            # Refresh collections only; do not fetch paper text or overwrite audit snapshots.
            verified, new_version = client.all('collections')
            remote = next((c for c in verified if c['key'] == change['key']), None)
            if remote is None or any((remote['data'].get(k) or False) != v for k, v in change['after'].items()):
                raise z.ZoteroError('Write returned success but read-back differs; inspect journal and remote state.')
            journal.update(status='verified', finished_at=now(), verified_library_version=new_version,
                           verified_object_version=remote['version'])
            _atomic(path, json.dumps(journal, ensure_ascii=False, indent=2) + '\n')
        except (z.ZoteroError, OSError, UnicodeError) as exc:
            journal.update(status='needs_review', finished_at=now())
            try:
                _atomic(path, json.dumps(journal, ensure_ascii=False, indent=2) + '\n')
            except OSError:
                pass
            reason = str(exc) if isinstance(exc, z.ZoteroError) else 'Local journal access failed.'
            raise z.ZoteroError(reason + ' Collection operation not fully verified; it may have reached Zotero. '
                                f'Inspect {path} and remote state before retrying.') from None
    print(f"Applied and verified: {display(change['new_path'])}; collection key preserved.")
    print('Item memberships, tags, and other collection records were not written. Existing audit snapshots are now stale.')
    return 0
