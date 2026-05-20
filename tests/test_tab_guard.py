from src.tab_guard import (
    _pop_keys,
    clear_stale_results,
    has_finished_downloads,
)


class TestHasFinishedDownloads:
    def test_false_when_nothing_set(self, fake_session_state):
        assert has_finished_downloads() is False
    
    def test_true_when_a_download_key_is_set(self, fake_session_state):
        fake_session_state["proofread_result"] = b"some-bytes"
        assert has_finished_downloads() is True
    
    def test_false_when_download_key_is_none(self, fake_session_state):
        fake_session_state["shrunk_bytes"] = None
        assert has_finished_downloads() is False


class TestPopKeys:
    def test_removes_present_keys(self, fake_session_state):
        fake_session_state["a"] = 1
        fake_session_state["b"] = 2
        _pop_keys(["a", "b"])
        assert "a" not in fake_session_state
        assert "b" not in fake_session_state
    
    def test_ignores_absent_keys(self, fake_session_state):
        fake_session_state["a"] = 1
        _pop_keys(["a", "missing"])
        assert "a" not in fake_session_state


class TestClearStaleResults:
    def test_records_active_page(self, fake_session_state):
        clear_stale_results("translate", None)
        assert fake_session_state["_active_page"] == "translate"
    
    def test_first_visit_keeps_existing_results(self, fake_session_state):
        fake_session_state["shrunk_bytes"] = b"data"
        clear_stale_results("translate", None)
        assert fake_session_state["shrunk_bytes"] == b"data"
    
    def test_same_page_keeps_existing_results(self, fake_session_state):
        fake_session_state["shrunk_bytes"] = b"data"
        clear_stale_results("shrink", "shrink")
        assert fake_session_state["shrunk_bytes"] == b"data"
    
    def test_leaving_a_page_drops_its_results(self, fake_session_state):
        fake_session_state["shrunk_bytes"] = b"data"
        fake_session_state["translated_bytes"] = b"keep-me"
        clear_stale_results("translate", "shrink")
        assert "shrunk_bytes" not in fake_session_state
        assert fake_session_state["translated_bytes"] == b"keep-me"
    
    def test_leaving_a_page_releases_its_uploader(self, fake_session_state):
        fake_session_state["shrink_uploader"] = "uploaded-file-stub"
        clear_stale_results("translate", "shrink")
        assert "shrink_uploader" not in fake_session_state
