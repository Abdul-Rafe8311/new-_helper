import pytest

from app.ai.embedder import FakeEmbedder, FastEmbedEmbedder, article_embedding_text, cosine


def test_fake_embedder_is_deterministic_and_normalised() -> None:
    e = FakeEmbedder()
    a, b = e.embed(["Fed cuts rates", "Fed cuts rates"])
    assert a == b
    assert len(a) == 384
    assert cosine(a, a) == pytest.approx(1.0)


def test_fake_embedder_similarity_follows_shared_words() -> None:
    e = FakeEmbedder()
    base, near, far = e.embed(
        ["central bank raises interest rates again", "central bank raises rates", "cricket final"]
    )
    assert cosine(base, near) > 0.7 > cosine(base, far)


def test_embedding_text_truncates_body_to_400_words() -> None:
    content = " ".join(f"w{i}" for i in range(1000))
    text = article_embedding_text("Title", "Excerpt", content)
    assert text.splitlines()[:2] == ["Title", "Excerpt"]
    assert len(text.splitlines()[2].split()) == 400
    assert article_embedding_text("T", None, None) == "T"


def test_fastembed_is_lazy_and_handles_empty_input() -> None:
    embedder = FastEmbedEmbedder()
    assert embedder.embed([]) == []  # must not load the model
    assert FastEmbedEmbedder._models == {}
