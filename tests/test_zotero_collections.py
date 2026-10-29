"""Offline regression coverage for narrow collection writes."""
import copy
import json
import sys
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))
from nora_cli import zotero as z, zotero_collections as c


@pytest.fixture
def config(tmp_path):
    return z.Config('123', api_key='test-only', data_dir=tmp_path)


@pytest.fixture
def tree():
    return [dict(key='SOURCE01', version=4, data=dict(name='old', parentCollection=False, relations={'x': 'y'})),
            dict(key='PARENT01', version=3, data=dict(name='oram', parentCollection=False)),
            dict(key='CHILD001', version=2, data=dict(name='child', parentCollection='SOURCE01'))]


def args(**overrides):
    result = dict(collection_command='edit', key='SOURCE01', name='new', parent='PARENT01',
                  apply=False, expect_library_version=None)
    result.update(overrides)
    return SimpleNamespace(**result)


def test_plan_preserves_source_and_builds_paths(config, tree):
    original = copy.deepcopy(tree)
    plan = c.plan(config, tree, 10, 'SOURCE01', 'new', 'PARENT01')
    assert plan['old_path'] == 'old' and plan['new_path'] == 'oram/new'
    assert plan['object_version'] == 4 and plan['library_version'] == 10
    assert tree == original


@pytest.mark.parametrize('overrides', [dict(parent='SOURCE01'), dict(parent='CHILD001'),
                                      dict(parent='MISSING1'), dict(name=''), dict(name='a/b'),
                                      dict(name=' x'), dict(name='x\n'), dict(name='_hidden')])
def test_invalid_moves_do_not_write(config, tree, overrides):
    kw = dict(name='new', parent='PARENT01')
    kw.update(overrides)
    with pytest.raises(z.ZoteroError):
        c.plan(config, tree, 10, 'SOURCE01', **kw)


def test_duplicate_and_ignored_parent(config, tree):
    tree.append(dict(key='OTHER001', version=2, data=dict(name='new', parentCollection='PARENT01')))
    with pytest.raises(z.ZoteroError, match='already exists'):
        c.plan(config, tree, 10, 'SOURCE01', 'new', 'PARENT01')
    tree[1]['data']['name'] = '_archive'
    with pytest.raises(z.ZoteroError, match='excluded'):
        c.plan(config, tree, 10, 'SOURCE01', 'different', 'PARENT01')


def test_preview_and_conflict_never_write(config, tree, monkeypatch):
    monkeypatch.setattr(z.Client, 'all', lambda self, resource: (tree, 10))
    monkeypatch.setattr(c, 'write', lambda *a: pytest.fail('unexpected write'))
    assert c.run(config, args()) == 0
    assert not config.state_dir.exists()
    with pytest.raises(z.ZoteroError, match='requires'):
        c.run(config, args(apply=True))
    with pytest.raises(z.ZoteroError, match='changed since preview'):
        c.run(config, args(apply=True, expect_library_version=9))


def test_apply_journal_verification_and_repeat(config, tree, monkeypatch):
    monkeypatch.setattr(z.Client, 'all', lambda self, resource: (tree, 10))
    calls = []
    def write(config, change):
        journals = list((config.state_dir / 'collection_operations').glob('*.json'))
        assert len(journals) == 1
        assert json.loads(journals[0].read_text())['status'] == 'attempting'
        calls.append(change)
        tree[0]['data'].update(change['after'])
        tree[0]['version'] = 10
    monkeypatch.setattr(c, 'write', write)
    assert c.run(config, args(apply=True, expect_library_version=10)) == 0
    journal = json.loads(next((config.state_dir / 'collection_operations').glob('*.json')).read_text())
    assert journal['status'] == 'verified' and journal['before']['name'] == 'old'
    assert tree[0]['data']['relations'] == {'x': 'y'}
    assert c.run(config, args(apply=True, expect_library_version=10)) == 0
    assert len(calls) == 1


