"""Preview-first item trash operation; no permanent deletion."""
import json
import re
import uuid

from . import zotero as z, zotero_scope
from .zotero_audit import _atomic, _locked, display, now
from .zotero_collections import post


def add_parser(sub):
    parser = sub.add_parser('item', help='explicit item operations')
    commands = parser.add_subparsers(dest='item_command')
    trash = commands.add_parser('trash', help='move one bibliographic item to trash (recoverable)')
    trash.add_argument('key')
    trash.add_argument('--apply', action='store_true')
    trash.add_argument('--expect-library-version', type=int)


def read_item(config, key):
    if not re.fullmatch(r'[A-Z0-9]{8}', key):
        raise z.ZoteroError('Invalid item key.')
    items, headers = z._get(z.Client(config).base + f'/items?itemKey={key}&includeTrashed=1&format=json', config.api_key)
    z.validate_objects(items, 'items')
    if len(items) != 1 or items[0]['key'] != key:
        raise z.ZoteroError('Item not found.')
    version = z._header_int(headers, 'last-modified-version')
    if items[0]['version'] > version:
        raise z.ZoteroError('Invalid item version.')
    return items[0], version


def run(config, args):
    if not args.item_command:
        print('Use: nora zotero item trash KEY')
        return 0
    if args.apply and args.expect_library_version is None:
        raise z.ZoteroError('--apply requires --expect-library-version from a reviewed preview.')
    item, version = read_item(config, args.key)
    if args.expect_library_version is not None and version != args.expect_library_version:
        raise z.ZoteroError('Library changed since preview; no write attempted.')
    data = item['data']
    if data['itemType'] in {'note', 'annotation', 'attachment'} or data.get('parentItem'):
        raise z.ZoteroError('Select a top-level bibliographic item.')
    collections, _ = z.Client(config).all('collections', version)
    if zotero_scope.scope({'items': [item], 'collections': collections}, config, include_trashed=True)['_excluded_items']:
        raise z.ZoteroError('Item is excluded by collection policy.')
    print(f"Library: {config.identity}; version: {version}; item: {args.key}")
    print(f"Move to trash (recoverable): {display(data.get('title', ''))}")
    if data.get('deleted'):
        print('Already in trash; no write needed.')
        return 0
    if not args.apply:
        print(f'Preview only. Add --apply --expect-library-version {version} to execute.')
        return 0
    with _locked(config):
        directory = config.state_dir / 'item_operations'
        directory.mkdir(exist_ok=True, mode=0o700)
        path = directory / (uuid.uuid4().hex + '.json')
        journal = dict(library=config.identity, library_version=version, key=args.key,
                       item_version=item['version'], title=data.get('title', ''),
                       operation='trash', before={'deleted': data.get('deleted', 0)},
                       after={'deleted': 1}, status='attempting', started_at=now())
        def save():
            _atomic(path, json.dumps(journal, ensure_ascii=False, indent=2) + '\n')
        save()
        print(f'Operation journal: {path}')
        try:
            post(config, 'items', [dict(key=args.key, version=item['version'], deleted=1)], version)
            verified, new_version = read_item(config, args.key)
            if not verified['data'].get('deleted'):
                raise z.ZoteroError('Trash status not confirmed on read-back.')
            journal.update(status='verified', verified_library_version=new_version, finished_at=now())
            save()
        except (z.ZoteroError, OSError, UnicodeError) as exc:
            journal.update(status='needs_review', finished_at=now())
            try:
                save()
            except OSError:
                pass
            reason = str(exc) if isinstance(exc, z.ZoteroError) else 'Local journal access failed.'
            raise z.ZoteroError(reason + f' The item may already be in trash. Inspect {path} before retrying.') from None
    print(f'Applied and verified: item {args.key} is in trash; library version: {new_version}.')
    print('Restore using Zotero Trash if needed. Existing audit snapshots are stale.')
    return 0
