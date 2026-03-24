# CECS 327 — Assignment 3: Total-Order Multicast

Replicated key–value store with Lamport-clock-based totally ordered multicast
(atomic broadcast). Every replica delivers all updates in the same global order.

---

## System model

| Assumption | Detail |
|---|---|
| Replicas | N peers, each with its own Lamport clock |
| Channels | Reliable, FIFO-ordered per sender→receiver pair |
| Clients | May send `UPDATE` to any replica |
| Ordering | Holdback queue + `maxSeen` table enforce total order before delivery |

```
Clients
  |       \        (clients may send to any replica)
  v        v
+----+  +----+  +----+  +----+
| R0 |  | R1 |  | R2 |  | R3 |
+----+  +----+  +----+  +----+
   \       |       /       |
    \------|------/--------|
     total-order multicast
 (TOBCAST + ACK, holdback queues,
  deliver only when safe)
```

---

## Files

| File | Purpose |
|---|---|
| `multicast.py` | `TOBCAST` and `ACK` dataclass definitions |
| `replica.py` | `Replica` — Lamport clock, holdback queue, delivery logic |
| `test.py` | Part A unit tests (6 scenarios, synchronous simulation) |
| `simulator.py` | Part B async simulator with per-channel FIFO delays |
| `answers.md` | Part C written answers |

---

## How to run

Requires Python 3.10+. No external dependencies.

### Part A — unit tests

```bash
python3 test.py
```

Six tests covering: single put, put-then-append, multiple increments,
concurrent conflicting updates, duplicate-ID prevention, and delivery-order
consistency. All should print `PASS`.

### Part B — async simulator experiments

```bash
python3 simulator.py
```

Runs three experiments with random network delays and per-channel FIFO
ordering. Each experiment prints a per-replica delivery log and verifies that
all replicas have identical final state and identical delivery sequence.

---

## Algorithm summary

### Timestamp rule
When replica *Ri* broadcasts an update it increments its Lamport clock and
stamps the message `ts = (clock, replicaID)`. Ties in clock value are broken
by replica ID, giving a deterministic total order.

### Message flow

```
broadcastUpdate(op):
  clock += 1
  ts = (clock, self.id)
  TOBCAST msg = (updateID, op, ts, sender)
  insert msg into local holdback queue
  send TOBCAST to all other replicas

  # self-ACK: bump clock so maxSeen[self] > msg.ts
  clock += 1
  ackTs = (clock, self.id)
  maxSeen[self] = ackTs
  send ACK(ackTs) to all other replicas
  attempt_deliver()

receiveTobcast(msg):
  clock = max(clock, msg.ts[0]) + 1
  insert msg into holdback queue
  maxSeen[msg.sender] = max(maxSeen[msg.sender], msg.ts)
  clock += 1
  ackTs = (clock, self.id)
  maxSeen[self] = ackTs
  send ACK(ackTs) to all other replicas
  attempt_deliver()

receiveAck(ack):
  clock = max(clock, ack.ts[0]) + 1
  maxSeen[ack.sender] = max(maxSeen[ack.sender], ack.ts)
  attempt_deliver()
```

### Delivery condition (the key correctness invariant)

A message `m` at the **head** of the holdback queue is safe to deliver when:

```
for every replica k:  maxSeen[k] > m.ts
```

This guarantees replica *k* will never produce a future message with timestamp
≤ `m.ts`.  Under FIFO channels, it also guarantees that every message from *k*
with timestamp ≤ `m.ts` has already been received and sits ahead of `m` in the
holdback queue.  Therefore the head `m` truly is globally earliest and delivery
order is identical at all replicas.

### Why the self-ACK is necessary

Without the self-ACK, the sender sets `maxSeen[self] = msg.ts`. The delivery
condition requires `maxSeen[self] > msg.ts` (strictly greater), so the
condition can never be satisfied for the sender's own message and no message is
ever delivered.  The self-ACK bumps the sender's clock one more step, producing
`ackTs > msg.ts` and resolving this.

---

## Supported operations

| Type | Parameters | Effect |
|---|---|---|
| `put` | `key`, `value` | `store[key] = value` |
| `append` | `key`, `suffix` | `store[key] += suffix` |
| `incr` | `key` | `store[key] += 1` |

---

## Part B experiments

| Experiment | Replicas | Updates | Seed |
|---|---|---|---|
| 1 — Concurrent conflicting | 3 | 3 concurrent appends on key `x` | 10 |
| 2 — High contention | 4 | 30 increments on key `count` | 99 |
| 3 — Non-conflicting | 5 | 5 puts + 5 cross-replica appends on distinct keys | 77 |

All three print `PASS` confirming identical store state and delivery order
across every replica.
