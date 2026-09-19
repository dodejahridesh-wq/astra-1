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

## Decision: one authoritative persistence runtime

The reconciliation phase retains `astra_core` as the authoritative runtime package. The persistence layer uses one explicit, monotonic SQLite schema version and migration path rather than maintaining parallel storage implementations. Existing remote execution, world-model, governance, scheduler, verification, and service behavior remains the integration baseline; local improvements are ported selectively when they strengthen that baseline without introducing a second runtime.

## Decision: migration compatibility is a release gate

A persistence change is not considered complete until a fresh database reaches the latest schema and a representative legacy database migrates without loss of existing executions, memories, tasks, and world data. Migration tests are part of the normal regression suite and benchmark gate.


## Decision: prospective memory is a separate state layer

Deferred intentions will not be represented solely as episodic memories. Astra-1 uses a typed intention store with explicit cue type, lifecycle, priority, due state, provenance, and execution binding. The store can make an intention eligible when a cue is observed, but it cannot grant action authority or perform consequential actions by itself.

This keeps retrospective memory, prospective intention state, and execution authorization distinct and inspectable.

## Decision: prediction errors revise hypotheses, not history

Prediction errors are retained as immutable evidence. When the same action, predicted outcome, and observed contradictory outcome recur at least twice, Astra-1 may create a provenance-tagged transition-rule revision. The superseded hypothesis is marked revised and the new hypothesis becomes active; subsequent matching evidence updates the existing revision rather than creating duplicates.

This boundary deliberately separates world-model adaptation from model-weight self-modification and from permission changes. Any future adaptive policy must preserve the evidence trail and pass deterministic regression tests.
