from app.services.conversation_service import make_title


def test_make_title_short_message() -> None:
    assert make_title("Hello world") == "Hello world"


def test_make_title_collapses_whitespace() -> None:
    assert make_title("Hello\n\nworld") == "Hello world"


def test_make_title_truncates_long_message() -> None:
    title = make_title("x" * 100, max_length=20)
    assert len(title) == 20
    assert title.endswith("…")