def test_uncertain_write_keeps_journal(config, tree, monkeypatch):
    monkeypatch.setattr(z.Client, 'all', lambda self, resource: (tree, 10))
    def fail(*a):
        raise z.ZoteroError('Version conflict')
    monkeypatch.setattr(c, 'write', fail)
    with pytest.raises(z.ZoteroError, match='Version conflict'):
        c.run(config, args(apply=True, expect_library_version=10))
    journal = json.loads(next((config.state_dir / 'collection_operations').glob('*.json')).read_text())
    assert journal['status'] == 'needs_review'


def test_transport_partial_payload_version_and_no_redirect(config, tree, monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"successful":{"0":{"key":"SOURCE01"}},"failed":{}}'
    class Opener:
        def open(self, req, timeout):
            assert req.method == 'POST'
            assert req.full_url == 'https://api.zotero.org/users/123/collections'
            assert req.get_header('If-unmodified-since-version') == '10'
            assert json.loads(req.data) == [dict(key='SOURCE01', version=4, name='new', parentCollection='PARENT01')]
            return Response()
    def opener(handler):
        assert isinstance(handler, z._NoRedirect)
        return Opener()
    monkeypatch.setattr(c.urllib.request, 'build_opener', opener)
    c.write(config, c.plan(config, tree, 10, 'SOURCE01', 'new', 'PARENT01'))


@pytest.mark.parametrize('code', [403, 412, 429])
def test_http_errors_are_sanitized_and_not_retried(config, tree, monkeypatch, code):
    class Opener:
        calls = 0
        def open(self, req, timeout):
            self.calls += 1
            raise urllib.error.HTTPError(req.full_url, code, 'SECRET-SERVER-CONTENT', {}, None)
    opener = Opener()
    monkeypatch.setattr(c.urllib.request, 'build_opener', lambda handler: opener)
    with pytest.raises(z.ZoteroError) as exc:
        c.write(config, c.plan(config, tree, 10, 'SOURCE01', 'new', 'PARENT01'))
    assert 'SECRET' not in str(exc.value) and str(code) in str(exc.value)
    assert opener.calls == 1


from nora_cli import zotero_collection_members as m


def paper(key='PAPER001', **fields):
    data = dict(itemType='journalArticle', title='Example', collections=['SOURCE01'])
    data.update(fields)
    return dict(key=key, version=4, data=data)


def member_args(**overrides):
    values = dict(collection_command='add-items', key='PARENT01', item=['PAPER001'],
                  apply=False, expect_library_version=None)
    values.update(overrides)
    return SimpleNamespace(**values)


def test_memberships_are_additive_idempotent_and_do_not_mutate(config, tree):
    item = paper()
    changes = m.membership_plan(config, tree, [item], 'PARENT01')
    assert changes[0]['after'] == ['SOURCE01', 'PARENT01']
    assert item['data']['collections'] == ['SOURCE01']
    item['data']['collections'] = changes[0]['after']
    assert m.membership_plan(config, tree, [item], 'PARENT01') == []


def test_memberships_reject_ignored_item_and_destination(config, tree):
    tree[0]['data']['name'] = '_archive'
    with pytest.raises(z.ZoteroError, match='ignored'):
        m.membership_plan(config, tree, [paper()], 'PARENT01')
    with pytest.raises(z.ZoteroError, match='ignored'):
        m.membership_plan(config, tree, [paper(collections=[])], 'SOURCE01')


@pytest.mark.parametrize('kind', ['note', 'annotation', 'attachment'])
def test_memberships_reject_non_bibliographic(config, tree, kind):
    with pytest.raises(z.ZoteroError, match='bibliographic'):
        m.membership_plan(config, tree, [paper(itemType=kind)], 'PARENT01')


def test_create_plan_and_existing_name_noop(config, tree):
    key, payload = m.create_plan(config, tree, 10, 'gpu-security', 'root')
    assert len(key) == 8 and payload == dict(key=key, name='gpu-security', parentCollection=False)
    assert m.create_plan(config, tree, 10, 'oram', 'root') == ('PARENT01', None)
    with pytest.raises(z.ZoteroError, match='excluded'):
        m.create_plan(config, tree, 10, '_private', 'root')
    with pytest.raises(z.ZoteroError, match='not found'):
        m.create_plan(config, tree, 10, 'gpu-security', 'MISSING1')


