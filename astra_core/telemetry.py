from dataclasses import dataclass, field
from time import perf_counter

@dataclass
class Trace:
    events:list=field(default_factory=list)
    started:float=field(default_factory=perf_counter)
    def emit(self, stage, detail): self.events.append({"stage":stage,"detail":detail})
    @property
    def elapsed(self): return perf_counter()-self.started
