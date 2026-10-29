"""Zotero integration: offline fixtures only, no credentials or live library access."""
import json
import os
import sys
import urllib.error
import urllib.parse
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nora_cli import zotero as z
from nora_cli import zotero_audit as a
from nora_cli.cli import main


@pytest.fixture
def config(tmp_path, monkeypatch):
    for name in list(z.ENV_FIELDS) + ["ZOTERO_API_KEY", "XDG_CONFIG_HOME", "XDG_DATA_HOME"]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    return z.Config("123", data_dir=tmp_path / "state")


def item(key="PAPER001", **overrides):
    data = dict(itemType="journalArticle", title="An Example Research Paper", date="2024",
                creators=[{"creatorType": "author", "name": "Example Research Institute"}],
                collections=["COLLECT1"], tags=[], DOI="10.1000/example", abstractNote="Abstract")
    data.update(overrides)
    return {"key": key, "version": 3, "data": data}


def attachment(key="ATTACH01", **overrides):
    data = dict(itemType="attachment", title="PDF", parentItem="PAPER001",
                contentType="application/pdf", linkMode="imported_url", filename="paper.pdf")
    data.update(overrides)
    return {"key": key, "version": 3, "data": data}


def snapshot(config, items=None, collections=None, version=3):
    return {"schema_version": 1, "library": config.identity, "version": version,
            "fetched_at": "2026-10-28T12:00:00+00:00", "total_api_items": 2,
            "items": [item(), attachment()] if items is None else items,
            "collections": [{"key": "COLLECT1", "version": 3,
                             "data": {"name": "_inbox", "parentCollection": False}}] if collections is None else collections}


def headers(version=3, total=0):
    return {"last-modified-version": str(version), "total-results": str(total)}