def test_create_cli_preview_apply_verify(config, tree, monkeypatch):
    monkeypatch.setattr(z.Client, 'all', lambda self, resource: (tree, 10))
    monkeypatch.setattr(m, 'new_key', lambda: 'NEWKEY22')
    calls = []
    def post(config, resource, payloads, version):
        assert resource == 'collections' and version == 10
        calls.append(payloads)
        tree.append(dict(key=payloads[0]['key'], version=10, data=dict(payloads[0])))
    monkeypatch.setattr(c, 'post', post)
    options = SimpleNamespace(collection_command='create', name='gpu-security', parent='root',
                              apply=False, expect_library_version=None)
    assert m.run(config, options) == 0
    assert not calls and not config.state_dir.exists()
    options.apply = True
    options.expect_library_version = 10
    assert m.run(config, options) == 0
    assert m.run(config, options) == 0
    assert len(calls) == 1


def test_membership_cli_payload_and_partial_failure_journal(config, tree, monkeypatch):
    records = [paper(), paper('PAPER002')]
    monkeypatch.setattr(z.Client, 'all', lambda self, resource: (tree, 10))
    monkeypatch.setattr(m, 'selected_items', lambda *a: records)
    def partial(config, resource, payloads, version):
        assert resource == 'items' and version == 10
        assert payloads == [dict(key=i['key'], version=4, collections=['SOURCE01', 'PARENT01']) for i in records]
        records[0]['data']['collections'].append('PARENT01')
        raise z.ZoteroError('Partial write')
    monkeypatch.setattr(c, 'post', partial)
    with pytest.raises(z.ZoteroError, match='partial or complete'):
        m.run(config, member_args(item=['PAPER001', 'PAPER002'], apply=True, expect_library_version=10))
    journal = json.loads(next((config.state_dir/'collection_operations').glob('*.json')).read_text())
    assert journal['status'] == 'needs_review'
    assert journal['changes'][0]['before'] == ['SOURCE01']
    assert journal['changes'][1]['before'] == ['SOURCE01']


def test_membership_cli_verified_and_noop(config, tree, monkeypatch):
    records = [paper()]
    monkeypatch.setattr(z.Client, 'all', lambda self, resource: (tree, 10))
    monkeypatch.setattr(m, 'selected_items', lambda *a: records)
    calls = []
    def post(config, resource, payloads, version):
        calls.append(payloads)
        records[0]['data']['collections'] = payloads[0]['collections']
    monkeypatch.setattr(c, 'post', post)
    assert m.run(config, member_args()) == 0 and not calls
    assert m.run(config, member_args(apply=True, expect_library_version=10)) == 0
    assert m.run(config, member_args(apply=True, expect_library_version=10)) == 0
    assert len(calls) == 1
    journal = json.loads(next((config.state_dir/'collection_operations').glob('*.json')).read_text())
    assert journal['status'] == 'verified'


def test_selected_items_version_and_missing_guard(config, monkeypatch):
    monkeypatch.setattr(z, '_get', lambda *a: ([paper()], {'last-modified-version': '10'}))
    assert len(m.selected_items(config, ['PAPER001'], 10)) == 1
    with pytest.raises(z.ZoteroError, match='changed'):
        m.selected_items(config, ['PAPER001'], 9)
    with pytest.raises(z.ZoteroError, match='missing'):
        m.selected_items(config, ['PAPER001', 'PAPER002'], 10)


def test_batch_response_requires_all_confirmations(config, monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"successful":{"0":{"key":"PAPER001"}},"failed":{"1":{"code":412}}}'
    class Opener:
        def open(self, *a, **kw): return Response()
    monkeypatch.setattr(c.urllib.request, 'build_opener', lambda *a: Opener())
    with pytest.raises(z.ZoteroError, match='did not confirm'):
        c.post(config, 'items', [dict(key='PAPER001'), dict(key='PAPER002')], 10)


def test_finish_inbox_removes_parent_and_child_keeps_other_memberships(config, tree):
    tree += [dict(key='INBOX001', version=1, data=dict(name='_inbox', parentCollection=False)),
             dict(key='INBOX002', version=1, data=dict(name='conference', parentCollection='INBOX001'))]
    item = paper(collections=['INBOX001', 'INBOX002', 'SOURCE01'])
    changes = m.membership_plan(config, tree, [item], 'PARENT01', finish_inbox=True)
    assert changes[0]['after'] == ['SOURCE01', 'PARENT01']
    assert item['data']['collections'] == ['INBOX001', 'INBOX002', 'SOURCE01']
    item['data']['collections'] = changes[0]['after']
    assert m.membership_plan(config, tree, [item], 'PARENT01', finish_inbox=True) == []


