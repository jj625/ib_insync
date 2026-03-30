import asyncio
import inspect
import os, sys
for d in ['../', '../../eventkit']:
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), d))
    if parent_dir not in sys.path:
        # sys.path.append(parent_dir)
        sys.path.insert(0, parent_dir)
        print(f"{parent_dir} added to sys.path")
import ib_insync
import eventkit
print(inspect.getfile(ib_insync))
print(inspect.getfile(eventkit))

from ib_insync.util import run

async def hello():
    print("hello")
    await asyncio.sleep(0.1)
    return "done"

# Create coroutine object
coro = hello()
print("iscoroutine=", asyncio.iscoroutine(coro))

async def await_twice():
    await hello()
    print(await hello())
asyncio.run(await_twice())

asyncio.run(asyncio.sleep(3))  # ensure previous prints complete

# Call run() twice with the SAME coroutine object
print(run(coro))   # First run works
print(run(coro))   # Second run fails!
