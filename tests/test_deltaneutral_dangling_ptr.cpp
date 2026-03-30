/* Test: dangling pointer in EOrderDecoder::decodeDeltaNeutral
 *
 * decodeDeltaNeutral creates a DeltaNeutralContract on the stack, decodes wire
 * data into it, stores its ADDRESS into m_contract->deltaNeutralContract, then
 * returns -- destroying the stack local.  The pointer is now dangling.
 *
 * This test demonstrates the bug by:
 * 1. Calling decodeDeltaNeutral with a valid wire buffer
 * 2. Clobbering the stack frame where the local lived
 * 3. Reading back through the dangling pointer to show garbage values
 */

#include "EOrderDecoder.h"
#include "Contract.h"
#include "Order.h"
#include "OrderState.h"

#include <cassert>
#include <cstdio>
#include <cstring>
#include <memory>
#include <string>
#include <vector>

// ---- Wire buffer helpers ----

// Append a null-terminated field to the buffer (the TWS legacy wire format).
static void appendField(std::vector<char>& buf, const char* value) {
    size_t len = strlen(value);
    buf.insert(buf.end(), value, value + len);
    buf.push_back('\0');
}

// Build a wire buffer for decodeDeltaNeutral (version >= 20, contract present).
// Fields: "1\0" (present=true), "<conId>\0", "<delta>\0", "<price>\0"
static std::vector<char> buildDeltaNeutralBuffer(long conId, double delta, double price) {
    std::vector<char> buf;
    appendField(buf, "1");                                   // present = true
    appendField(buf, std::to_string(conId).c_str());         // conId
    appendField(buf, std::to_string(delta).c_str());         // delta
    appendField(buf, std::to_string(price).c_str());         // price
    return buf;
}

// ---- Stack clobbering ----

// Write a distinctive pattern over the stack region where the previous
// function's locals lived.  Must be noinline to prevent the compiler from
// folding it into the caller and reusing the same frame.
__attribute__((noinline))
static void clobberStack() {
    volatile char garbage[512];
    memset(const_cast<char*>(garbage), 0xDE, sizeof(garbage));
    // Force the compiler to actually write (volatile prevents elision)
    (void)garbage[0];
}

// ---- Tests ----

// Regression test: decode values must survive after decodeDeltaNeutral returns.
// Before the fix, this was a dangling pointer to a destroyed stack local.
// After the fix, the DeltaNeutralContract is heap-allocated and owned by Contract.
static int testDecodeValues() {
    printf("TEST: decodeDeltaNeutral values survive after return ... ");

    const long   EXPECTED_CONID = 12345;
    const double EXPECTED_DELTA = 0.5;
    const double EXPECTED_PRICE = 100.25;

    Contract   contract;
    Order      order;
    OrderState orderState;

    // version=20 triggers the deltaNeutral path; serverVersion is unused
    EOrderDecoder decoder(&contract, &order, &orderState, /*version=*/20, /*serverVersion=*/145);

    auto buf = buildDeltaNeutralBuffer(EXPECTED_CONID, EXPECTED_DELTA, EXPECTED_PRICE);
    const char* ptr    = buf.data();
    const char* endPtr = buf.data() + buf.size();

    bool ok = decoder.decodeDeltaNeutral(ptr, endPtr);
    assert(ok && "decodeDeltaNeutral should return true");
    assert(contract.deltaNeutralContract != nullptr && "pointer should be set");

    // Clobber the stack to overwrite any lingering stack-local memory.
    // If the pointer is dangling (the bug), the values below will be garbage.
    clobberStack();

    // After the fix, values must be correct (heap-allocated, stable).
    // Before the fix, this would read garbage from the dead stack frame.
    if (contract.deltaNeutralContract->conId != EXPECTED_CONID ||
        contract.deltaNeutralContract->delta != EXPECTED_DELTA ||
        contract.deltaNeutralContract->price != EXPECTED_PRICE) {
        printf("FAIL (dangling pointer — values corrupted after return)\n");
        printf("  Expected: conId=%ld  delta=%.6f  price=%.6f\n",
               EXPECTED_CONID, EXPECTED_DELTA, EXPECTED_PRICE);
        printf("  Got:      conId=%ld  delta=%.6f  price=%.6f\n",
               contract.deltaNeutralContract->conId,
               contract.deltaNeutralContract->delta,
               contract.deltaNeutralContract->price);
        return 1;
    }

    printf("PASS\n");
    return 0;
}

