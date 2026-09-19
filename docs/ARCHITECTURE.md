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