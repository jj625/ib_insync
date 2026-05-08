"""
single-session, single-client server
"""
import asyncio
import datetime
import logging, argparse
import struct
import time

"""
Binary log format (simple, append-only)
File layout (little-endian):
u8 direction: 0 = C→S, 1 = S→C
u64 timestamp in microseconds since epoch
u32 length N
N bytes payload
"""

LOG_STRUCT = struct.Struct("<BQI")  # dir, ts_us, length

def now_us() -> int:
    return int(time.time() * 1_000_000)

def write_record(files_tup, direction: int, payload: bytes):
    f_bin, f_txt = files_tup
    if not f_bin:
        return
    
    _ts = now_us()
    header = LOG_STRUCT.pack(direction, _ts, len(payload))
    f_bin.write(header)
    f_bin.write(payload)
    f_bin.flush()
    if f_txt:
        f_txt.write(f"{_ts} {direction} {len(payload)} {payload}\n")
        f_txt.flush()

def read_records(path):
    with open(path, "rb") as f:
        while True:
            header = f.read(LOG_STRUCT.size)
            if not header:
                break
            direction, ts_us, length = LOG_STRUCT.unpack(header)
            payload = f.read(length)
            if len(payload) < length:
                break
            yield direction, ts_us, payload

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
    dir_flag = 0 if direction == "C→S" else 1
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
            write_record(log_files, dir_flag, data)
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
    if args.recording:
        log_binfile = open("mitm_log.bin", "ab")
        log_txtfile = open("mitm_log.txt", "a")
        logger.info(f"Recording enabled. Logging to mitm_log.bin")
    else:
        log_binfile = None
        log_txtfile = None
    tasks = [
        asyncio.create_task(cancel_event.wait(), name='cancel_event'), # awaitable
        asyncio.create_task(pipe(client_reader, server_writer, "C→S", cancel_event, (log_binfile, log_txtfile)), name='C→S'),
        asyncio.create_task(pipe(server_reader, client_writer, "S→C", cancel_event, (log_binfile, log_txtfile)), name='S→C'),
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
    parser.add_argument("-r", "--recording", action="store_true", help="Enable recording of traffic to a binary log file")
    args = parser.parse_args()
    asyncio.run(main(args))