static int testNotPresent() {
    printf("TEST: decodeDeltaNeutral with contract not present ... ");

    Contract   contract;
    Order      order;
    OrderState orderState;
    EOrderDecoder decoder(&contract, &order, &orderState, 20, 145);

    // Wire buffer: "0\0" = not present
    std::vector<char> buf;
    appendField(buf, "0");
    const char* ptr    = buf.data();
    const char* endPtr = buf.data() + buf.size();

    bool ok = decoder.decodeDeltaNeutral(ptr, endPtr);
    assert(ok);
    assert(contract.deltaNeutralContract == nullptr &&
           "pointer should remain NULL when contract not present");

    printf("PASS\n");
    return 0;
}

static int testVersionTooLow() {
    printf("TEST: decodeDeltaNeutral with version < 20 (no-op) ... ");

    Contract   contract;
    Order      order;
    OrderState orderState;
    EOrderDecoder decoder(&contract, &order, &orderState, /*version=*/19, 145);

    // No wire data should be consumed
    const char* ptr    = nullptr;
    const char* endPtr = nullptr;

    bool ok = decoder.decodeDeltaNeutral(ptr, endPtr);
    assert(ok);
    assert(contract.deltaNeutralContract == nullptr);

    printf("PASS\n");
    return 0;
}

static int testContractCopyDeepCopies() {
    printf("TEST: Contract copy constructor deep-copies deltaNeutralContract ... ");

    Contract original;
    original.deltaNeutralContract = std::unique_ptr<DeltaNeutralContract>(new DeltaNeutralContract());
    original.deltaNeutralContract->conId = 999;
    original.deltaNeutralContract->delta = 0.75;
    original.deltaNeutralContract->price = 50.0;

    Contract copy(original);

    // Must be a different pointer (deep copy, not shallow)
    assert(copy.deltaNeutralContract != nullptr);
    assert(copy.deltaNeutralContract != original.deltaNeutralContract);

    // Values must match
    assert(copy.deltaNeutralContract->conId == 999);
    assert(copy.deltaNeutralContract->delta == 0.75);
    assert(copy.deltaNeutralContract->price == 50.0);

    // Mutating the copy must not affect the original
    copy.deltaNeutralContract->conId = 111;
    assert(original.deltaNeutralContract->conId == 999);

    printf("PASS\n");
    return 0;
}

static int testContractCopyAssignment() {
    printf("TEST: Contract copy-assignment deep-copies deltaNeutralContract ... ");

    Contract original;
    original.deltaNeutralContract = std::unique_ptr<DeltaNeutralContract>(new DeltaNeutralContract());
    original.deltaNeutralContract->conId = 42;
    original.deltaNeutralContract->delta = 1.0;
    original.deltaNeutralContract->price = 200.0;

    Contract assigned;
    assigned = original;

    assert(assigned.deltaNeutralContract != nullptr);
    assert(assigned.deltaNeutralContract != original.deltaNeutralContract);
    assert(assigned.deltaNeutralContract->conId == 42);
    assert(assigned.deltaNeutralContract->delta == 1.0);
    assert(assigned.deltaNeutralContract->price == 200.0);

    // Self-assignment must not crash
    assigned = assigned;
    assert(assigned.deltaNeutralContract->conId == 42);

    printf("PASS\n");
    return 0;
}

static int testContractCopyNullPointer() {
    printf("TEST: Contract copy with null deltaNeutralContract ... ");

    Contract original;
    assert(original.deltaNeutralContract == nullptr);

    Contract copy(original);
    assert(copy.deltaNeutralContract == nullptr);

    Contract assigned;
    assigned.deltaNeutralContract = std::unique_ptr<DeltaNeutralContract>(new DeltaNeutralContract());
    assigned = original;  // should delete old and set to null
    assert(assigned.deltaNeutralContract == nullptr);

    printf("PASS\n");
    return 0;
}

static int testContractDestructorFreesMemory() {
    printf("TEST: Contract destructor cleans up deltaNeutralContract ... ");

    // This test verifies no crash on destruction.  Under ASan, a leak
    // or double-free would be caught.
    {
        Contract c;
        c.deltaNeutralContract = std::unique_ptr<DeltaNeutralContract>(new DeltaNeutralContract());
        c.deltaNeutralContract->conId = 1;
    }
    // If we get here without crashing, the destructor worked.

    // Also test destruction of a contract with null pointer (no-op delete)
    {
        Contract c;
    }

    printf("PASS\n");
    return 0;
}

int main() {
    printf("=== DeltaNeutralContract Dangling Pointer Tests ===\n\n");

    int failures = 0;
    failures += testDecodeValues();
    failures += testNotPresent();
    failures += testVersionTooLow();
    failures += testContractCopyDeepCopies();
    failures += testContractCopyAssignment();
    failures += testContractCopyNullPointer();
    failures += testContractDestructorFreesMemory();

    printf("\n");
    if (failures == 0) {
        printf("All tests passed.\n");
    } else {
        printf("%d test(s) FAILED.\n", failures);
    }
    return failures;
}
