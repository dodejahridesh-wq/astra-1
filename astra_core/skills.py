from dataclasses import dataclass

@dataclass
class Skill:
    name: str
    description: str
    status: str = "candidate"
    score: float = 0.0

class SkillRegistry:
    def __init__(self): self.skills={}
    def register_candidate(self, skill): self.skills[skill.name]=skill
    def evaluate(self, name, score):
        skill=self.skills[name]; skill.score=score; skill.status="promoted" if score>=.8 else "candidate"; return skill