def test_finish_inbox_existing_destination_still_clears_inbox(config, tree):
    tree.append(dict(key='INBOX001', version=1, data=dict(name='_inbox')))
    changes = m.membership_plan(config, tree, [paper(collections=['INBOX001', 'PARENT01'])], 'PARENT01', True)
    assert changes[0]['after'] == ['PARENT01']
    with pytest.raises(z.ZoteroError, match='outside'):
        m.membership_plan(config, tree, [paper()], 'INBOX001', True)


def test_finish_inbox_does_not_override_ignored_member(config, tree):
    tree += [dict(key='INBOX001', version=1, data=dict(name='_inbox')),
             dict(key='HIDDEN01', version=1, data=dict(name='_hidden', parentCollection='INBOX001'))]
    with pytest.raises(z.ZoteroError, match='ignored'):
        m.membership_plan(config, tree, [paper(collections=['HIDDEN01'])], 'PARENT01', True)


def test_finish_inbox_cli_changes_only_collections(config, tree, monkeypatch):
    tree.append(dict(key='INBOX001', version=1, data=dict(name='_inbox')))
    records = [paper(collections=['INBOX001', 'SOURCE01'])]
    monkeypatch.setattr(z.Client, 'all', lambda self, resource: (tree, 10))
    monkeypatch.setattr(m, 'selected_items', lambda *a: records)
    def post(config, resource, payloads, version):
        assert payloads == [dict(key='PAPER001', version=4, collections=['SOURCE01', 'PARENT01'])]
        records[0]['data']['collections'] = payloads[0]['collections']
    monkeypatch.setattr(c, 'post', post)
    assert m.run(config, member_args(apply=True, expect_library_version=10, finish_inbox=True)) == 0


from nora_cli import zotero_items as zi


def trash_args(**overrides):
    return SimpleNamespace(**dict(dict(item_command='trash', key='PAPER001', apply=False, expect_library_version=None), **overrides))


def test_trash_preview_apply_and_repeat(config, tree, monkeypatch):
    record = paper()
    monkeypatch.setattr(zi, 'read_item', lambda *a: (record, 10))
    monkeypatch.setattr(z.Client, 'all', lambda *a: (tree, 10))
    calls = []
    def post(config, resource, payloads, version):
        assert resource == 'items' and payloads == [dict(key='PAPER001', version=4, deleted=1)]
        assert version == 10
        calls.append(1)
        record['data']['deleted'] = 1
    monkeypatch.setattr(zi, 'post', post)
    assert zi.run(config, trash_args()) == 0
    assert not calls and not config.state_dir.exists()
    assert zi.run(config, trash_args(apply=True, expect_library_version=10)) == 0
    assert zi.run(config, trash_args(apply=True, expect_library_version=10)) == 0
    assert len(calls) == 1
    assert json.loads(next((config.state_dir/'item_operations').glob('*.json')).read_text())['status'] == 'verified'


def test_trash_version_and_ignore_guard(config, tree, monkeypatch):
    monkeypatch.setattr(zi, 'read_item', lambda *a: (paper(), 10))
    monkeypatch.setattr(z.Client, 'all', lambda *a: (tree, 10))
    monkeypatch.setattr(zi, 'post', lambda *a: pytest.fail('Unexpected write'))
    with pytest.raises(z.ZoteroError, match='requires'):
        zi.run(config, trash_args(apply=True))
    with pytest.raises(z.ZoteroError, match='changed'):
        zi.run(config, trash_args(apply=True, expect_library_version=9))
    tree[0]['data']['name'] = '_archive'
    with pytest.raises(z.ZoteroError, match='excluded'):
        zi.run(config, trash_args(apply=True, expect_library_version=10))


