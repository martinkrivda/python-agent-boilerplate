from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class GenerateParams:
    temperature: float = 0.7
    max_tokens: int = 1024


@dataclass
class GenerateResult:
    content: str
    provider: str
    model: str
    usage: dict | None = None


class ModelClient(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: list[ChatMessage],
        params: GenerateParams,
    ) -> GenerateResult: ...
