from pathlib import Path

import pytest

from app.models.enums import Depth
from app.personalize.config import DEFAULT_SELECTION
from app.personalize.score import score_all
from app.personalize.select import explore_count, select_items
from app.scripts.simulate_reader import (
    average,
    build_world,
    draw_chart,
    main,
    onboarding_state,
    precision_at,
    simulate,
    view_of,
)

SEEDS = range(7, 12)


def test_the_curve_rises_over_a_week_for_a_single_reader() -> None:
    result = simulate(7)
    assert len(result.learning) == 7
    assert result.learning[-1] > result.learning[0]


def test_day_seven_beats_day_one_on_average_and_beats_a_frozen_profile() -> None:
    mean = average([simulate(seed) for seed in SEEDS])
    assert mean.learning[6] > mean.learning[0] + 0.2
    assert mean.learning[6] > mean.control[6] + 0.2
    assert mean.learning[0] == pytest.approx(mean.control[0])  # same starting profile
    assert mean.changes > 0


def test_the_simulation_is_deterministic() -> None:
    assert simulate(3) == simulate(3)


def test_the_world_hides_three_liked_topics_and_onboarding_gets_one_wrong() -> None:
    world = build_world(7, 7)
    assert len(world.liked) == 3
    assert world.wrong_topic not in world.liked
    state = onboarding_state(world)
    assert world.wrong_topic in state.topics
    assert len(world.days) == 7


def test_precision_is_the_share_of_the_first_ten_the_reader_cares_about() -> None:
    world = build_world(7, 2)
    state = onboarding_state(world)
    profile = view_of(state)
    assert profile.depth is Depth.BALANCED
    picks = select_items(score_all(world.days[0], profile, world.days[0][0].published_at), profile)
    value = precision_at(world, picks)
    assert 0.0 <= value <= 1.0
    assert value * 10 == int(value * 10)


def test_cli_prints_a_table_and_writes_the_chart(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "curve.png"
    assert main(["--readers", "1", "--out", str(out)]) == 0
    assert out.read_bytes().startswith(b"\x89PNG")
    printed = capsys.readouterr().out
    assert "precision@10" in printed
    assert printed.count("\n") >= 9


def test_cli_can_skip_the_chart(tmp_path: Path) -> None:
    out = tmp_path / "none.png"
    assert main(["--readers", "1", "--no-chart", "--out", str(out)]) == 0
    assert not out.exists()


def test_chart_can_be_drawn_directly(tmp_path: Path) -> None:
    draw_chart(average([simulate(7, 3)]), tmp_path / "sub" / "c.png", 1)
    assert (tmp_path / "sub" / "c.png").exists()


def test_explore_rate_from_the_profile_shrinks_the_explore_share() -> None:
    state = onboarding_state(build_world(7, 1))
    base = explore_count(40, DEFAULT_SELECTION, view_of(state))
    state.explore_rate = 0.05
    assert explore_count(40, DEFAULT_SELECTION, view_of(state)) < base
    assert explore_count(40, DEFAULT_SELECTION, view_of(state)) == 2
