import argparse
import ib_insync as ibi
import logging
import asyncio
from random import randint

from ib_insync import loop
from ib_insync.client import MIN_SERVER_VER_PROTOBUF

logger = logging.getLogger(__name__)

class IBConnectionError(Exception):
    """Base class for all IBKR connection-related errors."""
    def __init__(self, message, *, code=None, details=None):
        super().__init__(message)
        self.code = code
        self.details = details

class ClientIdInUseError(IBConnectionError):
    """Raised when the IBKR clientId is already in use."""
    pass


class TWSNotRunningError(IBConnectionError):
    """Raised when TWS/Gateway is not reachable."""
    pass


class AuthenticationError(IBConnectionError):
    """Raised when IBKR rejects the connection due to auth issues."""
    pass


class PeerClosedConnectionError(IBConnectionError):
    """Raised when IBKR closes the socket immediately after connect."""
    pass

class IBApiErrorAwaiter:
    """
    Turn IB.Client.apiError(msg) event into an awaitable future.
    Also wraps the error message into a RuntimeError exception.
    apiError() is not part of ibapi protocol.
    """
    def __init__(self, ib: ibi.IB):
        self.ib = ib
        _loop = asyncio.get_running_loop()
        self.future = _loop.create_future()

        def _handler(msg: str):
            if not self.future.done():
                self.future.set_exception(RuntimeError(msg))

        # apiError is called from two places:
        # 1. during Client.connectAsync()
        # 2. in Client._onSocketDisconnected()
        ib.client.apiError.connect(_handler)

class IBWrapperErrorAwaiter:
    """
    Turns IB.Wrapper.error() into an awaitable future.
    ibapi protocol sends error(reqId, errorCode, errorString, contract).
    ib_insync maps it to IB.errorEvent event.
    TODO: Care must be taken to account for serial error messages.
    """
    def __init__(self, ib: ibi.IB):
        self.ib = ib
        _loop = asyncio.get_running_loop()
        self.future = _loop.create_future()

        def _handler(reqId, errorCode, errorString, contract):
            if not self.future.done():
                self.future.set_exception(RuntimeError(str(errorString)))

        self.ib.errorEvent.connect(_handler)

def classify_connect_error(exc: Exception) -> IBConnectionError:
    """
    Convert raw socket / IBKR errors into typed IBConnectionError subclasses.
    """
    logger.info("Classifying connection error")
    msg = str(exc)

    # OS-level connection refused
    if isinstance(exc, ConnectionRefusedError):
        logger.info("TWS/Gateway not running")
        return TWSNotRunningError("TWS/Gateway not running")

    # IBKR-specific message patterns
    if "clientId 3464 already in use" in msg:
        logger.info("Client ID already in use")
        return ClientIdInUseError("Client ID already in use")

    # Fallback
    return IBConnectionError(f"Connection failed: {msg}")

async def connect_with_errors(ib, host, port, clientId) -> None:
    err = IBApiErrorAwaiter(ib)
    # err = IBWrapperErrorAwaiter(ib)

    connect_task = asyncio.create_task(
        ib.connectAsync(host, port, clientId)
    )

    done, pending = await asyncio.wait(
        {connect_task, err.future},
        return_when=asyncio.FIRST_COMPLETED
    )

    # If connect_task wins → err.future is still pending → you cancel it → no exception inside it → no warning
    # If err.future wins → you use its exception → and connect_task is cancelled → no warning

    for p in pending:
        p.cancel()
        # try:
        #     await p
        # except Exception:
        #     pass
    # logger.debug(f"Waiting for connection or error...\ndone:\n{done}\npending:\n{pending}")

    # Error happened first
    if err.future in done:
        logger.debug("Error happened first")
        connect_task.cancel()
        exc = await err.future
        raise classify_connect_error(exc)

    # Connection finished first
    logger.debug("Connection finished first")
    result = await connect_task

    # But IBKR might still be disconnected
    if not ib.isConnected():
        raise RuntimeError("Connection failed without explicit error")

    return result

class IBConnection:
    def __init__(self, ib: ibi.IB, host, port, clientId=-1):
        self.ib = ib
        self.host = host
        self.port = port
        if clientId < 0:
            self.clientId = randint(99, 999)
        else:
            self.clientId = clientId

    async def __aenter__(self):
        await connect_with_errors(
            self.ib,
            self.host,
            self.port,
            self.clientId
        )

        # after a successful connect, install a monitor
        _loop = asyncio.get_running_loop()
        self._runtime_error_future = _loop.create_future()
        # self._install_runtime_error_hook()

        def on_error(msg):
            if "Peer closed connection" in msg:
                if not self._runtime_error_future.done():
                    self._runtime_error_future.set_exception(
                        PeerClosedConnectionError("IBKR closed the connection")
                    )

        self.ib.client.apiError += on_error
        self._on_error = on_error

        # return self.ib
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # Remove the runtime error hook
        self.ib.client.apiError -= self._on_error

        # If runtime error triggered, propagate it
        if self._runtime_error_future.done():
            logger.debug("Runtime error triggered")
            err = self._runtime_error_future.exception()
            assert isinstance(err, BaseException)
            # await self.ib.disconnectAsync()

            # # Retrieve exception to avoid warnings
            # try:
            #     self._runtime_error_future.exception()
            # except Exception:
            #     pass

            raise err
        # Deterministic, awaitable shutdown
        
        # Normal exit: clean disconnect
        # await self.ib.disconnectAsync()
        self.ib.disconnect()

        # cleanup: avoid "Future exception was never retrieved" warnings
        if not self._runtime_error_future.done():
            self._runtime_error_future.cancel()
        else:
            try:
                self._runtime_error_future.exception()
            except Exception:
                pass

async def main(args):
    ib = ibi.IB()

    PORT = args.port
    CLIENT_ID = args.clientid

    # print(f'Connecting to {HOST}:{PORT} clientId={CLIENT_ID} ...')
    # _account = ''
    # await ib.connectAsync(HOST, PORT, CLIENT_ID, readonly=True, account=_account, timeout=10, 
    #     _MaxClientVer=args.maxclientversion, 
    #     _opts =  {
    #         'sync_multi_accounts': False, 
    #         'reqPositions': False, 
    #         'reqExecutions': False,
    #         'skip_reqOpenOrders': True,
    #         'skip_reqCompletedOrders': True,
    #     },
    # )
    try:
        async with IBConnection(ib, '127.0.0.1', PORT, CLIENT_ID) as ibc:
            sv = ib.client.serverVersion()
            print(f'Server version: {sv}')
            print(f'Protobuf active: {sv >= MIN_SERVER_VER_PROTOBUF}')
            print(f'Accounts: {ib.managedAccounts()}')

        # assert sv >= MIN_SERVER_VER_PROTOBUF, (
        #     f'Server version {sv} < {MIN_SERVER_VER_PROTOBUF}; '
        #     f'protobuf not supported by this server')

        # assert ib.client._useProtobuf(), 'Client did not enter protobuf mode'

            assert ib.isConnected(), 'IB reports not connected after connectAsync'

            # await asyncio.Event().wait()
            await ibc._runtime_error_future

    except Exception as e:
        logger.error(f"An error occurred: {e}")

    print(ib.isConnected())

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7496)
    parser.add_argument("--clientid", type=int, default=-1)
    args = parser.parse_args()


    asyncio.run(main(args))