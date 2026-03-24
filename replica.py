from multicast import *

# Oanh Tran 0296617186

class Replica:
    def __init__(self, replicaID, allReplicas):
        self.replicaID = replicaID
        self.allReplicas = allReplicas   # dict: id -> Replica
        self.clock = 0
        self.holdbackQueue = []
        self.maxSeen = {rid: (-1, -1) for rid in allReplicas}
        self.delivered = set()
        self.store = {}

    def sendToReplicas(self, msg):
        for rid, replica in self.allReplicas.items():
            if rid == self.replicaID:
                continue
            if isinstance(msg, TOBCAST):
                replica.receiveTobcast(msg)
            elif isinstance(msg, ACK):
                replica.receiveAck(msg)

    def broadcastUpdate(self, updateID, op):
        # Required TOBCAST timestamp rule
        self.clock += 1
        ts = (self.clock, self.replicaID)
        msg = TOBCAST(updateID=updateID, op=op, ts=ts, senderID=self.replicaID)
        # sender sees its own multicast
        self.insertHoldback(msg)
        self.maxSeen[self.replicaID] = max(self.maxSeen[self.replicaID], ts)
        # send TOBCAST to other replicas
        self.sendToReplicas(msg)
        # try delivery after local insert / later ACKs arrive
        self.deliver()

    def receiveTobcast(self, msg):
        # Lamport receive rule
        self.clock = max(self.clock, msg.ts[0]) + 1
        self.insertHoldback(msg)
        self.maxSeen[msg.senderID] = max(self.maxSeen[msg.senderID], msg.ts)
        # ACK is also a send event, so timestamp it
        self.clock += 1
        ackTs = (self.clock, self.replicaID)
        self.maxSeen[self.replicaID] = max(self.maxSeen[self.replicaID], ackTs)
        ack = ACK(updateID=msg.updateID, ts=ackTs, senderID=self.replicaID)
        self.sendToReplicas(ack)

        self.deliver()

    def receiveAck(self, ack):
        self.clock = max(self.clock, ack.ts[0]) + 1
        self.maxSeen[ack.senderID] = max(self.maxSeen[ack.senderID], ack.ts)
        self.deliver()

    #check is appropriate to deliver
    def deliverCheck(self, msg):
        for rid in self.allReplicas:
            if self.maxSeen[rid] <= msg.ts:
                return False
        return True

    def deliver(self):
        while self.holdbackQueue:
            head = self.holdbackQueue[0]

            if head.updateID in self.delivered:
                self.holdbackQueue.pop(0)
                continue

            if not self.deliverCheck(head):
                break

            self.holdbackQueue.pop(0)
            self.apply(head.op)
            self.delivered.add(head.updateID)

            print(f"Replica {self.replicaID} delivered {head.updateID} {head.op} at ts={head.ts}")

    def apply(self, op):
        opType = op["type"]
        if opType == "put":
            self.store[op["key"]] = op["value"]

        elif opType == "append":
            key = op["key"]
            current = self.store.get(key, "")
            self.store[key] = current + op["suffix"]

        elif opType == "incr":
            key = op["key"]
            current = self.store.get(key, 0)
            self.store[key] = current + 1

        else:
            raise ValueError(f"Unknown operation type: {opType}")

    def insertHoldback(self, msg):
        for existing in self.holdbackQueue:
            if existing.updateID == msg.updateID:
                return
        self.holdbackQueue.append(msg)
        self.holdbackQueue.sort(key=lambda m: m.ts)