def test_explicit_credentials_precedence_no_autoload_or_secret_repr(config, tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("ZOTERO_LIBRARY_ID=999\nZOTERO_API_KEY=implicit-secret\n")
    with pytest.raises(z.ZoteroError, match="LIBRARY_ID"):
        z.load_config()
    file = tmp_path / "robo.env"
    file.write_text("ZOTERO_LIBRARY_ID=123\nZOTERO_API_KEY='file-secret' # comment\n"
                    "ZOTERO_PDF_DIR='/tmp/pdfs with spaces'\nUNRELATED=$(dangerous command)\n")
    result = z.load_config(env_file=file)
    assert result.api_key == "file-secret" and result.pdf_dir == Path("/tmp/pdfs with spaces")
    assert "file-secret" not in repr(result)
    monkeypatch.setenv("ZOTERO_API_KEY", "env-secret")
    monkeypatch.setenv("ZOTERO_LIBRARY_ID", "456")
    assert z.load_config(env_file=file).api_key == "env-secret"
    assert z.load_config(env_file=file).library_id == "456"


@pytest.mark.parametrize("value", ["$(touch /tmp/not-allowed)", "${OTHER_KEY}", "`command`", "'unterminated"])
def test_env_file_never_executes_or_expands(config, tmp_path, value):
    file = tmp_path / "env"
    file.write_text(f"ZOTERO_API_KEY={value}\n")
    with pytest.raises(z.ZoteroError) as exc:
        z.load_config(env_file=file)
    assert value not in str(exc.value)


def test_config_xdg_and_secret_rejection(config, tmp_path, monkeypatch):
    folder = tmp_path / "config/nora"
    folder.mkdir(parents=True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(folder.parent))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    path = folder / "zotero.json"
    path.write_text(json.dumps({"library_id": "123", "library_type": "group"}))
    result = z.load_config()
    assert result.state_dir == tmp_path / "data/nora/zotero/group-123"
    path.write_text(json.dumps({"library_id": "123", "api_key": "secret"}))
    with pytest.raises(z.ZoteroError, match="Keep API keys"):
        z.load_config()


def test_robo_home_prefix_in_pdf_path_only(config, tmp_path):
    file = tmp_path / "robo.env"
    file.write_text('ZOTERO_LIBRARY_ID=123\nZOTERO_PDF_DIR="${HOME}/papers"\n')
    assert z.load_config(env_file=file).pdf_dir == tmp_path / "papers"
    file.write_text('ZOTERO_LIBRARY_ID=123\nZOTERO_API_KEY="${HOME}"\n')
    with pytest.raises(z.ZoteroError, match="without expansion"):
        z.load_config(env_file=file)


@pytest.mark.parametrize("name,value", [("ZOTERO_LIBRARY_ID", "../123"), ("ZOTERO_LIBRARY_TYPE", "users"),
                                        ("ZOTERO_API_KEY", "secret\nheader"), ("ZOTERO_PDF_DIR", "relative")])
def test_invalid_configuration_is_safe(config, monkeypatch, name, value):
    monkeypatch.setenv("ZOTERO_LIBRARY_ID", "123")
    monkeypatch.setenv(name, value)
    with pytest.raises(z.ZoteroError) as exc:
        z.load_config()
    assert "secret" not in str(exc.value)


def test_pagination_full_snapshot_includes_children_and_keeps_versions(config, monkeypatch):
    calls = []
    def get(url, key):
        calls.append(url)
        parsed = urllib.parse.urlsplit(url)
        start = int(urllib.parse.parse_qs(parsed.query)["start"][0])
        if parsed.path.endswith("collections"):
            return snapshot(config)["collections"], headers(total=1)
        pages = {0: [item()], 1: [attachment()], 2: [{"key": "NOTE0001", "version": 3,
                                                   "data": {"itemType": "note", "note": "private note"}}]}
        return pages[start], headers(total=3)
    monkeypatch.setattr(z, "_get", get)
    result = z.Client(config).snapshot()
    assert len(calls) == 4 and result["version"] == 3
    assert result["total_api_items"] == 3 and len(result["items"]) == 2
    assert "private note" not in json.dumps(result)


@pytest.mark.parametrize("failure", ["version", "total", "empty", "duplicate", "missing_header", "collection_version"])
def test_incomplete_or_changing_snapshot_fails(config, monkeypatch, failure):
    def get(url, key):
        if "/collections?" in url:
            return [], headers(version=4 if failure == "collection_version" else 3)
        start = int(urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["start"][0])
        if failure == "collection_version":
            return [item()], headers(total=1)
        if start == 0:
            return [item()], headers(total=2)
        if failure == "missing_header":
            return [attachment()], {}
        return ([] if failure == "empty" else [item() if failure == "duplicate" else attachment()],
                headers(version=4 if failure == "version" else 3, total=3 if failure == "total" else 2))
    monkeypatch.setattr(z, "_get", get)
    with pytest.raises(z.ZoteroError):
        z.Client(config).snapshot()
    assert not config.state_dir.exists()


class Response:
    def __init__(self, body=b"[]", response_headers=None):
        self.body = body
        self.headers = response_headers or headers()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self):
        return self.body


def test_transport_get_only_key_in_header_and_no_redirect(config, monkeypatch):
    class Opener:
        def open(self, request, timeout):
            assert request.method == "GET" and timeout == 15
            assert request.get_header("Zotero-api-key") == "secret"
            assert "secret" not in request.full_url
            return Response()
    monkeypatch.setattr(z.urllib.request, "build_opener", lambda handler: Opener())
    assert z._get("https://api.zotero.org/users/123/items", "secret")[0] == []
    assert z._NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.test") is None


@pytest.mark.parametrize("code", [401, 403, 404, 429, 503, 302])
def test_http_errors_never_expose_body_or_key(config, monkeypatch, code):
    class Opener:
        def open(self, *args, **kwargs):
            raise urllib.error.HTTPError("https://example.org/secret", code, "secret", {"Retry-After": "12"}, None)
    monkeypatch.setattr(z.urllib.request, "build_opener", lambda handler: Opener())
    with pytest.raises(z.ZoteroError) as exc:
        z._get("https://api.zotero.org/users/123/items", "secret")
    assert "secret" not in str(exc.value) and f"HTTP {code}" in str(exc.value)


