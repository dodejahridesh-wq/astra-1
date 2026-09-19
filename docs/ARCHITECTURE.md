# Astra-1 Architecture

Astra-1 separates the cognitive substrate from the persistent cognitive architecture and collective layer.

Core loop: **Goal -> Perceive -> Retrieve -> Model -> Plan -> Simulate -> Act -> Observe -> Verify -> Reflect -> Consolidate -> Learn**.

The foundation model is an interchangeable substrate. The organism layer owns persistent state, memory, world modeling, executive behavior, verification, metacognition, skills, governance and telemetry.

Simulation state must never silently become real-world state. Consequential actions require explicit authorization.

## Current runtime boundary

The deterministic prototype is now wrapped by a persistent runtime. SQLite stores execution records, ordered trace events, and episodic-memory records so an execution can be inspected after the in-process runtime is restarted.

A dependency-free HTTP service exposes three research-facing boundaries:

- `GET /health` — service health.
- `POST /run` — execute a goal through the deterministic runtime.
- `GET /trace/{execution_id}` — retrieve a persisted execution and its ordered events.

This is intentionally a local research service, not an unrestricted autonomous-action endpoint.

## Persistence rule

Durable state is treated as part of the cognitive architecture rather than an implementation detail. Future persistence work should extend this boundary to world-model state, task state, provenance, and memory lifecycle while retaining explicit versioning and auditability.


## Prospective intention layer

Astra-1 treats deferred intentions as a distinct durable state type rather than ordinary episodic memory. Each intention carries a typed cue (time, event, state, or manual), priority, lifecycle status, optional due time, provenance, payload, and optional bindings to goals, tasks, and executions.

The runtime exposes creation, cue polling, and completion operations. Polling is an explicit trigger step: an intention becomes `due` only when its typed cue is observed. The intention store does not itself authorize or perform consequential actions.

This separation reflects current prospective-memory research: deferred intentions require future-cue detection and lifecycle management, while long-term memory research shows that retrospective recall alone does not guarantee reliable future behavior.

## Temporal executive

The temporal executive is the wake-up boundary between durable prospective state and cognitive execution. A tick records the observed time, resolves eligible time/event cues, and optionally dispatches due intentions through the ordinary persistent runtime.

Every tick is durable and auditable. Dispatch does not bypass task state, execution state, simulation boundaries, verification, or governance. A failed or blocked execution leaves the intention non-completed rather than silently treating attempted work as success.

This gives Astra-1 an explicit temporal loop:

**Persist intention → observe cue → mark due → dispatch → execute → verify → complete or block → persist tick.**

A future scheduler may invoke ticks from a clock, event stream, or external orchestrator; the core executive itself remains deterministic and testable.

## Predictive world model and selective foresight

The world model now retains empirical action-to-outcome transitions and prediction errors. `SelectiveForesight` derives a prediction only when repeated observed transitions provide sufficient empirical confidence; unsupported actions produce no prediction.

Prediction is explicitly distinct from observation. A prediction carries its confidence, evidence count, and world-model version. When a prediction is later compared with an observation, the mismatch is retained as a prediction-error record rather than silently rewriting history.

This is intentionally conservative. Astra-1 does not treat a generated forecast as fact, and it does not use low-confidence foresight merely because a model can produce a plausible narrative. The design is informed by recent work on self-evolving world models, episodic/semantic memory, prediction-observation mismatch, and selective foresight.