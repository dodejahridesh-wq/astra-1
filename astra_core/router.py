"""Model routing without coupling Astra-1 to a single provider."""
from dataclasses import dataclass

from .models import ModelProvider, ModelResponse


@dataclass(frozen=True)
class Route:
    role: str
    provider_name: str


class ModelRouter:
    def __init__(self, default: ModelProvider, specialists: dict[str, ModelProvider] | None = None):
        self.default = default
        self.specialists = specialists or {}

    def provider_for(self, role: str) -> ModelProvider:
        return self.specialists.get(role, self.default)

    def generate(self, prompt: str, role: str = "general") -> ModelResponse:
        return self.provider_for(role).generate(prompt, role)
