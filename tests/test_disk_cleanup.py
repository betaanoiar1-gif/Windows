from pathlib import Path

from smartpc.disk_cleanup import _matches_category, summarize
from smartpc.models import Action, Candidate, Risk


def test_thumbnail_match_is_narrow():
    class Category:
        key = "explorer_thumbnails"

    assert _matches_category(Category(), Path("thumbcache_256.db"))
    assert not _matches_category(Category(), Path("iconcache.db"))
    assert not _matches_category(Category(), Path("thumbcache_256.tmp"))


def test_summary_separates_automatic_and_review_bytes():
    items = [
        Candidate("a", "cleanup:temp", 100, action=Action.QUARANTINE, risk=Risk.SAFE, metadata={"category": "temp"}),
        Candidate("b", "cleanup:wer", 900, action=Action.REVIEW, risk=Risk.LOW, metadata={"category": "wer"}),
    ]
    result = summarize(items)
    assert result["bytes"] == 1000
    assert result["automatic_quarantine_bytes"] == 100
    assert result["categories"]["wer"]["bytes"] == 900
