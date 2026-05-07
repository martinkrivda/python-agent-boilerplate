import time
import openai
import structlog
from openai import AsyncOpenAI

from app.ai.model_client import ChatMessage, GenerateParams, GenerateResult, ModelClient
from app.core.config import Settings
from app.core.errors import ProviderError
from app.core.metrics import Metrics, get_metrics

log = structlog.get_logger()


class OpenAICompatibleModelClient(ModelClient):
    def __init__(self, settings: Settings, metrics: Metrics | None = None) -> None:
        extra_headers: dict[str, str] = {}
        if settings.openrouter_http_referer:
            extra_headers["HTTP-Referer"] = settings.openrouter_http_referer
        if settings.openrouter_title:
            extra_headers["X-Title"] = settings.openrouter_title

        self._client = AsyncOpenAI(
            base_url=settings.ai_base_url,
            api_key=settings.ai_api_key,
            timeout=float(settings.ai_request_timeout),
            default_headers=extra_headers if extra_headers else None,
        )
        self._provider = settings.ai_provider
        self._model = settings.ai_model
        self._metrics = metrics or get_metrics()

    async def generate(
        self,
        messages: list[ChatMessage],
        params: GenerateParams,
    ) -> GenerateResult:
        self._metrics.record_ai_request(self._provider, self._model)
        start = time.monotonic()
        try:
            completion = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=params.temperature,
                max_tokens=params.max_tokens,
            )
            content = completion.choices[0].message.content or ""
            usage = dict(completion.usage) if completion.usage else None
            return GenerateResult(
                content=content,
                provider=self._provider,
                model=completion.model or self._model,
                usage=usage,
            )
        except openai.APITimeoutError as exc:
            self._metrics.record_ai_error(self._provider, self._model)
            raise ProviderError.timeout() from exc
        except openai.AuthenticationError as exc:
            self._metrics.record_ai_error(self._provider, self._model)
            raise ProviderError.auth_failure() from exc
        except openai.APIConnectionError as exc:
            self._metrics.record_ai_error(self._provider, self._model)
            raise ProviderError.unavailable() from exc
        except openai.APIStatusError as exc:
            self._metrics.record_ai_error(self._provider, self._model)
            if exc.status_code in (401, 403):
                raise ProviderError.auth_failure() from exc
            raise ProviderError.bad_response(detail=f"Provider returned status {exc.status_code}.") from exc
        except Exception as exc:
            self._metrics.record_ai_error(self._provider, self._model)
            log.error("unexpected_provider_error", exc_info=True)
            raise ProviderError.bad_response() from exc
        finally:
            self._metrics.observe_ai_duration(self._provider, self._model, time.monotonic() - start)
