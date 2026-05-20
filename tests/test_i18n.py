from src.i18n import (
    TRANSLATIONS,
    get_lang,
    t,
    toggle_lang,
    widget_text_map,
)


class TestGetLang:
    def test_defaults_to_english(self, fake_session_state):
        assert get_lang() == "en"
    
    def test_returns_stored_language(self, fake_session_state):
        fake_session_state["lang"] = "fr"
        assert get_lang() == "fr"


class TestTranslate:
    def test_known_key_english(self, fake_session_state):
        assert t("tab.translate") == "Translate Document"
    
    def test_known_key_french(self, fake_session_state):
        fake_session_state["lang"] = "fr"
        assert t("tab.translate") == "Traduire un document"
    
    def test_missing_key_returns_the_key(self, fake_session_state):
        assert t("no.such.key") == "no.such.key"
    
    def test_unknown_language_falls_back_to_english(self, fake_session_state):
        fake_session_state["lang"] = "de"
        assert t("tab.translate") == "Translate Document"
    
    def test_kwargs_are_formatted_into_the_string(self, fake_session_state):
        result = t("shrink.complete", before="1.00 MB", after="0.50 MB")
        assert result == "Shrunk: 1.00 MB → 0.50 MB"
    
    def test_every_english_key_exists_in_french(self):
        assert set(TRANSLATIONS["en"]) == set(TRANSLATIONS["fr"])


class TestToggleLang:
    def test_toggles_english_to_french(self, fake_session_state):
        toggle_lang()
        assert get_lang() == "fr"
    
    def test_toggles_french_to_english(self, fake_session_state):
        fake_session_state["lang"] = "fr"
        toggle_lang()
        assert get_lang() == "en"


class TestWidgetTextMap:
    def test_french_maps_english_widget_text_to_french(self, fake_session_state):
        fake_session_state["lang"] = "fr"
        mapping = widget_text_map()
        assert mapping["Drag and drop file here"] == "Glisser-déposer un fichier ici"
    
    def test_english_maps_french_widget_text_to_english(self, fake_session_state):
        mapping = widget_text_map()
        assert mapping["Glisser-déposer un fichier ici"] == "Drag and drop file here"
    
    def test_override_default_text_is_remapped(self, fake_session_state):
        mapping = widget_text_map()
        assert mapping["200MB per file • DOCX"] == "Drag a DOCX file (max 200 MB)"
