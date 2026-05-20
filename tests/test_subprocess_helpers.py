import io

from src.subprocess_helpers import _write_source, release_upload


class TestWriteSource:
    def test_writes_bytes(self, tmp_path):
        out = tmp_path / "out.bin"
        _write_source(b"hello", out)
        assert out.read_bytes() == b"hello"
    
    def test_writes_bytearray(self, tmp_path):
        out = tmp_path / "out.bin"
        _write_source(bytearray(b"hello"), out)
        assert out.read_bytes() == b"hello"
    
    def test_writes_memoryview(self, tmp_path):
        out = tmp_path / "out.bin"
        _write_source(memoryview(b"hello"), out)
        assert out.read_bytes() == b"hello"
    
    def test_writes_file_like_object(self, tmp_path):
        out = tmp_path / "out.bin"
        _write_source(io.BytesIO(b"streamed content"), out)
        assert out.read_bytes() == b"streamed content"
    
    def test_rewinds_file_like_before_copying(self, tmp_path):
        out = tmp_path / "out.bin"
        source = io.BytesIO(b"streamed content")
        source.read()  # advance to end; _write_source must seek(0) first
        _write_source(source, out)
        assert out.read_bytes() == b"streamed content"


class TestReleaseUpload:
    def test_no_op_for_object_without_file_id(self):
        # Plain objects (e.g. bytes) carry no file_id; release_upload returns quietly.
        release_upload(b"not an upload")
    
    def test_no_op_outside_a_streamlit_run(self):
        class FakeUpload:
            file_id = "abc123"
        
        # No active script run context, so the lookup short-circuits without error.
        release_upload(FakeUpload())
