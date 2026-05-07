import pytest
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry

from app.ai.model_client import ChatMessage, GenerateParams, GenerateResult, ModelClient
from app.api.dependencies import get_model_client


class FakeModelClient(ModelClient):
    async def generate(self, messages: list[ChatMessage], params: GenerateParams) -> GenerateResult:
        return GenerateResult(
            content="fake answer", provider="fake", model="fake-model", usage={"total_tokens": 10}
        )


class RaisesModelClient(ModelClient):
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def generate(self, messages: list[ChatMessage], params: GenerateParams) -> GenerateResult:
        raise self._exc


@pytest.fixture
def fake_model_client():
    return FakeModelClient()


@pytest.fixture
def raises_model_client():
    def factory(exc: Exception) -> RaisesModelClient:
        return RaisesModelClient(exc)

    return factory


@pytest.fixture
def metrics_registry():
    return CollectorRegistry()


@pytest.fixture
def app(fake_model_client):
    from app.ai.model_settings import ModelSettings
    from app.core.config import Settings
    from app.main import app as fastapi_app

    fastapi_app.dependency_overrides[get_model_client] = lambda: fake_model_client
    fastapi_app.state.model_client = fake_model_client
    fastapi_app.state.model_settings = ModelSettings.from_settings(Settings())
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
