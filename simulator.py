import threading
import time
import random
from collections import defaultdict
from queue import Queue

# Sovannmonyrotn Kun 033159813

channels = {}
channelsLock = threading.Lock()

# This function will create a queue and worker per pair in First In First Out order to ensures delivery
def getChannel(senderId, receiverId):
    key = (senderId, receiverId)
    with channelsLock:
        if key not in channels:
            queue = Queue()
            channels[key] = queue
            thread = threading.Thread(target=channelWorker, args=(queue, ))
            thread.start()
    return channels[key]

def channelWorker(queue): # This function will process message one at a time with simulated network latency
    while True:
        item = queue.get()
        if item is None:  # If queue is empty, tell worker to quit
            break
        delay, replica, message = item
        time.sleep(delay)
        replica.receiveMessage(message)
        queue.task_done()

def waitForNetwork(): # This function will be to join all channels and repeat it until there's no new one and all queues are drained
    while True:
        with channelsLock:
            seen = set(channels.keys())
            channel = list(channels.values())
        for queue in channel:
            queue.join()
        with channelsLock:
            if set(channels.keys()) == seen:
                for queue in channel:
                    queue.join()
                break

class Message:  # TOBCAST
    def __init__(self, updateID, operation, timestamp, sender):
        self.updateID = updateID # ID for update
        self.operation = operation # Dictionary with type, key, and value/suffix
        self.timestamp = timestamp # Lamport timestamp as tuple (clock, replicaID)
        self.sender = sender # Replica ID

class ACK:
    def __init__(self, updateID, timestamp, sender):
        self.updateID = updateID # ID of the update being acknowledged
        self.timestamp = timestamp # stores clock and replicaID
        self.sender = sender # Replica ID

class Replica:
    def __init__(self, replicaID, totalReplicas):
        self.replicaID = replicaID
        self.clock = 0 # Lamport clock for simulation
        self.totalReplicas = totalReplicas
        self.holdback = [] # Sorted list by timestamp tuple
        self.maxSeen = defaultdict(lambda: (-1, -1)) # Largest timestamp seen from each replica
        self.store = {}  # For storing replicated key-value
        self.delivered = set() # Delivered update IDs
        self.deliverLog = [] # Logs for ordered delivery
        self.lock = threading.RLock()
        self.allReplicas = None

    def insertHoldback(self, message): # This function will insert messages into the holdback queue and also sorting them
        for existing in self.holdback:
            if existing.updateID == message.updateID:
                return
        self.holdback.append(message)
        self.holdback.sort(key=lambda msg: msg.timestamp)  # Total order by (clock, replicaID)

    def incrementClock(self):
        self.clock += 1

    def updateClock(self, timestamp):
        self.clock = max(self.clock, timestamp[0]) + 1

    def broadcast(self, updateID, operation, replicas): # This function will broadcast TOBCAST to all replicas
        with self.lock:
            self.incrementClock()
            ts = (self.clock, self.replicaID)
            msg = Message(updateID, operation, ts, self.replicaID)
            self.insertHoldback(msg)
            for replica in replicas:
                if replica.replicaID != self.replicaID:
                    simulateNetwork(self.replicaID, replica, msg)
            self.incrementClock()
            ackTs = (self.clock, self.replicaID)
            self.maxSeen[self.replicaID] = max(self.maxSeen[self.replicaID], ackTs)
            ack = ACK(updateID, ackTs, self.replicaID)
            for replica in replicas:
                if replica.replicaID != self.replicaID:
                    simulateNetwork(self.replicaID, replica, ack)
            self.tryDeliver()

    def receiveMessage(self, message): # This function will handle both TOBCAST and ACK
        with self.lock:
            if isinstance(message, Message):
                self.updateClock(message.timestamp)
                self.insertHoldback(message)
                self.maxSeen[message.sender] = max(self.maxSeen[message.sender], message.timestamp)
                # Send ACK to all other replicas
                self.incrementClock()
                ackTs = (self.clock, self.replicaID)
                self.maxSeen[self.replicaID] = max(self.maxSeen[self.replicaID], ackTs)
                ack = ACK(message.updateID, ackTs, self.replicaID)
                for replica in self.allReplicas:
                    if replica.replicaID != self.replicaID:
                        simulateNetwork(self.replicaID, replica, ack)
            elif isinstance(message, ACK):
                self.updateClock(message.timestamp)
                self.maxSeen[message.sender] = max(self.maxSeen[message.sender], message.timestamp)
            self.tryDeliver()

    def tryDeliver(self): # This function will attemp to deliver messages from the holdback queue
        while self.holdback:
            head = self.holdback[0]
            if head.updateID in self.delivered:
                self.holdback.pop(0)
                continue
            checkDeliver = True  # Check to see if it is safe to deliver
            for i in range(self.totalReplicas):
                if self.maxSeen[i] <= head.timestamp:
                    checkDeliver = False
                    break
            if checkDeliver:
                self.holdback.pop(0)
                self.runOperation(head)
            else:
                break

    def runOperation(self, message):
        op = message.operation
        key = op["key"]
        operationType = op["type"]
        if operationType == "put":
            self.store[key] = op["value"]
        elif operationType == "append":
            self.store[key] = self.store.get(key, "") + op["suffix"]
        elif operationType == "incr":
            self.store[key] = self.store.get(key, 0) + 1
        self.delivered.add(message.updateID)
        self.deliverLog.append(message.updateID)
        print(f"Replica {self.replicaID}: DELIVER {message.updateID} (timestamp={message.timestamp}) -> {key}={self.store[key]}")

