"""Prove the learning loop works: a synthetic reader with hidden tastes, a week of editions.

    python -m app.scripts.simulate_reader [--seed 7] [--readers 5] [--days 7] [--no-chart]

The reader secretly likes three of eight topics. Their onboarding profile is deliberately
imperfect (one right topic, one wrong one, a vague vector). Every day we compose an edition with
the real scorer and selector, the reader clicks, skips and sometimes says "more like this"
according to their hidden tastes, and the nightly learner updates the profile from those events.
We report precision@10 (share of the first ten stories the reader truly cares about) per day,
next to a control whose profile never learns. No database, network or LLM is involved.
"""

import argparse
import math
import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from app.models.enums import Depth
from app.personalize.config import DEFAULT_LEARNING, LearningConfig
from app.personalize.learn import Change, LearnerState, StoryFacts, learn
from app.personalize.score import score_all
from app.personalize.select import Selection, select_items
from app.personalize.signals import RawEvent, story_signals
from app.personalize.types import Candidate, ProfileView

TOPICS = ("technology", "ai", "markets", "sports", "health", "science", "politics", "culture")
DIM = 24
ARTICLES_PER_DAY = 80
SOURCES = 8
PEOPLE_PER_TOPIC = 4
PRECISION_AT = 10
CHART_PATH = Path(__file__).resolve().parents[4] / "docs" / "learning-curve.png"

# click behaviour of the hidden reader
P_OPEN_RELEVANT = 0.8
P_OPEN_OTHER = 0.04
P_MORE_LIKE = 0.15
P_SAVE = 0.06
P_SKIP_OTHER = 0.5
P_LESS_LIKE = 0.1


def _unit(v: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v]


def _noise(rng: random.Random, scale: float) -> list[float]:
    return [rng.gauss(0.0, scale) for _ in range(DIM)]


@dataclass(frozen=True, slots=True)
class World:
    """Everything a seed fixes: topic geometry, the reader's secret tastes, a week of articles."""

    centroids: dict[str, list[float]]
    liked: frozenset[str]
    wrong_topic: str
    days: list[list[Candidate]]
    primary: dict[UUID, str]
    source_ids: list[UUID]


def build_world(seed: int, days: int, per_day: int = ARTICLES_PER_DAY) -> World:
    rng = random.Random(seed)  # noqa: S311  (a seeded simulation, not security)
    centroids = {t: _unit([rng.gauss(0, 1) for _ in range(DIM)]) for t in TOPICS}
    shuffled = rng.sample(TOPICS, len(TOPICS))
    liked = frozenset(shuffled[:3])
    wrong = shuffled[3]
    source_ids = [UUID(int=rng.getrandbits(128)) for _ in range(SOURCES)]
    qualities = [0.6 + 0.04 * i for i in range(SOURCES)]
    start = datetime(2026, 10, 10, 5, 0, tzinfo=UTC)

    primary: dict[UUID, str] = {}
    corpus: list[list[Candidate]] = []
    n = 0
    for d in range(days):
        day: list[Candidate] = []
        for _ in range(per_day):
            n += 1
            topic = rng.choice(TOPICS)
            second = rng.choice([t for t in TOPICS if t != topic])
            who = f"{topic.title()} Person {rng.randrange(PEOPLE_PER_TOPIC)}"
            source = rng.randrange(SOURCES)
            cid = UUID(int=rng.getrandbits(128))
            primary[cid] = topic
            day.append(
                Candidate(
                    id=cid,
                    url=f"https://example.com/{n}",
                    title=f"{topic.title()} story {n}",
                    headline=f"{topic.title()} story {n}",
                    summary=f"A story about {topic}.",
                    key_facts=(),
                    source_id=source_ids[source],
                    source_name=f"Source {source}",
                    source_quality=qualities[source],
                    cluster_id=n,
                    cluster_size=rng.randint(1, 4),
                    topics={topic: 0.85, second: 0.3},
                    entities={"people": [who]},
                    embedding=_unit(
                        [c + e for c, e in zip(centroids[topic], _noise(rng, 0.12), strict=True)]
                    ),
                    published_at=start + timedelta(days=d) + timedelta(minutes=rng.randrange(120)),
                    image_url=None,
                )
            )
        corpus.append(day)
    return World(centroids, liked, wrong, corpus, primary, source_ids)


def onboarding_state(world: World) -> LearnerState:
    """What a reader who got only part of their tastes across in onboarding looks like."""
    right = sorted(world.liked)[0]
    vector = _unit(
        [
            a + b
            for a, b in zip(world.centroids[right], world.centroids[world.wrong_topic], strict=True)
        ]
    )
    return LearnerState(
        topics={right: 0.6, world.wrong_topic: 0.6},
        interest_vector=vector,
        entities={"people": [], "companies": [], "teams": [], "places": []},
    )


def view_of(state: LearnerState) -> ProfileView:
    return ProfileView(
        user_id=UUID(int=1),
        first_name="Sim",
        paper_name=None,
        city=None,
        timezone="UTC",
        topics=dict(state.topics),
        keywords=[],
        entities={k: list(v) for k, v in state.entities.items()},
        blocked_topics=frozenset(state.blocked_topics),
        blocked_keywords=(),
        blocked_sources=(),
        source_affinity=dict(state.source_affinity),
        reading_minutes=10,
        depth=Depth.BALANCED,
        surprise_me=True,
        interest_vector=state.interest_vector,
        context_notes=None,
        explore_rate=state.explore_rate,
    )


def compose(world: World, day: int, state: LearnerState) -> list[Selection]:
    now = datetime(2026, 10, 10, 6, 0, tzinfo=UTC) + timedelta(days=day)
    profile = view_of(state)
    return select_items(score_all(world.days[day], profile, now), profile)


