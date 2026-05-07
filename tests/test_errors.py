from app.core.errors import AppError, InternalError, ProviderError, ValidationError


def test_provider_error_timeout():
    err = ProviderError.timeout()
    assert err.status == 504
    assert err.code == "E2001"


def test_provider_error_auth():
    err = ProviderError.auth_failure()
    assert err.status == 502
    assert err.code == "E2002"


def test_provider_error_unavailable():
    err = ProviderError.unavailable()
    assert err.status == 503
    assert err.code == "E2003"


def test_provider_error_bad_response():
    err = ProviderError.bad_response()
    assert err.status == 502
    assert err.code == "E2004"


def test_internal_error():
    err = InternalError()
    assert err.status == 500
    assert err.code == "E3001"


def test_validation_error():
    err = ValidationError(detail="bad input")
    assert err.status == 422
    assert err.code == "E1001"


def test_app_error_is_exception():
    err = ProviderError.timeout()
    assert isinstance(err, Exception)
    assert isinstance(err, AppError)
