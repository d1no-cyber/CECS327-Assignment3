# test_replica.py

from replica import Replica

def make_replicas(n):
    replicas = {}
    for i in range(n):
        replicas[i] = None
    for i in range(n):
        replicas[i] = Replica(i, replicas)
    return replicas


def print_stores(replicas, label="stores"):
    print(f"\n--- {label} ---")
    for rid in sorted(replicas):
        print(f"Replica {rid}: {replicas[rid].store}")


def assert_same_stores(replicas):
    stores = [replicas[rid].store for rid in sorted(replicas)]
    first = stores[0]
    for s in stores[1:]:
        assert s == first, f"Stores differ: {stores}"
    print("PASS: all replicas have identical store state")


def assert_delivered_everywhere(replicas, update_id):
    for rid in replicas:
        assert update_id in replicas[rid].delivered, (
            f"Replica {rid} did not deliver {update_id}"
        )
    print(f"PASS: update {update_id} delivered everywhere")


# -----------------------------
# TEST 1: single put
# -----------------------------
def test_single_put():
    print("\nTEST 1: single put")
    replicas = make_replicas(3)

    replicas[0].broadcastUpdate(
        updateID="u1",
        op={"type": "put", "key": "x", "value": "hello"}
    )

    print_stores(replicas, "after single put")
    assert_delivered_everywhere(replicas, "u1")
    assert_same_stores(replicas)
    assert replicas[0].store["x"] == "hello"
    print("PASS: test_single_put")


# -----------------------------
# TEST 2: append after put
# -----------------------------
def test_put_then_append():
    print("\nTEST 2: put then append")
    replicas = make_replicas(3)

    replicas[0].broadcastUpdate(
        updateID="u1",
        op={"type": "put", "key": "msg", "value": "hi"}
    )

    replicas[1].broadcastUpdate(
        updateID="u2",
        op={"type": "append", "key": "msg", "suffix": "!"}
    )

    print_stores(replicas, "after put then append")
    assert_delivered_everywhere(replicas, "u1")
    assert_delivered_everywhere(replicas, "u2")
    assert_same_stores(replicas)
    assert replicas[0].store["msg"] == "hi!"
    print("PASS: test_put_then_append")


# -----------------------------
# TEST 3: multiple increments
# -----------------------------
def test_multiple_increments():
    print("\nTEST 3: multiple increments")
    replicas = make_replicas(3)

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

    print_stores(replicas, "after multiple increments")
    assert_same_stores(replicas)
    assert replicas[0].store["count"] == 3
    print("PASS: test_multiple_increments")


# -----------------------------
# TEST 4: concurrent-style updates
# -----------------------------
def test_conflicting_updates_total_order():
    print("\nTEST 4: conflicting updates still converge")
    replicas = make_replicas(3)

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

    print_stores(replicas, "after conflicting appends")
    assert_delivered_everywhere(replicas, "u1")
    assert_delivered_everywhere(replicas, "u2")
    assert_same_stores(replicas)

    final_value = replicas[0].store["x"]
    assert final_value in ("AB", "BA"), f"Unexpected final value: {final_value}"
    print(f"PASS: all replicas agree on x = {final_value}")


# -----------------------------
# TEST 5: duplicate delivery prevention
# -----------------------------
def test_no_duplicate_delivery():
    print("\nTEST 5: duplicate delivery prevention")
    replicas = make_replicas(3)

    replicas[0].broadcastUpdate(
        updateID="u1",
        op={"type": "put", "key": "y", "value": "once"}
    )

    # simulate duplicate same update arriving again
    replicas[1].broadcastUpdate(
        updateID="u1",
        op={"type": "put", "key": "y", "value": "twice?"}
    )

    print_stores(replicas, "after duplicate updateID attempt")
    assert_same_stores(replicas)

    # because delivered set is keyed by updateID,
    # second one should not be applied again
    assert replicas[0].store["y"] == "once"
    print("PASS: duplicate updateID not delivered twice")


# -----------------------------
# TEST 6: all replicas same delivery order
# -----------------------------
def test_same_delivery_order():
    print("\nTEST 6: same delivery order")
    replicas = make_replicas(3)

    updates = [
        ("u1", {"type": "put", "key": "z", "value": ""}, 0),
        ("u2", {"type": "append", "key": "z", "suffix": "1"}, 1),
        ("u3", {"type": "append", "key": "z", "suffix": "2"}, 2),
        ("u4", {"type": "append", "key": "z", "suffix": "3"}, 0),
    ]

    for uid, op, sender in updates:
        replicas[sender].broadcastUpdate(uid, op)

    print_stores(replicas, "after same-order test")
    assert_same_stores(replicas)

    delivered_sets = [replicas[r].delivered for r in replicas]
    first = delivered_sets[0]
    for ds in delivered_sets[1:]:
        assert ds == first, "Delivered update sets differ across replicas"

    print("PASS: all replicas delivered same set of updates")


if __name__ == "__main__":
    test_single_put()
    test_put_then_append()
    test_multiple_increments()
    test_conflicting_updates_total_order()
    test_no_duplicate_delivery()
    test_same_delivery_order()

    print("\nAll tests finished.")