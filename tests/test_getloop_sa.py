import asyncio
import sys
import inspect
import ib_insync
from ib_insync.util import getLoop

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
    print("hello")
    await asyncio.sleep(0.1)
    return "done"


# --- Scenario 1: Fresh thread, no loop yet ---
print("Scenario 1: fresh thread")
loop1 = getLoop()
print("Loop created:", loop1)
print("Result:", loop1.run_until_complete(hello()))

# --- Scenario 2: After asyncio.run() closes the loop ---
print("\nScenario 2: after asyncio.run() closes loop")
asyncio.run(hello())  # creates + closes loop
loop2 = getLoop()     # should transparently create a new one
print("Loop recreated:", loop2)
print("Result:", loop2.run_until_complete(hello()))

# --- Scenario 3: Already running loop ---
print("\nScenario 3: inside running loop")
async def main():
    loop3 = getLoop()
    print("Loop running:", loop3)
    print("Result:", await hello())

asyncio.run(main())