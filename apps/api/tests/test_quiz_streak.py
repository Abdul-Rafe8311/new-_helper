from datetime import date

from app.services.quiz import streak_from_days

TODAY = date(2026, 10, 17)


def days(*offsets: int) -> set[date]:
    return {date.fromordinal(TODAY.toordinal() - n) for n in offsets}


def test_no_finished_quiz_is_a_streak_of_zero() -> None:
    assert streak_from_days(set(), TODAY) == 0


def test_the_streak_grows_with_each_consecutive_day() -> None:
    assert streak_from_days(days(0), TODAY) == 1
    assert streak_from_days(days(0, 1), TODAY) == 2
    assert streak_from_days(days(0, 1, 2, 3), TODAY) == 4


def test_today_still_open_keeps_yesterdays_streak() -> None:
    assert streak_from_days(days(1, 2), TODAY) == 2


def test_a_missed_day_resets_the_streak_to_zero() -> None:
    assert streak_from_days(days(2, 3, 4), TODAY) == 0  # yesterday and today both missed


def test_a_gap_ends_the_streak() -> None:
    assert streak_from_days(days(0, 1, 3, 4, 5), TODAY) == 2
