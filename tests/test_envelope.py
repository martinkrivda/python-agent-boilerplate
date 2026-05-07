import json
from datetime import datetime

from app.api.envelope import (
    FieldError,
    error_response,
    error_response_with_fields,
    ok,
)
from app.core.errors import ProviderError, ValidationError


def test_ok_returns_success_envelope():
    response = ok({"key": "value"})
    body = json.loads(response.body)
    assert body["success"] is True
    assert body["data"] == {"key": "value"}
    assert body["error"] is None
    assert "requestId" in body["meta"]
    assert "timestamp" in body["meta"]
    assert response.status_code == 200


def test_ok_custom_status_code():
    response = ok({"x": 1}, status_code=201)
    assert response.status_code == 201


def test_error_response_success_false():
    err = ProviderError.timeout()
    response = error_response(err, instance="/rest/v1/agent/run", request_id="req-1")
    body = json.loads(response.body)
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "E2001"
    assert body["error"]["status"] == 504
    assert body["error"]["requestId"] == "req-1"
    assert response.status_code == 504


def test_error_response_has_cache_control():
    err = ProviderError.timeout()
    response = error_response(err, instance="/test", request_id="r1")
    assert response.headers["cache-control"] == "no-store"


def test_timestamp_is_rfc3339_utc():
    response = ok({"x": 1})
    body = json.loads(response.body)
    ts = body["meta"]["timestamp"]
    assert ts.endswith("Z")
    datetime.fromisoformat(ts.replace("Z", "+00:00"))  # must not raise


def test_data_and_error_never_both_populated():
    ok_resp = json.loads(ok({"a": 1}).body)
    assert ok_resp["error"] is None
    assert ok_resp["data"] is not None

    err = ProviderError.unavailable()
    err_resp = json.loads(error_response(err, "/x", "r2").body)
    assert err_resp["data"] is None
    assert err_resp["error"] is not None


def test_validation_error_with_field_errors():
    fields = [FieldError(pointer="/message", message="Field required.", code="REQUIRED")]
    err = ValidationError(detail="Validation failed.")
    response = error_response_with_fields(err, fields=fields, instance="/test", request_id="r3")
    body = json.loads(response.body)
    assert body["error"]["errors"][0]["pointer"] == "/message"
    assert body["error"]["errors"][0]["code"] == "REQUIRED"