def test_successful_backoff_stops_without_retry(config, monkeypatch):
    class Opener:
        def open(self, *args, **kwargs):
            return Response(response_headers={"Backoff": "30"})
    monkeypatch.setattr(z.urllib.request, "build_opener", lambda handler: Opener())
    with pytest.raises(z.ZoteroError, match="30 seconds"):
        z._get("https://api.zotero.org/users/123/items", "secret")


def test_audit_inbox_unfiled_tag_variants_duplicates_and_no_cross_area_warning(config):
    first = item(tags=[{"tag": "Fuzzing", "type": 1}], collections=["COLLECT1", "COLLECT2"])
    second = item("PAPER002", tags=[{"tag": " fuzzing "}], collections=[], DOI="https://doi.org/10.1000/EXAMPLE")
    snap = snapshot(config, items=[first, second, attachment()], collections=[
        {"key": "COLLECT1", "data": {"name": "_inbox", "parentCollection": False}},
        {"key": "COLLECT2", "data": {"name": "other-area", "parentCollection": False}}])
    result = a.analyze(snap, config)
    kinds = [issue["kind"] for issue in result["issues"]]
    assert set(kinds) == {"unfiled", "duplicate_doi", "duplicate_title", "tag_variant", "no_pdf_attachment"}
    assert result["bibliographic_items"] == 2
    assert result["tag_assignments"] == {"automatic": 1, "manual": 1}
    assert result["pdf_local_status"] == {"stored_file_not_checked": 1}


def test_no_false_author_gap_for_corporate_creator_and_collection_paths(config):
    result = a.analyze(snapshot(config), config)
    assert result["issues"] == []
    paths, warnings = a.collection_paths([
        {"key": "A", "data": {"name": "security"}},
        {"key": "B", "data": {"name": "agents", "parentCollection": "A"}},
        {"key": "C", "data": {"name": "broken", "parentCollection": "D"}},
        {"key": "D", "data": {"name": "cycle", "parentCollection": "C"}}])
    assert paths["B"] == "security/agents" and warnings


def test_attachment_resolution_imported_url_linked_and_traversal(config, tmp_path):
    config.pdf_dir = tmp_path / "linked"
    config.pdf_dir.mkdir()
    (config.pdf_dir / "paper.pdf").write_bytes(b"%PDF-test")
    config.storage_dir = tmp_path / "storage"
    (config.storage_dir / "ATTACH01").mkdir(parents=True)
    (config.storage_dir / "ATTACH01/paper.pdf").write_bytes(b"%PDF-test")
    assert a._local_attachment(attachment()["data"], "ATTACH01", config) == "local_file_present"
    linked = {"linkMode": "linked_file", "path": "attachments:paper.pdf"}
    assert a._local_attachment(linked, "ATTACH02", config) == "local_file_present"
    linked["path"] = "attachments:../outside.pdf"
    assert a._local_attachment(linked, "ATTACH02", config) == "unsafe_path"
    linked["path"] = "attachments:/tmp/outside.pdf"
    assert a._local_attachment(linked, "ATTACH02", config) == "unsafe_path"
    malicious = attachment(filename="../outside.pdf")["data"]
    assert a._local_attachment(malicious, "ATTACH01", config) == "unsafe_path"


def test_ignored_disposition_survives_clear_and_reappearance(config):
    finding = a._issue(config.identity, "unfiled", ["PAPER001"], "Unfiled", {"title": "Old"})
    a.save_audit(config, snapshot(config), [finding])
    a.mark(config, finding["issue_key"], "ignored", "Intentional")
    a.save_audit(config, snapshot(config, version=4), [])
    cleared = a.read_state(config)["issues"][0]
    assert a.issue_status(cleared) == "cleared" and cleared["disposition"] == "ignored"
    updated = a._issue(config.identity, "unfiled", ["PAPER001"], "Unfiled", {"title": "New"})
    a.save_audit(config, snapshot(config, version=5), [updated])
    revived = a.read_state(config)["issues"][0]
    assert a.issue_status(revived) == "ignored" and revived["evidence_changed"]
    assert revived["review_note"] == "Intentional"
    assert (config.state_dir / "state.json").stat().st_mode & 0o777 == 0o600


