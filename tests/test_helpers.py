from pathlib import Path

import pytest

from src import helpers
from src.helpers import (
    SYNC_DOCUMENT_TRANSLATION_MAX_BYTES,
    chat,
    translate_document,
    translate_document_bytes,
)


class FakeTranslatorClient:
    def __init__(self):
        self.calls = []
    
    def translate(self, target_language, body):
        self.calls.append({"target_language": target_language, "body": body})
        return b"TRANSLATED-BYTES"


@pytest.fixture
def fake_translator(monkeypatch):
    client = FakeTranslatorClient()
    monkeypatch.setattr(helpers, "get_translator_client", lambda: client)
    return client


class TestSizeLimit:
    def test_constant_is_ten_megabytes(self):
        assert SYNC_DOCUMENT_TRANSLATION_MAX_BYTES == 10 * 1024 * 1024
    
    def test_oversized_document_is_rejected(self):
        oversized = b"\x00" * (SYNC_DOCUMENT_TRANSLATION_MAX_BYTES + 1)
        with pytest.raises(NotImplementedError):
            translate_document_bytes(oversized, source_language="en")
    
    def test_document_at_the_limit_is_accepted(self, fake_translator):
        at_limit = b"\x00" * SYNC_DOCUMENT_TRANSLATION_MAX_BYTES
        translate_document_bytes(at_limit, source_language="en")
        assert len(fake_translator.calls) == 1


class TestLanguageDirection:
    def test_english_translates_to_french(self, fake_translator):
        translate_document_bytes(b"small", source_language="en")
        assert fake_translator.calls[0]["target_language"] == "fr"
    
    def test_french_translates_to_english(self, fake_translator):
        translate_document_bytes(b"small", source_language="fr")
        assert fake_translator.calls[0]["target_language"] == "en"
    
    def test_language_is_case_insensitive(self, fake_translator):
        translate_document_bytes(b"small", source_language="EN")
        assert fake_translator.calls[0]["target_language"] == "fr"
    
    def test_unsupported_language_raises(self, fake_translator):
        with pytest.raises(ValueError):
            translate_document_bytes(b"small", source_language="de")
    
    def test_returns_translated_bytes(self, fake_translator):
        result = translate_document_bytes(b"small", source_language="en")
        assert result == b"TRANSLATED-BYTES"
    
    def test_filename_and_content_type_passed_through(self, fake_translator):
        translate_document_bytes(b"small", source_language="en", filename="report.docx")
        filename, data, content_type = fake_translator.calls[0]["body"]["document"]
        assert filename == "report.docx"
        assert data == b"small"
        assert content_type == helpers.DOCX_MIME


class TestTranslateDocumentFile:
    def test_writes_translated_file_next_to_input(self, tmp_path, fake_translator):
        input_path = tmp_path / "input.docx"
        input_path.write_bytes(b"original")
        
        translate_document(input_path, input_language="en")
        
        output_path = tmp_path / "input_translated.docx"
        assert output_path.exists()
        assert output_path.read_bytes() == b"TRANSLATED-BYTES"
    
    def test_reads_input_bytes_from_disk(self, tmp_path, fake_translator):
        input_path = tmp_path / "doc.docx"
        input_path.write_bytes(b"the-source-bytes")
        
        translate_document(input_path, input_language="fr")
        
        _, data, _ = fake_translator.calls[0]["body"]["document"]
        assert data == b"the-source-bytes"


class TestChat:
    def test_unknown_client_type_raises_value_error(self):
        with pytest.raises(ValueError):
            chat("hello", model="some-model", client_type="bogus")
