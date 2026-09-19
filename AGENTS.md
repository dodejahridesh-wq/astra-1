# Astra-1 Agent Instructions

## Mission

Astra-1 is an open research platform for persistent cognitive AI architecture. Build the architecture around interchangeable foundation-model substrates rather than treating a single model as the whole system.

The progression is:

**Model -> Cognitive Agent -> Persistent Cognitive System -> Persistent Cognitive Organism Architecture -> Collective Intelligence**

"Organism" and "species" are architectural metaphors. Never claim consciousness, sentience, biological life, or human equivalence.

## Source of truth

- The Git repository is the implementation source of truth.
- Inspect existing code before changing it.
- Reconcile documentation with actual behavior.
- Never treat an aspirational roadmap item as implemented.
- Preserve provenance and existing working behavior unless a change is justified and tested.

## Engineering loop

For each coherent milestone:

1. Inspect the relevant implementation and tests.
2. Make the smallest coherent change.
3. Add or update tests.
4. Run the relevant tests.
5. Run the broader regression suite.
6. Repair failures at their root.
7. Update documentation and implementation status.
8. Commit the stable checkpoint.

Do not stop after the first successful feature when a clearly dependent engineering task remains.

## Research loop

Prefer:

**implementation -> experiment -> measurement -> evidence -> documentation**

over claims, prompts, or marketing language.

Never invent benchmark results, research results, users, partnerships, capabilities, or verification.

## Architecture principles

Maintain explicit boundaries between:

- model substrate and cognitive runtime
- working, episodic, semantic, procedural, and autobiographical memory
- world model and generated hypotheses
- simulation and live execution
- generated claims and verified evidence
- candidate skills and promoted skills
- individual identities and collective knowledge
- sandbox functionality and consequential external actions

Consequential or irreversible actions require explicit human authorization.

Candidate improvements must be sandboxed and benchmarked before promotion. Never implement uncontrolled self-replication or uncontrolled governance changes.

## Persistence

Important cognitive state should become durable rather than existing only in process memory.

Persist execution identity, task state, provenance, traces, and other state when the architecture requires continuity across restarts.

## Model providers

Keep model access behind explicit provider interfaces. Support deterministic/local substitutes so the project remains reproducible without credentials. Never commit secrets.

## Testing

Never claim a test passed unless it was actually run.

When external services or credentials are unavailable, test the deterministic/local path and document the limitation.

## Documentation

When architecture or behavior changes, update:

- README when user-facing behavior changes
- docs/ARCHITECTURE.md for architecture changes
- docs/IMPLEMENTATION_STATUS.md for implementation status
- docs/ROADMAP.md for milestone changes
- docs/DECISIONS.md for durable architectural decisions

## Git hygiene

Use small, meaningful commits. Do not commit secrets, credentials, personal data, temporary artifacts, or generated junk. Do not rewrite history merely for cosmetic reasons.

## Long-running sessions

Maintain enough persistent project state that another Codex session can resume from the repository alone. Use AGENTS.md, implementation status, roadmap, decision log, tests, and Git history as recovery points.

Only ask the human to decide when the choice is genuinely irreversible, destructive, security-sensitive, financially consequential, or changes the project's fundamental research direction.
