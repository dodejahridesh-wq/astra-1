# Architecture Decision Log

1. Model/provider independence.
2. Explicit inspectable memory.
3. Verification as a first-class subsystem.
4. Strict simulation/real-state separation.
5. Sandboxed candidate evolution.
6. Separate identities in collective cognition.
7. Deterministic fallback for reproducible testing.


## Decision: durable runtime before interface expansion

Astra-1 will prioritize durable execution state, explicit execution modes, evidence boundaries, retrieval abstractions, and provider routing before building a feature-heavy research UI. This keeps the interface downstream of measurable runtime capabilities and makes the architecture usable by both humans and autonomous engineering agents.

## Decision: simulation is not live action

SANDBOX and SIMULATION are non-side-effect modes. LIVE is an explicit mode and is blocked by the current governance layer unless a future authorization mechanism grants the required permission. The runtime must never infer authorization merely from a model-generated plan.
