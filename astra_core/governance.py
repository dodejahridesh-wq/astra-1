from dataclasses import dataclass

@dataclass(frozen=True)
class ActionDecision:
    allowed: bool
    requires_human: bool
    risk: str
    reason: str

def assess_action(action, irreversible=False, external=False):
    if irreversible or external:
        return ActionDecision(False, True, "high", "Consequential or external action requires explicit human approval.")
    return ActionDecision(True, False, "low", "Sandbox/local action is permitted.")
