from app.core.request_context import get_request_id, reset_request_id, set_request_id


def test_set_and_get_request_id():
    token = set_request_id("abc-123")
    assert get_request_id() == "abc-123"
    reset_request_id(token)


def test_default_request_id_is_empty():
    assert get_request_id() == ""


def test_reset_restores_previous():
    token = set_request_id("first")
    assert get_request_id() == "first"
    reset_request_id(token)
    assert get_request_id() == ""
