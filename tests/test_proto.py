"""Test protobuf connect/disconnect against a live TWS/gateway on localhost:7296."""

import asyncio
import logging
import sys

import ib_insync as ibi
from ib_insync.client import MIN_SERVER_VER_PROTOBUF

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)-28s %(levelname)-8s %(message)s',
    stream=sys.stdout,
)
# bump client/decoder to DEBUG for protocol-level visibility
logging.getLogger('ib_insync.client').setLevel(logging.DEBUG)
logging.getLogger('ib_insync.ProtobufDecoder').setLevel(logging.DEBUG)

HOST = '127.0.0.1'
PORT = 7496
CLIENT_ID = 99
WAIT_SECONDS = 60


async def main():
    ib = ibi.IB()

    print(f'Connecting to {HOST}:{PORT} clientId={CLIENT_ID} ...')
    await ib.connectAsync(HOST, PORT, CLIENT_ID, timeout=10)

    sv = ib.client.serverVersion()
    print(f'Server version: {sv}')
    print(f'Protobuf active: {sv >= MIN_SERVER_VER_PROTOBUF}')
    print(f'Accounts: {ib.managedAccounts()}')

    assert sv >= MIN_SERVER_VER_PROTOBUF, (
        f'Server version {sv} < {MIN_SERVER_VER_PROTOBUF}; '
        f'protobuf not supported by this server')

    assert ib.client._useProtobuf(), 'Client did not enter protobuf mode'

    assert ib.isConnected(), 'IB reports not connected after connectAsync'

    print(f'Connected OK — waiting {WAIT_SECONDS}s ...')
    await asyncio.sleep(WAIT_SECONDS)

    print('Disconnecting ...')
    ib.disconnect()
    assert not ib.isConnected(), 'IB still reports connected after disconnect'
    print('Done.')


if __name__ == '__main__':
    ibi.IB.run(main())
