from replica import Replica
#optional test file for part A
def makeReplicas(n):
    replicas = {}
    for i in range(n):
        replicas[i] = None
    for i in range(n):
        replicas[i] = Replica(i, replicas)
    return replicas


def printStores(replicas, label="stores"):
    print(f"\n--- {label} ---")
    for rid in sorted(replicas):
        print(f"Replica {rid}: {replicas[rid].store}")


def assertSameStores(replicas):
    stores = [replicas[rid].store for rid in sorted(replicas)]
    first = stores[0]
    for s in stores[1:]:
        assert s == first, f"Stores differ: {stores}"
    print("PASS: all replicas have identical store state")


def assertDeliveredEverywhere(replicas, updateId):
    for rid in replicas:
        assert updateId in replicas[rid].delivered, (
            f"Replica {rid} did not deliver {updateId}"
        )
    print(f"PASS: update {updateId} delivered everywhere")


# -----------------------------
# TEST 1: single put
# -----------------------------
def testSinglePut():
    print("\nTEST 1: single put")
    replicas = makeReplicas(3)

    replicas[0].broadcastUpdate(
        updateID="u1",
        op={"type": "put", "key": "x", "value": "hello"}
    )

    printStores(replicas, "after single put")
    assertDeliveredEverywhere(replicas, "u1")
    assertSameStores(replicas)
    assert replicas[0].store["x"] == "hello"
    print("PASS: testSinglePut")


# -----------------------------
# TEST 2: append after put
# -----------------------------
def testPutThenAppend():
    print("\nTEST 2: put then append")
    replicas = makeReplicas(3)

    replicas[0].broadcastUpdate(
        updateID="u1",
        op={"type": "put", "key": "msg", "value": "hi"}
    )

    replicas[1].broadcastUpdate(
        updateID="u2",
        op={"type": "append", "key": "msg", "suffix": "!"}
    )

    printStores(replicas, "after put then append")
    assertDeliveredEverywhere(replicas, "u1")
    assertDeliveredEverywhere(replicas, "u2")
    assertSameStores(replicas)
    assert replicas[0].store["msg"] == "hi!"
    print("PASS: testPutThenAppend")


# -----------------------------
# TEST 3: multiple increments
# -----------------------------
def testMultipleIncrements():
    print("\nTEST 3: multiple increments")
    replicas = makeReplicas(3)

    replicas[0].broadcastUpdate(
        updateID="u1",
        op={"type": "put", "key": "count", "value": 0}
    )

    replicas[0].broadcastUpdate(
        updateID="u2",
        op={"type": "incr", "key": "count"}
    )

    replicas[1].broadcastUpdate(
        updateID="u3",
        op={"type": "incr", "key": "count"}
    )

    replicas[2].broadcastUpdate(
        updateID="u4",
        op={"type": "incr", "key": "count"}
    )

    printStores(replicas, "after multiple increments")
    assertSameStores(replicas)
    assert replicas[0].store["count"] == 3
    print("PASS: testMultipleIncrements")


# -----------------------------
# TEST 4: concurrent-style updates
# -----------------------------
def testConflictingUpdatesTotalOrder():
    print("\nTEST 4: conflicting updates still converge")
    replicas = makeReplicas(3)

    # initialize
    replicas[0].broadcastUpdate(
        updateID="u0",
        op={"type": "put", "key": "x", "value": ""}
    )

    # different replicas broadcast updates
    replicas[1].broadcastUpdate(
        updateID="u1",
        op={"type": "append", "key": "x", "suffix": "A"}
    )

    replicas[2].broadcastUpdate(
        updateID="u2",
        op={"type": "append", "key": "x", "suffix": "B"}
    )

    printStores(replicas, "after conflicting appends")
    assertDeliveredEverywhere(replicas, "u1")
    assertDeliveredEverywhere(replicas, "u2")
    assertSameStores(replicas)

    finalValue = replicas[0].store["x"]
    assert finalValue in ("AB", "BA"), f"Unexpected final value: {finalValue}"
    print(f"PASS: all replicas agree on x = {finalValue}")


# -----------------------------
# TEST 5: duplicate delivery prevention
# -----------------------------
def testNoDuplicateDelivery():
    print("\nTEST 5: duplicate delivery prevention")
    replicas = makeReplicas(3)

    replicas[0].broadcastUpdate(
        updateID="u1",
        op={"type": "put", "key": "y", "value": "once"}
    )

    # simulate duplicate same update arriving again
    replicas[1].broadcastUpdate(
        updateID="u1",
        op={"type": "put", "key": "y", "value": "twice?"}
    )

    printStores(replicas, "after duplicate updateID attempt")
    assertSameStores(replicas)

    # because delivered set is keyed by updateID,
    # second one should not be applied again
    assert replicas[0].store["y"] == "once"
    print("PASS: duplicate updateID not delivered twice")


# -----------------------------
# TEST 6: all replicas same delivery order
# -----------------------------
def testSameDeliveryOrder():
    print("\nTEST 6: same delivery order")
    replicas = makeReplicas(3)

    updates = [
        ("u1", {"type": "put", "key": "z", "value": ""}, 0),
        ("u2", {"type": "append", "key": "z", "suffix": "1"}, 1),
        ("u3", {"type": "append", "key": "z", "suffix": "2"}, 2),
        ("u4", {"type": "append", "key": "z", "suffix": "3"}, 0),
    ]

    for uid, op, sender in updates:
        replicas[sender].broadcastUpdate(uid, op)

    printStores(replicas, "after same-order test")
    assertSameStores(replicas)

    deliveredSets = [replicas[r].delivered for r in replicas]
    first = deliveredSets[0]
    for ds in deliveredSets[1:]:
        assert ds == first, "Delivered update sets differ across replicas"

    print("PASS: all replicas delivered same set of updates")


if __name__ == "__main__":
    testSinglePut()
    testPutThenAppend()
    testMultipleIncrements()
    testConflictingUpdatesTotalOrder()
    testNoDuplicateDelivery()
    testSameDeliveryOrder()

    print("\nAll tests finished.")