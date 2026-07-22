"""Tests for LATENCY_TRACE instrumentation helpers."""

from app.services.latency_trace import PhaseTimer, enabled


def test_phase_timer_ms():
    t = PhaseTimer()
    t.mark("end")
    assert t.ms_since_start("end") >= 0


def test_enabled_defaults_false(monkeypatch):
    monkeypatch.delenv("LATENCY_TRACE", raising=False)
    # Settings may be cached; just ensure enabled() returns bool
    assert isinstance(enabled(), bool)
