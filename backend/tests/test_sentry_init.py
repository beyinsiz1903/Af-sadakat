"""Sentry no-op when DSN absent."""
import importlib


def test_sentry_noop_without_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    import sentry_init
    importlib.reload(sentry_init)
    assert sentry_init.init_sentry() is False


def test_sentry_init_signature():
    import sentry_init
    assert callable(sentry_init.init_sentry)
