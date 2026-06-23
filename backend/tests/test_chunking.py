"""Markdown chunking splits by section and carries context."""

from scripts.ingest import chunk_markdown

SAMPLE = """# Returns Policy

## Return window
You may return most items within 30 days.

## Refund timing
Refunds are issued within 5-7 business days.
"""


def test_splits_by_section():
    chunks = chunk_markdown(SAMPLE)
    assert len(chunks) == 2


def test_chunk_carries_title_and_section():
    section, doc_title, content = chunk_markdown(SAMPLE)[0]
    assert doc_title == "Returns Policy"
    assert section == "Return window"
    # the embedded text keeps doc + section for context and citations
    assert "Returns Policy" in content
    assert "Return window" in content
    assert "30 days" in content


def test_empty_sections_are_skipped():
    chunks = chunk_markdown("# Title\n\n## Empty\n\n## Real\nhas content\n")
    sections = [c[0] for c in chunks]
    assert sections == ["Real"]