def precision_at(world: World, picks: Sequence[Selection], k: int = PRECISION_AT) -> float:
    first = picks[:k]
    hits = sum(world.primary[p.scored.candidate.id] in world.liked for p in first)
    return hits / k


def read_edition(
    world: World, picks: Sequence[Selection], day: int, rng: random.Random
) -> list[RawEvent]:
    """The hidden reader's behaviour on one edition."""
    morning = datetime(2026, 10, 10, 8, 0, tzinfo=UTC) + timedelta(days=day)
    events: list[RawEvent] = []

    def add(kind: str, c: Candidate, minutes: int, value: float | None = None) -> None:
        events.append(
            RawEvent(kind, c.id, c.id, morning + timedelta(minutes=minutes), value)
        )  # one edition item per story: reuse the article id as the item id

    for rank, pick in enumerate(picks):
        c = pick.scored.candidate
        relevant = world.primary[c.id] in world.liked
        add("impression", c, rank)
        if rng.random() < (P_OPEN_RELEVANT if relevant else P_OPEN_OTHER):
            add("open", c, rank)
            add("dwell", c, rank + 1, rng.uniform(40, 120) if relevant else rng.uniform(5, 25))
            if relevant and rng.random() < P_MORE_LIKE:
                add("more_like", c, rank + 2)
            if relevant and rng.random() < P_SAVE:
                add("save", c, rank + 2)
        elif not relevant and rng.random() < P_SKIP_OTHER:
            add("skip", c, rank + 1)
            if rng.random() < P_LESS_LIKE:
                add("less_like", c, rank + 2)
    return events


def nightly(
    world: World,
    state: LearnerState,
    picks: Sequence[Selection],
    events: Sequence[RawEvent],
    day: int,
    cfg: LearningConfig = DEFAULT_LEARNING,
) -> tuple[LearnerState, list[Change]]:
    explore_ids = {p.scored.candidate.id for p in picks if p.explore}
    by_id = {p.scored.candidate.id: p.scored.candidate for p in picks}
    night = datetime(2026, 10, 10, 23, 0, tzinfo=UTC) + timedelta(days=day)
    signals = story_signals(events, night, cfg=cfg)
    pairs = []
    for s in signals:
        c = by_id[s.article_id]
        facts = StoryFacts(
            c.id,
            c.topics,
            c.entities,
            c.embedding,
            str(c.source_id) if c.source_id else None,
            explore=c.id in explore_ids,
        )
        pairs.append((s, facts))
    return learn(state, pairs, cfg, nightly=True)


@dataclass(slots=True)
class Result:
    learning: list[float] = field(default_factory=list)
    control: list[float] = field(default_factory=list)
    changes: int = 0


def simulate(seed: int, days: int = 7, cfg: LearningConfig = DEFAULT_LEARNING) -> Result:
    """One reader's week: precision@10 per day with the learner on, and with a frozen profile."""
    world = build_world(seed, days)
    learner = onboarding_state(world)
    frozen = onboarding_state(world)
    rng = random.Random(seed + 1)  # noqa: S311
    result = Result()
    for day in range(days):
        picks = compose(world, day, learner)
        result.learning.append(precision_at(world, picks))
        result.control.append(precision_at(world, compose(world, day, frozen)))
        events = read_edition(world, picks, day, rng)
        learner, changes = nightly(world, learner, picks, events, day, cfg)
        result.changes += len(changes)
    return result


def average(results: Sequence[Result]) -> Result:
    n = len(results)
    days = len(results[0].learning)
    return Result(
        learning=[sum(r.learning[d] for r in results) / n for d in range(days)],
        control=[sum(r.control[d] for r in results) / n for d in range(days)],
        changes=sum(r.changes for r in results),
    )


def draw_chart(result: Result, path: Path, readers: int) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    days = list(range(1, len(result.learning) + 1))
    fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=150)
    ax.plot(days, result.learning, marker="o", color="#1f5fa8", linewidth=2.2)
    ax.plot(days, result.control, marker="o", color="#8a8f98", linewidth=1.8, linestyle="--")
    ax.annotate(
        "with learning", (days[-1], result.learning[-1]), xytext=(8, 0),
        textcoords="offset points", ha="left", va="center", color="#1f5fa8",
        fontsize=10, fontweight="bold",
    )  # fmt: skip
    ax.annotate(
        "never updated", (days[-1], result.control[-1]), xytext=(8, 0),
        textcoords="offset points", ha="left", va="center", color="#5d636c", fontsize=10,
    )  # fmt: skip
    ax.set_ylim(0, 1.0)
    ax.set_xlim(0.7, days[-1] + 1.4)
    ax.set_xticks(days)
    ax.set_xlabel("Day")
    ax.set_ylabel(f"Precision@{PRECISION_AT}")
    ax.set_title(
        f"The paper gets more relevant over a week (mean of {readers} synthetic readers)",
        fontsize=11, loc="left",
    )  # fmt: skip
    ax.grid(axis="y", alpha=0.25)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.scripts.simulate_reader", description=__doc__
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--readers", type=int, default=5, help="readers to average over")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--out", type=Path, default=CHART_PATH)
    parser.add_argument("--no-chart", action="store_true")
    args = parser.parse_args(argv)

    runs = [simulate(args.seed + i, args.days) for i in range(args.readers)]
    mean = average(runs)
    print(f"precision@{PRECISION_AT}, mean of {args.readers} readers")
    print("day  learning  control")
    for d, (a, b) in enumerate(zip(mean.learning, mean.control, strict=True), start=1):
        print(f"{d:>3}  {a:8.2f}  {b:7.2f}")
    print(f"profile changes logged: {mean.changes}")
    if not args.no_chart:
        draw_chart(mean, args.out, args.readers)
        print(f"chart: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
