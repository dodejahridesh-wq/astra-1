# Astra-1 Research Update — 2026-09-20

## Purpose

This note records the external research that informed the Phase 1.1 direction. It is a research synthesis, not a claim that Astra-1 implements all capabilities discussed by these sources.

## Findings

### 1. Persistent memory is a systems problem, not just retrieval

Recent survey work distinguishes agent memory by form, function, and dynamics, including factual, experiential, and working memory. It also highlights memory formation, evolution, retrieval, trustworthiness, and multimodal/multi-agent memory as active research areas.

Astra-1 response:
- durable provenance-bearing memory records
- explicit lifecycle status
- supersession and invalidation
- versioned knowledge metadata
- future consolidation/forgetting evaluation

Source:
https://arxiv.org/abs/2512.13564

### 2. Long-term memory must handle change and obsolete knowledge

Memora evaluates remembering, reasoning, and recommending over weeks-to-months of interaction and introduces a forgetting-aware metric that penalizes obsolete memories. LongMemEval-V2 evaluates environment experience such as dynamic state tracking, workflow knowledge, and environment-specific gotchas.

Astra-1 response:
- active/superseded/invalidated memory state is now explicit
- search excludes invalidated and superseded records
- supersession preserves provenance history rather than overwriting the old record

Sources:
https://arxiv.org/abs/2604.20006
https://arxiv.org/abs/2605.12493

### 3. Prospective memory is distinct from retrospective recall

PM-Bench isolates the problem of carrying out a deferred intention at the right future cue while other work continues. A September 2026 study reports that typed intention stores can materially improve this capability, suggesting that prospective memory should be represented as explicit state rather than left entirely to free-form context recall.

Astra-1 response:
- prospective memory is now a first-class roadmap item
- the next persistence milestone should introduce a typed intention store with explicit cue, lifecycle, due-state, and execution binding

Sources:
https://arxiv.org/abs/2607.12385
https://arxiv.org/abs/2609.01272

### 4. World models are moving toward explicit predictive components

Recent work explores world models that revise their predictive context from observed action transitions and prediction errors. Google DeepMind's Genie 3 demonstrates a different but related direction: interactive world simulation for agents and evaluation. Qwen-AgentWorld similarly treats environment simulation as a foundation capability for agentic systems.

Astra-1 response:
- retain a versioned explicit world model
- add confidence and provenance reconciliation
- investigate selective foresight instead of assuming every generated prediction is reliable
- keep simulation state separate from real state

Sources:
https://arxiv.org/abs/2606.30639
https://deepmind.google/models/genie/
https://arxiv.org/abs/2606.24597

### 5. Tool-use governance is becoming capability-aware and runtime-oriented

The current MCP specification defines tool metadata and recommends clear UI visibility and human control for tool invocation. Recent research on runtime interception and verifiable tool safety argues for pre-execution action checks rather than relying only on post-hoc evaluation.

Astra-1 response:
- capability metadata is now represented in the governance decision
- read-only, destructive, idempotent, and open-world characteristics can be carried with an action decision
- consequential/external/destructive operations remain blocked pending authorization
- future work should add richer policy evaluation and runtime interception

Sources:
https://modelcontextprotocol.io/specification/draft/server/index
https://arxiv.org/abs/2601.08012
https://arxiv.org/abs/2605.04785

### 6. Long-running agents require trajectory-level monitoring

OpenAI's 2026 work on long-horizon model safety describes failures that were not captured by earlier evaluations and the need for trajectory-level monitoring and greater user visibility. Its agent infrastructure also emphasizes durable state, sandboxing, snapshotting/rehydration, and separation of the harness from computation.

Astra-1 response:
- execution traces are durable and ordered
- execution state is explicit
- sandbox/live boundaries are explicit
- the next safety milestone should extend verification from single outcomes to whole trajectories and tool-call evidence

Sources:
https://openai.com/index/safety-alignment-long-horizon-models/
https://openai.com/index/the-next-evolution-of-the-agents-sdk/

## Architectural consequence

Astra-1 should not chase feature breadth by adding more agent tools first. The research points toward a stronger order:

**Persistent state → memory lifecycle → prospective intentions → predictive world model → pre-action governance → trajectory verification → richer tools/models**

That sequence preserves the project's original thesis: the durable cognitive architecture is the research object; foundation models are interchangeable cognitive substrates.
