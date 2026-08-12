from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class LLMResult(Generic[T]):
    data: T
    source: str  # "openai" | "fallback"
    error: str | None = None
    fallback_reason: str | None = None

    @classmethod
    def from_openai(cls, data: T) -> "LLMResult[T]":
        return cls(data=data, source="openai")

    @classmethod
    def from_fallback(
        cls,
        data: T,
        *,
        error: str | None = None,
        reason: str | None = None,
    ) -> "LLMResult[T]":
        return cls(
            data=data,
            source="fallback",
            error=error,
            fallback_reason=reason or error,
        )
