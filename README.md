# Astra-1

> **What if the next generation of AI is not just a larger model — but a new cognitive architecture around models?**

Astra-1 is an open research platform for building **persistent cognitive AI systems**: model-agnostic runtimes that combine memory, world modeling, planning, verification, metacognition, skills, simulation, governance, and collective cognition.

### The idea

Current AI can be viewed as a powerful cognitive substrate. Astra-1 explores the layer above the substrate:

**Model → Cognitive Agent → Persistent Cognitive Organism → Collective Intelligence**

The project uses “organism” and “species” as architectural metaphors. Astra-1 makes **no claim of consciousness, sentience, biological life, or human equivalence**.

### Cognitive loop

```
Goal
  ↓
Perceive → Retrieve → Model → Plan → Simulate
  ↓
Act → Observe → Verify → Reflect
  ↓
Consolidate → Learn
  ↺
```

### What is already here

- Deterministic sandbox organism loop
- Persistent SQLite execution runtime
- Dependency-free local HTTP API for health, execution, and trace inspection
- Durable execution/event history
- Model-provider interface with a reproducible local substrate
- Working / episodic / semantic / procedural / autobiographical memory model
- Explicit versioned world model
- Executive action-governance gate
- First-class verification
- Candidate skill registry and promotion gate
- Provenance-tagged collective knowledge packets
- Execution telemetry
- Benchmark cases
- Threat model and system card
- GitHub Actions test workflow

### Why this project exists

Astra-1 is designed for researchers, engineers, AI builders, students, and curious people interested in what comes **after the standalone chatbot paradigm**.

The long-term research direction is to make the architecture:

- persistent across sessions
- able to use multiple model providers and specialist models
- capable of grounded retrieval and independent verification
- able to acquire reusable skills in a sandbox
- able to simulate futures without confusing simulation with reality
- able to coordinate multiple isolated instances with provenance
- measurable through reproducible cognitive benchmarks

### Run it

Requires Python 3.11+.

```bash
python -m unittest discover -s tests -v
python -m astra_core.demo
python benchmarks/run.py
python -m astra_core.service
```

The local service exposes:

- `GET /health`
- `POST /run` with `{"goal":"..." }`
- `GET /trace/{execution_id}`

The default persistent database is `data/astra.db`. No API key is required for the deterministic sandbox.

### Project status

**Early research / experimental.** The current implementation is intentionally small and inspectable. It is not presented as AGI or a production autonomous system.

### Discover and share

A public landing page is available in [`docs/index.html`](docs/index.html). The project also includes a [public outreach plan](docs/MARKETING.md), [launch draft](docs/LAUNCH_POST.md), [social copy](marketing/SOCIAL_COPY.md), and [GitHub growth setup](docs/GITHUB_SETUP.md).

### Get involved

Read [CONTRIBUTING.md](CONTRIBUTING.md), explore the [architecture](docs/ARCHITECTURE.md), review the [roadmap](docs/ROADMAP.md), and open an Issue or Discussion with experiments, critiques, benchmark ideas, or implementation proposals.

### Research and safety

See:

- [System Card](docs/SYSTEM_CARD.md)
- [Threat Model](docs/THREAT_MODEL.md)
- [Governance](GOVERNANCE.md)
- [Security Policy](SECURITY.md)
- [Architecture Decisions](docs/DECISIONS.md)

### Citation

If Astra-1 contributes to your research, see [CITATION.cff](CITATION.cff).

### License

Apache-2.0.
