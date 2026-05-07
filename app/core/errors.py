from dataclasses import dataclass


@dataclass
class AppError(Exception):
    status: int
    code: str
    title: str
    detail: str
    instance: str = ""

    def __str__(self) -> str:
        return f"[{self.code}] {self.title}: {self.detail}"


@dataclass
class ValidationError(AppError):
    def __init__(self, detail: str = "Invalid request.", instance: str = "") -> None:
        super().__init__(
            status=422, code="E1001", title="Validation Error", detail=detail, instance=instance
        )


@dataclass
class ProviderError(AppError):
    @classmethod
    def timeout(cls, detail: str = "The AI provider timed out.") -> ProviderError:
        return cls(status=504, code="E2001", title="Provider Timeout", detail=detail)

    @classmethod
    def auth_failure(
        cls, detail: str = "Authentication with the AI provider failed."
    ) -> ProviderError:
        return cls(status=502, code="E2002", title="Provider Auth Failure", detail=detail)

    @classmethod
    def unavailable(cls, detail: str = "The AI provider is unavailable.") -> ProviderError:
        return cls(status=503, code="E2003", title="Provider Unavailable", detail=detail)

    @classmethod
    def bad_response(
        cls, detail: str = "The AI provider returned an invalid response."
    ) -> ProviderError:
        return cls(status=502, code="E2004", title="Invalid Provider Response", detail=detail)


@dataclass
class InternalError(AppError):
    def __init__(self, detail: str = "An unexpected error occurred.", instance: str = "") -> None:
        super().__init__(
            status=500,
            code="E3001",
            title="Internal Server Error",
            detail=detail,
            instance=instance,
        )
