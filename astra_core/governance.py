from dataclasses import dataclass


@dataclass(frozen=True)
class ActionDecision:
    allowed: bool
    requires_human: bool
    risk: str
    reason: str
    capability: str = "local"
    read_only: bool = False
    destructive: bool = False
    idempotent: bool = False
    open_world: bool = False


def assess_action(
    action,
    irreversible: bool = False,
    external: bool = False,
    *,
    capability: str = "local",
    read_only: bool = False,
    destructive: bool = False,
    idempotent: bool = False,
    open_world: bool = False,
):
    """Evaluate an action before execution using explicit capability metadata.

    The metadata is descriptive policy input, not proof of safety. External,
    irreversible, or destructive operations remain blocked pending explicit
    human authorization.
    """
    if not capability or not str(capability).strip():
        raise ValueError("capability must be a non-empty string")

    high_risk = irreversible or external or destructive
    if high_risk:
        reasons = []
        if external:
            reasons.append("external")
        if irreversible:
            reasons.append("irreversible")
        if destructive:
            reasons.append("destructive")
        detail = ", ".join(reasons)
        return ActionDecision(
            False,
            True,
            "high",
            f"Action '{action}' is blocked because it is {detail} and requires explicit human approval.",
            capability,
            read_only,
            destructive,
            idempotent,
            open_world,
        )

    risk = "low" if read_only and not open_world else "moderate" if open_world else "low"
    return ActionDecision(
        True,
        False,
        risk,
        "Non-consequential local action is permitted by the current sandbox policy.",
        capability,
        read_only,
        destructive,
        idempotent,
        open_world,
    )
