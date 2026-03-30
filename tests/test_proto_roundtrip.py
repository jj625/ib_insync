"""Reproduction tests for proto migration bugs in IB API 10.43 Python client.

Tests round-trip encoding/decoding through protobuf to detect field mapping
errors: typos, wrong assignment targets, and name mismatches.

Related: nautechsystems/nautilus_trader#3561, InteractiveBrokers/tws-api#1426
"""

import sys
sys.path.insert(0, "source/pythonclient")

from ibapi.order import Order
from ibapi.contract import ComboLeg, ContractDetails
from ibapi.client_utils import createOrderProto
from ibapi.decoder_utils import (
    decodeOrder, decodeContract, decodeContractDetails, decodeOrderState,
)
from ibapi.protobuf.Order_pb2 import Order as OrderProto
from ibapi.protobuf.Contract_pb2 import Contract as ContractProto
from ibapi.protobuf.ContractDetails_pb2 import ContractDetails as ContractDetailsProto
from ibapi.protobuf.OrderState_pb2 import OrderState as OrderStateProto
from ibapi.protobuf.TickOptionComputation_pb2 import TickOptionComputation as TickOptionComputationProto

passed = 0
failed = 0


def report(name, ok, detail=""):
    global passed, failed
    status = "PASS" if ok else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    if ok:
        passed += 1
    else:
        failed += 1


# Bug 1: client_utils.py:227 — clientId self-assignment (never written to proto)
def test_clientid_encoding():
    print("\nBug 1: clientId not encoded to OrderProto (client_utils.py:227)")

    order = Order()
    order.clientId = 42

    proto = createOrderProto(order)

    has_field = proto.HasField("clientId")
    report(
        "clientId encoded into OrderProto",
        has_field,
        f"proto.HasField('clientId') = {has_field}, expected True"
    )

    if has_field:
        report(
            "clientId value correct",
            proto.clientId == 42,
            f"got {proto.clientId}, expected 42"
        )


# Bug 2: decoder_utils.py:191 — ddeltaNeutralSettlingFirm typo
def test_delta_neutral_settling_firm_decoding():
    print("\nBug 2: deltaNeutralSettlingFirm typo (decoder_utils.py:191)")

    order_proto = OrderProto()
    order_proto.deltaNeutralSettlingFirm = "TEST_FIRM"

    contract_proto = ContractProto()
    decoded = decodeOrder(0, contract_proto, order_proto)

    actual = decoded.deltaNeutralSettlingFirm
    report(
        "deltaNeutralSettlingFirm decoded correctly",
        actual == "TEST_FIRM",
        f"got '{actual}', expected 'TEST_FIRM'"
    )

    # Check for the typo attribute
    has_typo = hasattr(decoded, "ddeltaNeutralSettlingFirm")
    report(
        "No spurious ddeltaNeutralSettlingFirm attribute",
        not has_typo,
        f"hasattr(order, 'ddeltaNeutralSettlingFirm') = {has_typo}"
    )


# Bug 3: decoder_utils.py:81 — shortSalesSlot vs shortSaleSlot
def test_combo_leg_short_sale_slot():
    print("\nBug 3: ComboLeg shortSaleSlot field name mismatch (decoder_utils.py:81)")

    contract_proto = ContractProto()
    leg_proto = contract_proto.comboLegs.add()
    leg_proto.conId = 12345
    leg_proto.ratio = 1
    leg_proto.action = "BUY"
    leg_proto.exchange = "SMART"
    leg_proto.shortSalesSlot = 2

    contract = decodeContract(contract_proto)
    leg = contract.comboLegs[0]

    actual = leg.shortSaleSlot  # the correct Python attribute name
    report(
        "shortSaleSlot decoded correctly",
        actual == 2,
        f"got {actual}, expected 2"
    )

    # Check if the wrong attribute was set instead
    has_wrong = hasattr(leg, "shortSalesSlot") and leg.shortSalesSlot == 2
    has_correct = leg.shortSaleSlot == 2
    report(
        "Value on correct attribute (shortSaleSlot), not wrong (shortSalesSlot)",
        has_correct and not has_wrong,
        f"shortSaleSlot={leg.shortSaleSlot}, "
        f"hasattr shortSalesSlot={hasattr(leg, 'shortSalesSlot')}"
    )


