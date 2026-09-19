from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class ModelResponse:
    text: str
    confidence: float
    provenance: str = "sandbox-model"

class ModelProvider(Protocol):
    name: str
    def generate(self, prompt: str, role: str = "general") -> ModelResponse: ...

class DeterministicProvider:
    name = "deterministic-sandbox"
    def generate(self, prompt: str, role: str = "general") -> ModelResponse:
        outputs = {
            "planner": ("Decompose the goal, execute the lowest-risk step, observe, verify, then consolidate.", .95),
            "verifier": ("Verification completed against available sandbox evidence.", .90),
            "reflector": ("Reflection found no blocking contradiction in the sandbox trace.", .88),
        }
        text, confidence = outputs.get(role, (f"Sandbox response for: {prompt}", .80))
        return ModelResponse(text, confidence)
