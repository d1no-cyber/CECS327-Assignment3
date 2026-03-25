# CECS 327 Assignment 3: Total-Order Multicast for Replication

For this assignment, we are implementing a key-value store with N replicas. Clients may send UPDATE operations to any replica. Replicas must ensure they deliver updates in the same total order at every node before applying them.

## System model and assumptions
- Replicas communicate by message passing over a network.
- Messages are reliably delivered and FIFO-ordered per sender→receiver
- Each replica maintains a Lamport clock; ties are broken deterministically

## Requirements
- Python 3

## Files
- multicast.py
- replica.py
- simulator.py
- test.py

## Diagram
```bash
Clients
|      \       (clients can send to any replica)
v       v
+----+ +----+ +----+ +----+
| R1 || R2  | | R3 | | R4 |
+----+ +----+ +----+ +----+
   \      |      |     /
     \----|------|----/
      total-order multicast
(TOBCAST + ACK, holdback queues, deliver only when safe)
```

## How to Run

Run required experiments:
```bash
python simulator.py
```
Create output logs:
```bash
python simulator.py > output.txt
```
Unit Tests (Optional)
```bash
python test.py
```

## Authors:

**Sovannmonyrotn Kun:** handled the coding and testing

**Oanh Tran:** handled the coding and testing

**David Tran:** handled the written report, README and testing.
