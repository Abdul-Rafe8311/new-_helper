from pydantic import BaseModel


class QuizStreakOut(BaseModel):
    """Consecutive days the reader finished the quiz, counted back from today (or yesterday while
    today's quiz is still open); ``done_today`` says which."""

    streak: int
    done_today: bool
