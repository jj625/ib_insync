"""
single-session, single-client server
"""
import asyncio
import datetime
import logging, argparse

logger = logging.getLogger(__name__)

LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 4002          # your client connects here
TWS_HOST    = "127.0.0.1"
TWS_PORT    = 7497          # real TWS/Gateway port

def ts():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="microseconds")

async def pipe(reader, writer, direction, cancel_event):
    """
    Forward bytes from reader → writer.
    direction: "C→S" or "S→C" for logging.
    """
    try:
        while not cancel_event.is_set():
            data = await reader.read(4096)
            if not data:
                # eof from one side → trigger shutdown
                cancel_event.set()
                break

            # raw logging (binary-safe)
            logger.info(f"{ts()} {direction} {len(data)} bytes")
            # optionally: write to a binary log file

            writer.write(data)
            await writer.drain()
    except asyncio.CancelledError:
        pass
    finally:
        writer.close()
        await writer.wait_closed()

async def handle_client(client_reader, client_writer):
    # Connect to real TWS/Gateway
    server_reader, server_writer = await asyncio.open_connection(TWS_HOST, TWS_PORT)

    # Two pipes: client→server and server→client
    cancel_event = asyncio.Event()
    tasks = [
        asyncio.create_task(cancel_event.wait(), name='cancel_event'), # awaitable
        asyncio.create_task(pipe(client_reader, server_writer, "C→S", cancel_event), name='C→S'),
        asyncio.create_task(pipe(server_reader, client_writer, "S→C", cancel_event), name='S→C'),
    ]

    # Wait until either pipe finishes
    logger.info(f"Connection established. Waiting for return...")
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    logger.info(f"Connection finished. Shutting down...")
    logger.info(f"done: {done}, pending: {pending}")

    # trigger shutdown
    cancel_event.set()

    # 🔥 CRITICAL FIX: close transports so read() wakes up
    client_writer.transport.close()
    server_writer.transport.close()

    # Cancel the other direction
    for task in pending:
        logger.info(f"Cancelling task: {task}")
        task.cancel()

    await asyncio.gather(*pending, return_exceptions=True)

    # server_writer.close()
    # client_writer.close()
    # await server_writer.wait_closed()
    # await client_writer.wait_closed()

    logger.info(f"Connection closed")

async def main(args):
    global TWS_PORT
    TWS_PORT = args.targetport

    # single-session server pattern
    _stop = asyncio.Future()
    async def _one_client_wrapper(reader, writer):
        await handle_client(reader, writer)
        logger.info(f"MITM proxy shutting down after handling one client")
        _stop.set_result(None)
    server = await asyncio.start_server(_one_client_wrapper, LISTEN_HOST, args.sourceport)
    logger.info(f"MITM proxy listening on {LISTEN_HOST}:{args.sourceport}")
    async with server:
        # await server.serve_forever()
        await _stop

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # cli args: -sourceport -targetport
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--sourceport", type=int, default=LISTEN_PORT, help="Port for the MITM proxy to listen on")
    parser.add_argument("-t", "--targetport", type=int, default=TWS_PORT, help="Port of the real TWS/Gateway")
    args = parser.parse_args()
    asyncio.run(main(args))
