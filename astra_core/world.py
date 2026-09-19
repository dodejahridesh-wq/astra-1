from dataclasses import dataclass, field

@dataclass
class WorldModel:
    entities: dict = field(default_factory=dict)
    relations: list = field(default_factory=list)
    events: list = field(default_factory=list)
    hypotheses: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    version: int = 0
    def observe(self, event):
        self.events.append(event); self.version += 1; return self.version
