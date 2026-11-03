import os

import pytest

from lowpoint.telegram.security import (
    UNAUTHORIZED_MESSAGE,
    is_chat_allowed,
    validate_secret_token,
)


class TestValidateSecretToken:
    def test_valid_token(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "my-secret-123")
        assert validate_secret_token("my-secret-123") is True

    def test_invalid_token(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "my-secret-123")
        assert validate_secret_token("wrong-secret") is False

    def test_none_header(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "my-secret-123")
        assert validate_secret_token(None) is False

    def test_empty_header(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "my-secret-123")
        assert validate_secret_token("") is False

    def test_no_env_var(self, monkeypatch):
        monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
        assert validate_secret_token("anything") is False

    def test_empty_env_var(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "")
        assert validate_secret_token("") is False

    def test_timing_safe(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "abc")
        assert validate_secret_token("ab") is False
        assert validate_secret_token("abcd") is False


class TestIsChatAllowed:
    def test_single_id(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_CHAT_IDS", "12345")
        assert is_chat_allowed(12345) is True
        assert is_chat_allowed(99999) is False

    def test_multiple_ids(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_CHAT_IDS", "111,222,333")
        assert is_chat_allowed(111) is True
        assert is_chat_allowed(222) is True
        assert is_chat_allowed(333) is True
        assert is_chat_allowed(444) is False

    def test_spaces_in_list(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_CHAT_IDS", " 111 , 222 ")
        assert is_chat_allowed(111) is True
        assert is_chat_allowed(222) is True

    def test_empty_env(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_CHAT_IDS", "")
        assert is_chat_allowed(12345) is False

    def test_no_env(self, monkeypatch):
        monkeypatch.delenv("ALLOWED_CHAT_IDS", raising=False)
        assert is_chat_allowed(12345) is False

    def test_negative_id(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_CHAT_IDS", "-100123456")
        assert is_chat_allowed(-100123456) is True
        assert is_chat_allowed(100123456) is False

    def test_non_numeric_ignored(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_CHAT_IDS", "abc,123")
        assert is_chat_allowed(123) is True


class TestUnauthorizedMessage:
    def test_message_is_polite(self):
        assert "pessoal" in UNAUTHORIZED_MESSAGE
        assert "testes" in UNAUTHORIZED_MESSAGE
