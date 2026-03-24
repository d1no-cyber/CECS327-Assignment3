# Part C — Written Questions

## Q1: Why does replication need total ordering for conflicting operations?

Without a global delivery order, two replicas can apply the same conflicting
writes in opposite orders and diverge permanently.

**Concrete example.** Two clients concurrently send to a replicated bank account:

- Client 1 → R0: `put(balance, 100)`
- Client 2 → R1: `put(balance, 200)`

Without total order, R0 may deliver 100 then 200 (final: **200**) while R1
delivers 200 then 100 (final: **100**). Now the replicas are inconsistent and
no future operation can reconcile them without external intervention.

Total-order multicast forces every replica to deliver both writes in the same
sequence, so all converge to the same final value regardless of which order is
chosen.

---

## Q2: What do Lamport clocks guarantee and what do they not guarantee?

**They guarantee (causal consistency):**
If event A causally precedes event B (A → B), then `ts(A) < ts(B)`. This is
the *clock condition*: any happened-before relationship is reflected in the
timestamps.

**They do NOT guarantee:**
- **Real-time ordering.** A higher Lamport timestamp does not mean a later
  wall-clock time. Clocks are logical, not physical.
- **A unique total order on their own.** Two concurrent events (neither
  causally precedes the other) can receive any relative timestamps; multiple
  events can even share the same timestamp.
- **The converse of the clock condition.** `ts(A) < ts(B)` does *not* imply
  A → B; concurrent events can be assigned any order by the algorithm.

**With tie-breaking** (e.g., break ties by replica ID), Lamport timestamps
yield a *total order* consistent with causality. This total order is
deterministic and agreed upon by all replicas, but it is arbitrary for truly
concurrent events — all we can guarantee is that it is the *same* arbitrary
order everywhere.

---

## Q3: What breaks if messages can be lost or delivered out of FIFO order?

**If messages are lost:**
A TOBCAST or ACK from replica *k* never arrives. The receiving replicas'
`maxSeen[k]` is never updated past the missing message's timestamp. The
holdback queue head can never satisfy `maxSeen[k] > msg.ts for all k`, so the
system stalls indefinitely — no message is ever delivered.

**If FIFO order is violated (messages from the same sender arrive
out-of-order):**
`maxSeen[k]` can advance past a message timestamp *before that message has
been received*. For example, a later TOBCAST from *k* (with a higher
timestamp) arrives first, updating `maxSeen[k]` past an earlier message's
timestamp. The delivery condition for some other head message `m` may now be
satisfied even though the earlier TOBCAST from *k* (with `ts < m.ts`) has not
yet arrived and is not in the holdback queue. The replica delivers `m` and
applies it without having the earlier message — the total order is broken and
replicas diverge.

This is why the algorithm **requires** reliable FIFO channels: FIFO ensures
that once `maxSeen[k]` exceeds `msg.ts`, all messages from *k* with timestamp
≤ `msg.ts` have already been received and are in the holdback queue.

---

## Q4: Where is the "coordination" happening?

All coordination is in the **middleware layer** — the `Replica` class methods:

- `broadcastUpdate`: increments the Lamport clock and multicasts both the
  TOBCAST and a self-ACK to signal the sender's progress.
- `receiveTobcast` / `receiveAck`: update `maxSeen` and the Lamport clock,
  then trigger delivery attempts.
- `deliverCheck` + `deliver`: the core of the protocol — the holdback queue
  and `maxSeen` table enforce the global total order before any update reaches
  the application.

The **application layer** (`apply` and `store`) is completely passive. It
executes operations in exactly the order the middleware presents them and has
no awareness of Lamport timestamps, acknowledgements, or other replicas. The
`deliver` method acts as the clean boundary: only operations that the
middleware has already determined are globally safe to deliver in the correct
order ever reach application state.
