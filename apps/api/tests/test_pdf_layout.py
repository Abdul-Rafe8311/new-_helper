import pytest

from app.pdf.layout import date_line, plan_pages, shorten
from app.pdf.snapshot import build_snapshot
from tests.pdf_helpers import fixture_records, fixture_snapshot


def test_snapshot_reads_the_fixture_edition():
    snap = fixture_snapshot()
    assert snap.paper_name == "The Rafe Courier"
    assert len(snap.stories) == 27
    assert snap.story(snap.lead_item_id).slot == "lead"
    assert len(snap.three_things) == 3
    assert len(snap.quiz) == 3
    assert snap.source_count > 10


def test_missing_layout_keys_are_derived_from_the_items():
    edition, items, reader = fixture_records()
    edition["layout"] = {}
    snap = build_snapshot(edition, items, reader)
    assert snap.paper_name == "The Rafe Courier"  # from the reader's profile
    assert snap.story(snap.lead_item_id).slot == "lead"
    assert snap.sections[0].name == "Top Stories"
    assert snap.quote is None
    assert snap.quiz == []


def test_headline_and_summary_fall_back_to_the_article():
    edition, items, reader = fixture_records()
    items[0]["headline"] = None
    items[0]["summary"] = None
    items[0]["article"]["title"] = "Article title"
    items[0]["article"]["excerpt"] = "Article excerpt."
    story = build_snapshot(edition, items, reader).stories[0]
    assert (story.headline, story.summary) == ("Article title", "Article excerpt.")


def test_empty_edition_is_rejected():
    edition, _, reader = fixture_records()
    with pytest.raises(ValueError, match="at least one story"):
        build_snapshot(edition, [], reader)


def test_fingerprint_changes_with_content_and_page_size():
    base = fixture_snapshot()
    assert base.fingerprint() == fixture_snapshot().fingerprint()
    assert base.fingerprint() != fixture_snapshot(page_size="Letter").fingerprint()
    edition, items, reader = fixture_records()
    items[3]["headline"] = "A corrected headline"
    assert base.fingerprint() != build_snapshot(edition, items, reader).fingerprint()


def test_date_line_matches_the_masthead_format():
    assert (
        date_line(fixture_snapshot())
        == "Saturday, 17 October 2026 · No. 12 · Islamabad 24°C, sunny"
    )


def test_shorten_keeps_whole_sentences():
    text = "First sentence here. Second sentence follows. Third one is last."
    assert shorten(text, 50) == "First sentence here. Second sentence follows."
    assert shorten(text, 25) == "First sentence here."
    assert shorten(text, 0) == text


def _full(plan):
    return sum(len(b.stories) for b in plan.sections)


def _stories(plan):
    return [v for b in plan.sections for v in b.stories] + [
        v for b in plan.sections for v in b.briefs
    ]


def test_every_story_is_printed_exactly_once():
    for depth in ("brief", "balanced", "deep"):
        plan = plan_pages(fixture_snapshot(depth=depth))
        shown = [plan.front.lead, *plan.front.features, *plan.front.briefs, *_stories(plan)]
        ids = [v.story.item_id for v in shown]
        assert len(ids) == len(set(ids)) == 27


def test_depth_changes_presentation():
    brief, balanced, deep = (
        plan_pages(fixture_snapshot(depth=d)) for d in ("brief", "balanced", "deep")
    )
    assert len(brief.front.briefs) > len(balanced.front.briefs) > len(deep.front.briefs)
    assert (
        len(brief.front.lead.summary)
        < len(balanced.front.lead.summary)
        < len(deep.front.lead.summary)
    )
    assert not balanced.front.lead.facts
    assert len(deep.front.lead.facts) == 3
    assert _full(brief) < _full(balanced)


def test_sections_follow_topic_weights_and_explore_comes_last():
    pakistan = plan_pages(fixture_snapshot(topics={"pakistan": 1.0}))
    culture = plan_pages(fixture_snapshot(topics={"culture": 1.0, "music": 1.0}))
    assert pakistan.sections[0].name == "Pakistan"
    assert culture.sections[0].name == "Culture"
    for plan in (pakistan, culture):
        assert plan.sections[-1].name == "Outside your bubble"
        assert plan.sections[-1].explore


def test_lead_is_the_composers_choice():
    edition, items, reader = fixture_records()
    chosen = items[7]["id"]
    edition["layout"]["lead_item_id"] = chosen
    plan = plan_pages(build_snapshot(edition, items, reader))
    assert plan.front.lead.story.item_id == chosen