def test_trash_readback_failure_retains_journal(config, tree, monkeypatch):
    monkeypatch.setattr(zi, 'read_item', lambda *a: (paper(), 10))
    monkeypatch.setattr(z.Client, 'all', lambda *a: (tree, 10))
    monkeypatch.setattr(zi, 'post', lambda *a: None)
    with pytest.raises(z.ZoteroError, match='may already'):
        zi.run(config, trash_args(apply=True, expect_library_version=10))
    assert json.loads(next((config.state_dir/'item_operations').glob('*.json')).read_text())['status'] == 'needs_review'


def test_read_item_includes_trash_and_checks_identity(config, monkeypatch):
    def get(url, key):
        assert 'includeTrashed=1' in url and 'itemKey=PAPER001' in url
        return [paper(deleted=1)], {'last-modified-version':'10'}
    monkeypatch.setattr(z, '_get', get)
    assert zi.read_item(config, 'PAPER001')[0]['data']['deleted'] == 1
    monkeypatch.setattr(z, '_get', lambda *a: ([paper('OTHER001')], {'last-modified-version':'10'}))
    with pytest.raises(z.ZoteroError, match='not found'):
        zi.read_item(config, 'PAPER001')


def test_flatten_inbox_keeps_root_and_other_memberships(config, tree):
    tree += [dict(key='INBOX001',version=1,data=dict(name='_inbox')),
             dict(key='INBOX002',version=1,data=dict(name='venue',parentCollection='INBOX001'))]
    record=paper(collections=['INBOX001','INBOX002','SOURCE01'])
    change=m.membership_plan(config,tree,[record],'INBOX001',flatten_inbox=True)[0]
    assert change['after']==['INBOX001','SOURCE01']
    record['data']['collections']=change['after']
    assert m.membership_plan(config,tree,[record],'INBOX001',flatten_inbox=True)==[]
    with pytest.raises(z.ZoteroError,match='top-level'):
        m.membership_plan(config,tree,[record],'PARENT01',flatten_inbox=True)


def test_delete_empty_checks_children_ignored_trashed_and_version(config,tree,monkeypatch):
    from nora_cli import zotero_collection_delete as cd
    monkeypatch.setattr(z,'_get',lambda *a:([],{'last-modified-version':'10','total-results':'0'}))
    assert cd.empty_collection(config,tree,'CHILD001',10)['key']=='CHILD001'
    with pytest.raises(z.ZoteroError,match='children'):
        cd.empty_collection(config,tree,'SOURCE01',10)
    with pytest.raises(z.ZoteroError,match='changed'):
        cd.empty_collection(config,tree,'CHILD001',9)
    monkeypatch.setattr(z,'_get',lambda *a:([paper(deleted=1)],{'last-modified-version':'10','total-results':'1'}))
    with pytest.raises(z.ZoteroError,match='not empty'):
        cd.empty_collection(config,tree,'CHILD001',10)
    tree[2]['data']['name']='_hidden'
    with pytest.raises(z.ZoteroError,match='ignored'):
        cd.empty_collection(config,tree,'CHILD001',10)


def test_delete_empty_transport_and_journal(config,tree,monkeypatch):
    from nora_cli import zotero_collection_delete as cd
    monkeypatch.setattr(z.Client,'all',lambda *a:(tree,10))
    monkeypatch.setattr(z,'_get',lambda *a:([],{'last-modified-version':'10','total-results':'0'}))
    class Response:
        status=204
        def __enter__(self):return self
        def __exit__(self,*a):pass
    class Opener:
        def open(self,req,timeout):
            assert req.method=='DELETE' and req.full_url.endswith('/collections?collectionKey=CHILD001')
            assert req.get_header('If-unmodified-since-version')=='10'
            tree[:]=[c for c in tree if c['key']!='CHILD001']
            return Response()
    monkeypatch.setattr(cd.urllib.request,'build_opener',lambda *a:Opener())
    opts=SimpleNamespace(key='CHILD001',apply=False,expect_library_version=None)
    assert cd.run(config,opts)==0 and not config.state_dir.exists()
    opts.apply=True;opts.expect_library_version=10
    assert cd.run(config,opts)==0
    assert json.loads(next((config.state_dir/'collection_operations').glob('*.json')).read_text())['status']=='verified'
