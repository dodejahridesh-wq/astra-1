from dataclasses import dataclass

@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    evidence: list
    notes: str

def verify(trace, expected_event):
    matches=[e for e in trace if expected_event in str(e)]
    return VerificationResult(bool(matches), matches, "Verified against execution trace." if matches else "Expected event not found.")
