import asyncio
import sys
import pytest
import inspect

import ib_insync
from ib_insync.util import getLoop
# # --- Your improved getLoop implementation ---
# def getLoop():
#     try:
#         return asyncio.get_running_loop()
#     except RuntimeError:
#         try:
#             loop = asyncio.get_event_loop_policy().get_event_loop()
#         except RuntimeError:
#             # Python ≥3.10: no current loop, must create one
#             loop = asyncio.new_event_loop()
#             asyncio.get_event_loop_policy().set_event_loop(loop)
#         if loop.is_closed():
#             # If the loop exists but is closed, replace it
#             loop = asyncio.new_event_loop()
#             asyncio.get_event_loop_policy().set_event_loop(loop)
#         return loop

print(inspect.getfile(sys.modules['ib_insync.util']))
print(inspect.getfile(ib_insync))

async def hello():
    await asyncio.sleep(0.01)
    return "done"


# --- Tests ---

def test_fresh_thread_creates_loop():
    # Ensure no loop is running
    with pytest.raises(RuntimeError):
        asyncio.get_running_loop()

    loop = getLoop()
    assert isinstance(loop, asyncio.AbstractEventLoop)
    result = loop.run_until_complete(hello())
    assert result == "done"


def test_after_asyncio_run_creates_new_loop():
    # Run and close a loop via asyncio.run()
    result = asyncio.run(hello())
    assert result == "done"

    # Now getLoop should transparently create a new one
    loop = getLoop()
    assert isinstance(loop, asyncio.AbstractEventLoop)
    assert not loop.is_closed()
    result2 = loop.run_until_complete(hello())
    assert result2 == "done"


def test_inside_running_loop_returns_same_loop():
    async def main():
        loop = getLoop()
        assert loop is asyncio.get_running_loop()
        return await hello()

    result = asyncio.run(main())
    assert result == "done"