def simulateNetwork(senderId, replica, message):  # This function is use to simulate network with random delay
    delay = random.uniform(0.05, 0.8)
    q = getChannel(senderId, replica.replicaID)
    q.put((delay, replica, message))

def runSimulation(name, numberofReplicas, updates):
    global channels
    with channelsLock:
        channels = {}  # Resetting channels for each simulation
    print()
    print(f"Running: {name}")
    print()
    replicas = [Replica(i, numberofReplicas) for i in range(numberofReplicas)]
    for replica in replicas:
        replica.allReplicas = replicas # Give each replica a reference to all others
    threads = []
    for i in range(len(updates)):
        targetReplica, operation = updates[i]
        def startBroadcast(replica=targetReplica, updateId=f"update-{i}", op=operation):
            replicas[replica].broadcast(updateId, op, replicas)
        t = threading.Thread(target=startBroadcast)
        t.start()
        threads.append(t)
    for t in threads:
        t.join() # Waiting for all broadcasts to be initiated before draining the network
    waitForNetwork()
    with channelsLock:
        for q in channels.values():
            q.put(None)
    allStates = []
    for replica in replicas:
        allStates.append(dict(replica.store))
    allDeliveries = []
    for replica in replicas:
        allDeliveries.append(list(replica.deliverLog))
    print()
    print("Final States:")
    for i in range(len(allStates)):
        print(f"Replica {i}: {allStates[i]}")
    print()
    print("Delivery Orders:")
    for i in range(len(allDeliveries)):
        print(f"Replica {i}: {allDeliveries[i]}")
    initialState = allStates[0]
    statesStatus = True
    for state in allStates:
        if state != initialState:
            statesStatus = False
            break
    if not statesStatus:
        print("ERROR: States Diverged!")
    else:
        print("All replica states are consistent.")
    initialDelivery = allDeliveries[0]
    deliveriesStatus = True
    for delivery in allDeliveries:
        if delivery != initialDelivery:
            deliveriesStatus = False
            break
    if not deliveriesStatus:
        print("ERROR: Delivery Order mismatch!")
    else:
        print("All replicas delivered updates in the same order.")

# Experiments
def experiment1(): # Conflicting Experiment
    random.seed(10)
    updates = [
        (0, {"type": "append", "key": "x", "suffix": "A"}),
        (1, {"type": "append", "key": "x", "suffix": "B"}),
        (2, {"type": "append", "key": "x", "suffix": "C"}),
    ]
    runSimulation("Concurrent Conflicting Updates", 3, updates)

def experiment2(): # High Contention Experiment
    random.seed(99)
    updates = []
    for _ in range(30):
        replica_id = random.randint(0, 3)
        updates.append((replica_id, {"type": "incr", "key": "count"}))
    runSimulation("High Contention (30 updates)", 4, updates)

def experiment3():  # Non-conflicting experiment
    random.seed(77)
    updates = []
    for i in range(5):
        updates.append((i, {"type": "put", "key": f"k{i}", "value": f"R{i}"}))
    for i in range(5):
        sender = (i + 1) % 5
        updates.append((sender, {"type": "append", "key": f"k{i}", "suffix": f"_R{sender}"}))
    runSimulation("Non-Conflicting Updates", 5, updates)

if __name__ == "__main__":
    experiment1()
    experiment2()
    experiment3()