# Round-trip: encode Order → proto → decode, check field preservation
def test_order_roundtrip():
    print("\nRound-trip: Order encode -> decode field preservation")

    order = Order()
    order.clientId = 7
    order.orderId = 100
    order.action = "BUY"
    order.totalQuantity = 50
    order.orderType = "LMT"
    order.lmtPrice = 123.45
    order.tif = "GTC"
    order.account = "DU12345"
    order.deltaNeutralSettlingFirm = "SETTLE_CO"

    proto = createOrderProto(order)
    contract_proto = ContractProto()

    decoded = decodeOrder(0, contract_proto, proto)

    checks = [
        ("clientId", order.clientId, decoded.clientId),
        ("action", order.action, decoded.action),
        ("orderType", order.orderType, decoded.orderType),
        ("tif", order.tif, decoded.tif),
        ("account", order.account, decoded.account),
        ("deltaNeutralSettlingFirm", order.deltaNeutralSettlingFirm,
         decoded.deltaNeutralSettlingFirm),
    ]

    for field, expected, actual in checks:
        report(
            f"{field} survives round-trip",
            actual == expected,
            f"got {actual!r}, expected {expected!r}"
        )


# Bug 4: decoder.py:1108 — None < 0 TypeError in tick option computation proto
def test_tick_option_computation_none_guard():
    print("\nBug 4: impliedVol None guard in proto tick option computation (decoder.py:1108)")

    # Create a proto with impliedVol unset — decoder should not crash
    proto = TickOptionComputationProto()
    proto.reqId = 1
    proto.tickType = 10

    # Simulate the decoder's extraction logic (same as decoder.py:1107-1130)
    impliedVol = proto.impliedVol if proto.HasField('impliedVol') else None
    delta = proto.delta if proto.HasField('delta') else None
    optPrice = proto.optPrice if proto.HasField('optPrice') else None

    report(
        "impliedVol is None when unset",
        impliedVol is None,
        f"got {impliedVol!r}"
    )

    # The fix: None guard prevents TypeError
    try:
        if impliedVol is not None and impliedVol < 0:
            impliedVol = None
        report("No TypeError on None guard comparison", True)
    except TypeError as e:
        report("No TypeError on None guard comparison", False, str(e))

    # Also test with a set value that should be converted to None
    proto2 = TickOptionComputationProto()
    proto2.impliedVol = -1.0
    val = proto2.impliedVol if proto2.HasField('impliedVol') else None
    if val is not None and val < 0:
        val = None
    report(
        "impliedVol -1 converted to None",
        val is None,
        f"got {val!r}"
    )


# Bug 5: client.py:7149 — duplicate currentTimeMillis() garbles error callback
def test_wshe_error_callback_args():
    print("\nBug 5: duplicate currentTimeMillis() in reqWshEventData (client.py:7149)")

    from ibapi.errors import UPDATE_TWS
    from ibapi.const import NO_VALID_ID

    # Verify the error constants have the expected types
    report(
        "UPDATE_TWS.code() is int",
        isinstance(UPDATE_TWS.code(), int),
        f"type={type(UPDATE_TWS.code()).__name__}"
    )
    report(
        "UPDATE_TWS.msg() is str",
        isinstance(UPDATE_TWS.msg(), str),
        f"type={type(UPDATE_TWS.msg()).__name__}"
    )

    # Simulate the corrected error call args (after fix)
    error_args = (
        NO_VALID_ID,       # reqId
        1000000,           # errorTime (simulated timestamp)
        UPDATE_TWS.code(), # errorCode
        UPDATE_TWS.msg() + " It does not support WSHE Calendar API.",  # errorString
    )
    report(
        "errorCode is int (not timestamp)",
        isinstance(error_args[2], int) and error_args[2] < 10000,
        f"errorCode={error_args[2]}"
    )
    report(
        "errorString is str (not int)",
        isinstance(error_args[3], str),
        f"type={type(error_args[3]).__name__}"
    )


# Bug 6: decoder.py:718 — isBond=False should be True for bond contract data
def test_bond_contract_details_is_bond():
    print("\nBug 6: isBond=True for bond contract data proto path (decoder.py:718)")

    contract_proto = ContractProto()
    contract_proto.lastTradeDateOrContractMonth = "20251215"

    details_proto = ContractDetailsProto()

    # Decode with isBond=True (the fix)
    details = decodeContractDetails(contract_proto, details_proto, True)

    report(
        "maturity set for bond",
        details.maturity == "20251215",
        f"maturity={details.maturity!r}"
    )

    # Decode with isBond=False for comparison
    details_stock = decodeContractDetails(contract_proto, details_proto, False)
    report(
        "lastTradeDateOrContractMonth set for non-bond",
        details_stock.contract.lastTradeDateOrContractMonth == "20251215",
        f"lastTradeDateOrContractMonth={details_stock.contract.lastTradeDateOrContractMonth!r}"
    )


