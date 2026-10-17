from app.ingest.fetchers.google_news import PAKISTAN, US
from app.ingest.queries import MAX_QUERIES, NewsQuery, ReaderInterests, build_queries


def _reader(keywords: list[str], tz: str = "UTC", **entities: list[str]) -> ReaderInterests:
    return ReaderInterests(keywords=keywords, entities=entities, timezone=tz)


def test_union_is_deduped_case_insensitively_across_readers() -> None:
    queries = build_queries(
        [
            _reader(["Large Language Models", "PSL"], companies=["Anthropic"]),
            _reader(["large language models"], companies=["anthropic", "Nvidia"]),
        ]
    )
    texts = [q.text.casefold() for q in queries]
    assert sorted(texts) == sorted(set(texts))
    assert set(texts) == {"large language models", "psl", "anthropic", "nvidia"}


def test_most_wanted_terms_come_first() -> None:
    queries = build_queries(
        [_reader(["zebra", "common"]), _reader(["common"]), _reader(["common"])]
    )
    assert queries[0].text == "common"


def test_pakistan_readers_also_get_the_local_edition() -> None:
    queries = build_queries(
        [_reader(["PSL"], tz="Asia/Karachi"), _reader(["NASA"], tz="Europe/Paris")]
    )
    assert NewsQuery("PSL", US) in queries
    assert NewsQuery("PSL", PAKISTAN) in queries
    assert NewsQuery("NASA", PAKISTAN) not in queries


def test_capped_at_one_hundred() -> None:
    reader = _reader([f"topic {i:03d}" for i in range(250)])
    assert len(build_queries([reader])) == MAX_QUERIES == 100


def test_blank_and_tiny_terms_are_ignored() -> None:
    queries = build_queries([_reader(["", "  ", "ai", "  spaced   out  "])])
    assert [q.text for q in queries] == ["spaced out"]


def test_no_readers_means_no_queries() -> None:
    assert build_queries([]) == []
