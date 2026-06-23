"""The anti-hallucination guardrail blocks weak matches.

These are pure unit tests: retrieve() is mocked, so no Bedrock or DB call is
made — we test only the threshold decision in retrieve_with_guardrail().
"""

from app.rag import retrieval

HIGH = [{"similarity": 0.5, "content": "x", "source": "a", "section": "b"}]
LOW = [{"similarity": 0.1, "content": "x", "source": "a", "section": "b"}]


def test_blocks_when_below_threshold(monkeypatch):
    monkeypatch.setattr(retrieval, "retrieve", lambda conn, q, k=3: LOW)
    assert retrieval.retrieve_with_guardrail(None, "q") is None


def test_passes_when_above_threshold(monkeypatch):
    monkeypatch.setattr(retrieval, "retrieve", lambda conn, q, k=3: HIGH)
    assert retrieval.retrieve_with_guardrail(None, "q") == HIGH


def test_blocks_when_no_hits(monkeypatch):
    monkeypatch.setattr(retrieval, "retrieve", lambda conn, q, k=3: [])
    assert retrieval.retrieve_with_guardrail(None, "q") is None