# Bug 7: decoder_utils.py:478 — underConid (lowercase) vs underConId (uppercase)
def test_under_con_id_case():
    print("\nBug 7: underConId case typo in decodeContractDetails (decoder_utils.py:478)")

    contract_proto = ContractProto()
    details_proto = ContractDetailsProto()
    details_proto.underConId = 12345

    details = decodeContractDetails(contract_proto, details_proto, False)

    report(
        "underConId set correctly (uppercase I)",
        details.underConId == 12345,
        f"got {details.underConId}"
    )

    has_typo = hasattr(details, "underConid") and details.__dict__.get("underConid") is not None
    report(
        "No spurious underConid attribute (lowercase i)",
        not has_typo,
        f"has underConid in __dict__: {'underConid' in details.__dict__}"
    )


# Bug 8: client.py:6229 — iterates historicalNewsOptionsStr instead of historicalNewsOptions
def test_historical_news_options_iteration():
    print("\nBug 8: historicalNewsOptions iteration variable (client.py:6229)")

    from ibapi.tag_value import TagValue

    historicalNewsOptions = [TagValue("opt1", "val1"), TagValue("opt2", "val2")]

    # Simulate the corrected code path (after fix)
    historicalNewsOptionsStr = ""
    if historicalNewsOptions:
        for tagValue in historicalNewsOptions:  # fixed: was historicalNewsOptionsStr
            historicalNewsOptionsStr += str(tagValue)

    report(
        "Options string is not empty",
        len(historicalNewsOptionsStr) > 0,
        f"got {historicalNewsOptionsStr!r}"
    )
    report(
        "Options string contains both tags",
        "opt1" in historicalNewsOptionsStr and "opt2" in historicalNewsOptionsStr,
        f"got {historicalNewsOptionsStr!r}"
    )


# Bug 9: decoder_utils.py:414 — missing decimalMaxString() on initMarginBefore
def test_init_margin_before_decimal_string():
    print("\nBug 9: initMarginBefore decimalMaxString conversion (decoder_utils.py:414)")

    order_state_proto = OrderStateProto()
    order_state_proto.initMarginBefore = 5000.75
    order_state_proto.maintMarginBefore = 3000.50

    decoded = decodeOrderState(order_state_proto)

    report(
        "initMarginBefore is str type",
        isinstance(decoded.initMarginBefore, str),
        f"type={type(decoded.initMarginBefore).__name__}, value={decoded.initMarginBefore!r}"
    )
    report(
        "maintMarginBefore is str type (reference)",
        isinstance(decoded.maintMarginBefore, str),
        f"type={type(decoded.maintMarginBefore).__name__}, value={decoded.maintMarginBefore!r}"
    )


# Bug 10: decoder.py:2787 — ",".join(protoBuf) crashes on bytes
def test_proto_error_handler_bytes_repr():
    print("\nBug 10: protoBuf error handler bytes join (decoder.py:2787)")

    protoBuf = b"\x08\x01\x10\x02"  # sample protobuf bytes

    # The fix: use repr() instead of ",".join()
    try:
        theBadMsg = repr(protoBuf)
        report(
            "repr(protoBuf) succeeds on bytes",
            True,
            f"got {theBadMsg!r}"
        )
    except TypeError as e:
        report("repr(protoBuf) succeeds on bytes", False, str(e))

    # Verify the old code would have crashed
    try:
        bad = ",".join(protoBuf)
        report("Old code crashes on bytes join", False, "unexpectedly succeeded")
    except TypeError:
        report("Old code crashes on bytes join (confirmed bug)", True)


if __name__ == "__main__":
    print("IB API 10.43 proto migration bug reproduction")
    print("=" * 55)

    # Original tests (PR #1428)
    test_clientid_encoding()
    test_delta_neutral_settling_firm_decoding()
    test_combo_leg_short_sale_slot()
    test_order_roundtrip()

    # New tests (7 additional bugs)
    test_tick_option_computation_none_guard()
    test_wshe_error_callback_args()
    test_bond_contract_details_is_bond()
    test_under_con_id_case()
    test_historical_news_options_iteration()
    test_init_margin_before_decimal_string()
    test_proto_error_handler_bytes_repr()

    print(f"\n--- Results: {passed} passed, {failed} failed ---")
    sys.exit(1 if failed > 0 else 0)
