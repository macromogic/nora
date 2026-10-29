"""Persistent per-library exclusions, shared by audit/review/project linking."""
import json
import re

from .zotero import ZoteroError


def ignored_collections(config):
    path = config.state_dir / 'ignored_collections.json'
    if not path.exists():
        return set()
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, OSError, UnicodeError):
        raise ZoteroError('Cannot read collection exclusions; refusing to process the library.') from None
    if (not isinstance(value, dict) or set(value) != {'library', 'collections'}
            or value['library'] != config.identity or not isinstance(value['collections'], list)
            or any(not isinstance(k, str) or not re.fullmatch(r'[A-Z0-9]{8}', k) for k in value['collections'])):
        raise ZoteroError('Invalid collection exclusions; refusing to process the library.')
    return set(value['collections'])


def change(config, action, key):
    from .zotero_audit import _locked, _atomic
    if not re.fullmatch(r'[A-Z0-9]{8}', key):
        raise ZoteroError('Expected an eight-character collection key, not a name or path.')
    with _locked(config):
        keys = ignored_collections(config)
        if action == 'add':
            keys.add(key)
        else:
            keys.discard(key)
        _atomic(config.state_dir / 'ignored_collections.json',
                json.dumps({'library': config.identity, 'collections': sorted(keys)}, indent=2) + '\n')


def scope(snapshot, config, *, include_trashed=False):
    """Never mutate the full snapshot. Any excluded membership takes precedence."""
    collections = ignored_collections(config)
    collections.update(c['key'] for c in snapshot['collections']
                       if c['data'].get('name', '').startswith('_')
                       and c['data']['name'] != '_inbox')
    while True:
        children = {c['key'] for c in snapshot['collections']
                    if c['data'].get('parentCollection') in collections}
        if children <= collections:
            break
        collections |= children
    items = {i['key'] for i in snapshot['items']
             if (i['data'].get('deleted') and not include_trashed) or collections.intersection(i['data'].get('collections', []))}
    while True:
        children = {i['key'] for i in snapshot['items'] if i['data'].get('parentItem') in items}
        if children <= items:
            break
        items |= children
    filtered = dict(snapshot,
                    collections=[c for c in snapshot['collections'] if c['key'] not in collections],
                    items=[i for i in snapshot['items'] if i['key'] not in items])
    filtered['_excluded_items'] = sorted(items)
    filtered['_excluded_collections'] = sorted(collections)
    return filtered


def visible_issues(issues, snapshot):
    excluded = set(snapshot.get('_excluded_items', [])) | set(snapshot.get('_excluded_collections', []))
    return [i for i in issues if not excluded.intersection(i['item_keys'])]
