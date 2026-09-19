from .models import DeterministicProvider
from .memory import MemorySystem
from .world import WorldModel
from .governance import assess_action
from .verification import verify
from .skills import SkillRegistry, Skill
from .collective import sign_packet
from .telemetry import Trace

class AstraOrganism:
    LOOP=("Goal","Perceive","Retrieve","Model","Plan","Simulate","Act","Observe","Verify","Reflect","Consolidate","Learn")
    def __init__(self, provider=None, identity="astra-1-sandbox"):
        self.identity=identity; self.provider=provider or DeterministicProvider(); self.memory=MemorySystem(); self.world=WorldModel(); self.skills=SkillRegistry(); self.trace=Trace()
    def run(self, goal):
        self.trace=Trace(); self.trace.emit("Goal",goal); self.trace.emit("Perceive","Received goal and initialized sandbox state.")
        self.trace.emit("Retrieve",f"{len(self.memory.retrieve(goal))} relevant memories")
        self.trace.emit("Model",self.provider.generate(goal).text)
        self.trace.emit("Plan",self.provider.generate(goal,"planner").text)
        self.trace.emit("Simulate","Simulated action has no external side effects.")
        decision=assess_action("sandbox-demo"); self.trace.emit("Act",decision.reason)
        event={"goal":goal,"action":"sandbox-demo","allowed":decision.allowed}; self.world.observe(event); self.trace.emit("Observe",str(event))
        result=verify(self.trace.events,"sandbox-demo"); self.trace.emit("Verify",result.notes)
        self.trace.emit("Reflect",self.provider.generate(goal,"reflector").text)
        self.memory.add("episodic",{"goal":goal,"trace":self.trace.events},"execution-trace",.95)
        self.memory.add("procedural","Use sandbox-demo workflow for low-risk validation.","learned-sandbox",.82)
        self.trace.emit("Consolidate","Execution trace stored in episodic memory.")
        skill=Skill("sandbox-demo","Validated low-risk sandbox execution workflow."); self.skills.register_candidate(skill); self.skills.evaluate(skill.name,.9); self.trace.emit("Learn","Candidate skill evaluated and promoted.")
        packet=sign_packet(self.identity,"Sandbox execution completed","execution-trace",.95); self.trace.emit("Collective",f"Knowledge packet signed: {packet.signature[:12]}...")
        return {"goal":goal,"verified":result.passed,"trace":self.trace.events}
