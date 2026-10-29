"""Detect known stale snapshots from durable write journals, including older CLI writes."""
import json
from datetime import datetime

from .zotero import ZoteroError


def reason(config, snapshot):
    try:
        fetched = datetime.fromisoformat(snapshot['fetched_at'].replace('Z', '+00:00'))
        for directory in ('collection_operations', 'item_operations'):
            for path in (config.state_dir / directory).glob('*.json'):
                journal = json.loads(path.read_text(encoding='utf-8'))
                if journal['library'] != config.identity:
                    raise ValueError()
                status = journal['status']
                if status == 'verified':
                    version = journal['verified_library_version']
                    if type(version) is not int:
                        raise ValueError()
                    if version > snapshot['version']:
                        return f'known library version {version} exceeds snapshot version {snapshot["version"]}'
                elif status == 'attempting':
                    return 'a write has no recorded outcome; inspect operation journals and refresh after it finishes'
                elif status == 'needs_review':
                    if datetime.fromisoformat(journal['finished_at'].replace('Z', '+00:00')) >= fetched:
                        return 'a write outcome is uncertain and newer than this snapshot'
                else:
                    raise ValueError()
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return 'snapshot freshness cannot be established from operation journals'
    return None


def check(config, snapshot, *, applying=False):
    problem = reason(config, snapshot)
    if problem:
        message = f'Stale or unverified snapshot: {problem}. Run nora zotero audit --write online.'
        if applying:
            raise ZoteroError(message + ' Nothing applied.')
        print('WARNING: ' + message)
