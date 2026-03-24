import heapq # Importing heapq for priority queueing that is used in discrete event simulation
import random # Importing random to simulate random network delays
from replica import Replica # Importing replica to use as base class for replica logic
from multicast import TOBCAST # Importing TOBCAST for Total Order Broadcast

class SimulateNetwork: # This class will simulates a network with message delays and event scheduling
    def __init__(self, min_delay=1, max_delay=8, seed=42): 
        random.seed(seed) # Ensuring that the simulation is reproducible
        self.min_delay = min_delay # Initializing min_delay as the minimum time it takes for the message to arrive
        self.max_delay = max_delay # Initializing max_delay as the maximum time it takes for the message to arrive
        self.time = 0 # Setting time to zero for global simulation clock
        self._heap = [] # Creating a heap for an event queue which stores time, sequence, and function
        self._seq = 0 # This will be use as a tie-breaker when there two events scheduled at the same time
        self.replicas: dict = {} # Creating a dictionary for mapping ID to Replica objects
        self._channel_ready: dict = {} # Creating a dictionary to track the last delivery time per channel to ensure that it is in First In First Out order

    def _push(self, t, fn): # This is a helper function to push new event to the heap
        heapq.heappush(self._heap, (t, self._seq, fn))
        self._seq += 1 # Incrementing the number of sequence by one to maintain event order stable

    def schedule(self, extra_delay, fn): # This function is used to schedule a function to run after a delay
        self._push(self.time + extra_delay, fn)

    def deliver_to(self, src_id, target_id, msg): # This function will calculate delivery time and schedule a message arrival at the target
        delay = random.randint(self.min_delay, self.max_delay) # This will randomly pick a network latency
        channel = (src_id, target_id) # Identifying the point-to-point link
        ready = self._channel_ready.get(channel, 0)
        deliver_time = max(self.time + delay, ready)
        self._channel_ready[channel] = deliver_time
        target = self.replicas[target_id]

        def _deliver():
            if isinstance(msg, TOBCAST):
                target.receiveTobcast(msg)
            else:
                target.receiveAck(msg)

        self._push(deliver_time, _deliver)

    def run(self):
        while self._heap:
            t, _, fn = heapq.heappop(self._heap)
            self.time = t
            fn()


class SimReplica(Replica):

    def __init__(self, rid, all_replicas, net: SimulateNetwork):
        super().__init__(rid, all_replicas)
        self.net = net

    def sendToReplicas(self, msg):
        for rid in self.allReplicas:
            if rid != self.replicaID:
                self.net.deliver_to(self.replicaID, rid, msg)

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
            self.deliver_log.append(head.updateID)

            print(f"  [t={self.net.time:4d}] R{self.replicaID} DELIVER "
                  f"{head.updateID:12s} ts={head.ts}")


def make_sim(n, min_delay=1, max_delay=8, seed=42):
    net = SimulateNetwork(min_delay=min_delay, max_delay=max_delay, seed=seed)
    ids = list(range(n))
    replicas = {i: None for i in ids}
    for i in ids:
        replicas[i] = SimReplica(i, replicas, net)
    net.replicas = replicas
    return net, replicas


def print_results(replicas):
    print("\n  Final stores:")
    for rid in sorted(replicas):
        print(f"    R{rid}: {replicas[rid].store}")
    print("\n  Delivery order per replica:")
    for rid in sorted(replicas):
        print(f"    R{rid}: {replicas[rid].deliver_log}")


def assert_consistent(replicas, label=""):
    stores = [replicas[r].store for r in sorted(replicas)]
    logs   = [replicas[r].deliver_log for r in sorted(replicas)]
    assert all(s == stores[0] for s in stores), \
        f"[{label}] FAIL stores differ:\n  {stores}"
    assert all(l == logs[0] for l in logs), \
        f"[{label}] FAIL delivery orders differ:\n  {logs}"
    print(f"\n  PASS [{label}]: all {len(replicas)} replicas have identical "
          f"store AND delivery order")


def experiment1():
    print("\n" + "=" * 65)
    print("Experiment 1: Concurrent Conflicting Updates")
    print("  3 replicas; R0, R1, R2 each append to key 'x' concurrently")
    print("=" * 65)

    net, replicas = make_sim(n=3, seed=10)

    replicas[0].broadcastUpdate("init", {"type": "put", "key": "x", "value": ""})
    net.run()
    print(f"  [init done at t={net.time}]")

    net.schedule(0, lambda: replicas[0].broadcastUpdate(
        "u1", {"type": "append", "key": "x", "suffix": "A"}))
    net.schedule(0, lambda: replicas[1].broadcastUpdate(
        "u2", {"type": "append", "key": "x", "suffix": "B"}))
    net.schedule(0, lambda: replicas[2].broadcastUpdate(
        "u3", {"type": "append", "key": "x", "suffix": "C"}))
    net.run()

    print_results(replicas)
    assert_consistent(replicas, "Experiment 1")
    final = replicas[0].store["x"]
    assert set(final) == {"A", "B", "C"} and len(final) == 3, \
        f"Expected all of A, B, C once: got {final!r}"
    print(f"  x = {final!r}  (all 3 appends present, same order everywhere)")


def experiment2():
    print("\n" + "=" * 65)
    print("Experiment 2: High Contention")
    print("  4 replicas; 30 concurrent incr ops on key 'count'")
    print("=" * 65)

    net, replicas = make_sim(n=4, seed=99)

    replicas[0].broadcastUpdate("init", {"type": "put", "key": "count", "value": 0})
    net.run()
    print(f"  [init done at t={net.time}]")

    for i in range(30):
        sender = i % 4
        uid    = f"incr{i:02d}"
        net.schedule(i, lambda s=sender, u=uid: replicas[s].broadcastUpdate(
            u, {"type": "incr", "key": "count"}))

    net.run()

    print_results(replicas)
    assert_consistent(replicas, "Experiment 2")
    got = replicas[0].store["count"]
    assert got == 30, f"Expected count=30, got {got}"
    print(f"  count = {got}  (exactly 30 increments applied everywhere)")


def experiment3():
    print("\n" + "=" * 65)
    print("Experiment 3: Non-Conflicting Updates (different keys)")
    print("  5 replicas; each writes its own key, then cross-replica appends")
    print("=" * 65)

    net, replicas = make_sim(n=5, seed=77)

    keys = ["alpha", "beta", "gamma", "delta", "epsilon"]

    for i, key in enumerate(keys):
        net.schedule(0, lambda s=i, key=key: replicas[s].broadcastUpdate(
            f"put_{key}", {"type": "put", "key": key, "value": key}))
    net.run()
    print(f"  [puts done at t={net.time}]")

    for i, key in enumerate(keys):
        src = (i + 1) % 5
        net.schedule(0, lambda s=src, key=key: replicas[s].broadcastUpdate(
            f"app_{key}", {"type": "append", "key": key, "suffix": "!"}))
    net.run()
    print(f"  [appends done at t={net.time}]")

    print_results(replicas)
    assert_consistent(replicas, "Experiment 3")

    for key in keys:
        expected = key + "!"
        got = replicas[0].store[key]
        assert got == expected, f"Expected {expected!r}, got {got!r}"
    print("  All keys have correct final value (key + '!')")


if __name__ == "__main__":
    experiment1()
    experiment2()
    experiment3()
    print("\n" + "=" * 65)
    print("All experiments passed.")
