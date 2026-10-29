"""Delete only verified empty leaf collections, with library-version protection."""
import json
import re
import urllib.request
import uuid

from . import zotero as z, zotero_scope
from .zotero_audit import _atomic, _locked, display, now


def empty_collection(config, collections, key, version):
    if not re.fullmatch(r'[A-Z0-9]{8}', key):
        raise z.ZoteroError('Invalid collection key.')
    target = next((c for c in collections if c['key'] == key), None)
    if target is None:
        raise z.ZoteroError('Collection not found.')
    if target['data'].get('name') == '_inbox':
        raise z.ZoteroError('Keep the inbox root.')
    if key in zotero_scope.scope({'collections':collections,'items':[]}, config)['_excluded_collections']:
        raise z.ZoteroError('Collection is ignored.')
    if any(c['data'].get('parentCollection') == key for c in collections):
        raise z.ZoteroError('Collection still has children; only empty leaves can be deleted.')
    items, headers = z._get(z.Client(config).base + f'/collections/{key}/items?includeTrashed=1&limit=1&format=json', config.api_key)
    if z._header_int(headers, 'last-modified-version') != version:
        raise z.ZoteroError('Library changed during empty check.')
    if items or z._header_int(headers, 'total-results') != 0:
        raise z.ZoteroError('Collection is not empty (including ignored or trashed members).')
    return target


def run(config, args):
    if args.apply and args.expect_library_version is None:
        raise z.ZoteroError('--apply requires --expect-library-version.')
    client = z.Client(config)
    collections, version = client.all('collections')
    if args.expect_library_version is not None and args.expect_library_version != version:
        raise z.ZoteroError('Library changed since preview.')
    target = empty_collection(config, collections, args.key, version)
    print(f"Library: {config.identity}; version: {version}; delete empty collection {args.key}: {display(target['data']['name'])}")
    if not args.apply:
        print(f'Preview only. Add --apply --expect-library-version {version}.')
        return 0
    if not config.api_key:
        raise z.ZoteroError('Write permission required.')
    with _locked(config):
        directory = config.state_dir / 'collection_operations'
        directory.mkdir(exist_ok=True, mode=0o700)
        path = directory / (uuid.uuid4().hex + '.json')
        journal = dict(library=config.identity, library_version=version, operation='delete-empty',
                       before=target, status='attempting', started_at=now())
        def save():
            _atomic(path, json.dumps(journal, ensure_ascii=False, indent=2)+'\n')
        save()
        print(f'Operation journal: {path}')
        try:
            # Multi-object DELETE with a library precondition closes the empty-check race.
            request = urllib.request.Request(client.base + '/collections?collectionKey=' + args.key, method='DELETE',
                headers={'Zotero-API-Key':config.api_key,'Zotero-API-Version':'3',
                         'If-Unmodified-Since-Version':str(version)})
            with urllib.request.build_opener(z._NoRedirect()).open(request, timeout=15) as response:
                if response.status != 204:
                    raise z.ZoteroError('Unexpected deletion response.')
            after, new_version = client.all('collections')
            if any(c['key'] == args.key for c in after):
                raise z.ZoteroError('Deletion not confirmed.')
            journal.update(status='verified', verified_library_version=new_version, finished_at=now())
            save()
        except (OSError, z.ZoteroError, ValueError):
            journal.update(status='needs_review', finished_at=now())
            try:
                save()
            except OSError:
                pass
            raise z.ZoteroError(f'Deletion outcome unverified; inspect {path} and remote state before retrying.') from None
    print(f'Applied and verified: delete-empty; library version: {new_version}.')
    return 0
