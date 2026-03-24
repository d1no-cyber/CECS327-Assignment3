from dataclasses import dataclass

@dataclass
class TOBCAST:
    updateID: str
    op: dict
    ts: tuple #(clock, replicaID)
    senderID: int
    
    
@dataclass
class ACK:
    updateID: str
    ts: tuple
    senderID: int