from multicast import *

#Oanh Tran 0296617186

class Replica:
    def __init__(self, replicaID, allReplicas):
        self.replicaID = replicaID
        self.allReplicas = allReplicas
        self.clock = 0
        self.holdbackQueue = []
        self.maxSeen = {rid: (-1, -1) for rid in allReplicas}
        self.delivered = set()
        self.store = {}

    # send -> receive
    def sendToReplicas(self, msg):
        for r in self.allReplicas:
            print(f"Sending to replica {r}: {msg}")

    def broadcastUpdate(self, updateID, op):
        self.clock += 1
        # timestamp carries clock and replica id
        ts = (self.clock, self.replicaID)
        msg = TOBCAST(updateID=updateID, op=op, ts=ts, senderID=self.replicaID)
        # sender has now seen its own timestamp
        self.maxSeen[self.replicaID] = ts
        # put own message in holdback too
        self.insertHoldback(msg)
        self.sendToReplicas(msg)

    def receiveTobcast(self, msg):
        # lamport update after receiving message
        self.clock = max(self.clock, msg.ts[0]) + 1
        # store message in holdback queue
        self.insertHoldback(msg)
        # sender up to this timestamp
        self.maxSeen[msg.senderID] = msg.ts
        ack = ACK(updateID=msg.updateID, ts=msg.ts, senderID=self.replicaID)
        self.sendToReplicas(ack)
        self.deliver()

    def receiveAck(self, ack):
        self.clock = max(self.clock, ack.ts[0]) + 1
        # replica sending the ack has made progress up to ack.ts
        self.maxSeen[ack.senderID] = ack.ts
        print(f"Replica {self.replicaID} received ACK: {ack}")
        self.deliver()

    #makes sure every replica delivers message in same order
    def deliverCheck(self, msg):
        for rid in self.allReplicas:
            if self.maxSeen[rid] <= msg.ts:
                return False
        return True

    def deliver(self):
        while len(self.holdbackQueue) > 0:
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

    #key value operations
    def apply(self, op):
        opType = op["type"]
        if opType == "put":
            key = op["key"]
            value = op["value"]
            self.store[key] = value
        elif opType == "append":
            key = op["key"]
            suffix = op["suffix"]
            current = self.store.get(key, "")
            self.store[key] = current + suffix

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
        