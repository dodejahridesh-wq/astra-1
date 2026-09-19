from dataclasses import dataclass
import hashlib, json

@dataclass(frozen=True)
class KnowledgePacket:
    sender: str
    claim: str
    provenance: str
    confidence: float
    signature: str

def sign_packet(sender, claim, provenance, confidence):
    body=json.dumps([sender,claim,provenance,confidence], sort_keys=True)
    return KnowledgePacket(sender,claim,provenance,confidence,hashlib.sha256(body.encode()).hexdigest())