def test_newer_snapshot_lock_and_corruption_preserve_state(config):
    a.save_audit(config, snapshot(config, version=5), [])
    path = config.state_dir / "state.json"
    before = path.read_bytes()
    with pytest.raises(z.ZoteroError, match="newer snapshot"):
        a.save_audit(config, snapshot(config, version=3), [])
    assert path.read_bytes() == before
    lock = config.state_dir / ".write.lock"
    lock.write_text("another writer")
    with pytest.raises(z.ZoteroError, match="locked"):
        a.save_audit(config, snapshot(config, version=6), [])
    assert path.read_bytes() == before
    lock.unlink()
    path.write_text("{broken")
    with pytest.raises(z.ZoteroError, match="preserved"):
        a.save_audit(config, snapshot(config, version=6), [])
    assert path.read_text() == "{broken"


def test_atomic_replace_failure_leaves_previous_state(config, monkeypatch):
    a.save_audit(config, snapshot(config), [])
    before = (config.state_dir / "state.json").read_bytes()
    def fail(*args):
        raise OSError("disk problem")
    monkeypatch.setattr(a.os, "replace", fail)
    with pytest.raises(OSError):
        a.save_audit(config, snapshot(config, version=4), [])
    assert (config.state_dir / "state.json").read_bytes() == before
    assert not list(config.state_dir.glob(".nora-*"))
    assert not (config.state_dir / ".write.lock").exists()


def test_cli_preview_offline_write_and_review_no_workspace(config, monkeypatch, capsys):
    monkeypatch.setenv("ZOTERO_LIBRARY_ID", "123")
    monkeypatch.setattr(z.Client, "snapshot", lambda self: snapshot(config, items=[item(collections=[])]))
    base = ["zotero", "--data-dir", str(config.data_dir)]
    assert main(base + ["audit"]) == 0
    assert not config.state_dir.exists() and not Path(".nora").exists()
    assert "Preview only" in capsys.readouterr().out
    assert main(base + ["audit", "--write"]) == 0
    assert (config.state_dir / "AUDIT_REPORT.md").is_file()
    assert not Path(".nora").exists()
    issue = a.read_state(config)["issues"][0]
    assert main(base + ["review", "mark", issue["issue_key"], "ignored", "--note", "Intentional"]) == 0
    assert main(base + ["review", "list", "--status", "ignored"]) == 0
    def offline_fail(*args):
        raise AssertionError("unexpected network")
    monkeypatch.setattr(z.Client, "snapshot", offline_fail)
    assert main(base + ["audit", "--offline", "--limit", "0"]) == 0
    assert "saved snapshot" in capsys.readouterr().out


def test_failed_download_does_not_clear_previous_findings(config, monkeypatch):
    finding = a._issue(config.identity, "unfiled", ["PAPER001"], "Unfiled", {})
    a.save_audit(config, snapshot(config), [finding])
    before = (config.state_dir / "state.json").read_bytes()
    monkeypatch.setenv("ZOTERO_LIBRARY_ID", "123")
    def fail(self):
        raise z.ZoteroError("Network failed")
    monkeypatch.setattr(z.Client, "snapshot", fail)
    assert main(["zotero", "--data-dir", str(config.data_dir), "audit", "--write"]) == 1
    assert (config.state_dir / "state.json").read_bytes() == before


def test_offline_doctor_redacts_key_and_never_connects(config, monkeypatch, capsys):
    monkeypatch.setenv("ZOTERO_LIBRARY_ID", "123")
    monkeypatch.setenv("ZOTERO_API_KEY", "very-secret")
    def fail(*args):
        raise AssertionError("network not expected")
    monkeypatch.setattr(z, "_get", fail)
    assert main(["zotero", "doctor", "--offline"]) == 0
    output = capsys.readouterr().out
    assert "very-secret" not in output and "not been verified" in output


def test_render_controls_and_bounded_output(config):
    snap = snapshot(config, items=[item(tags=[{"tag": "bad\x1b[31m\n<tag>"}], collections=[])])
    result = a.analyze(snap, config)
    issues = a.reconcile([], result["issues"], snap["fetched_at"])
    report = a.render(snap, result, issues, limit=1)
    assert "\x1b" not in report and "<tag>" not in report
    assert "more; use --limit 0" in report
