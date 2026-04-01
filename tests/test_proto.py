"""Test protobuf connect/disconnect against a live TWS/gateway on localhost:7296."""

import asyncio
import logging
import sys

import ib_insync as ibi
from ib_insync.client import MIN_SERVER_VER_PROTOBUF

HOST = '127.0.0.1'
PORT = 7496
CLIENT_ID = 99
WAIT_SECONDS = 60


async def main():
    ib = ibi.IB()

    print(f'Connecting to {HOST}:{PORT} clientId={CLIENT_ID} ...')
    _account = 'U2575725'
    await ib.connectAsync(HOST, PORT, CLIENT_ID, readonly=True, account=_account, timeout=10)

    sv = ib.client.serverVersion()
    print(f'Server version: {sv}')
    print(f'Protobuf active: {sv >= MIN_SERVER_VER_PROTOBUF}')
    print(f'Accounts: {ib.managedAccounts()}')

    assert sv >= MIN_SERVER_VER_PROTOBUF, (
        f'Server version {sv} < {MIN_SERVER_VER_PROTOBUF}; '
        f'protobuf not supported by this server')

    assert ib.client._useProtobuf(), 'Client did not enter protobuf mode'

    assert ib.isConnected(), 'IB reports not connected after connectAsync'

    print(f'Current time: {await ib.reqCurrentTimeAsync()}')
    print(f'Current time in millis: {await ib.reqCurrentTimeInMillisAsync()}')

    print(f'Portfolio:\n{ib.portfolio()}')

    print(f'FA groups:\n{await ib.requestFAAsync(1), {await ib.requestFAAsync(2)}}')
    print(await ib.reqUserInfoAsync())
    print(f'Connected OK — waiting {WAIT_SECONDS}s ...')
    await asyncio.sleep(WAIT_SECONDS)

    print('Disconnecting ...')
    ib.disconnect()
    assert not ib.isConnected(), 'IB still reports connected after disconnect'
    print('Done.')


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)-20s %(levelname)-8s %(message)s',
        stream=sys.stdout,
    )
    # bump client/decoder to DEBUG for protocol-level visibility
    logging.getLogger('ib_insync.client').setLevel(logging.DEBUG)
    logging.getLogger('ib_insync.ProtobufDecoder').setLevel(logging.DEBUG)

    # filter out log messages that contain certain keywords
    class KeywordFilter(logging.Filter):
        def __init__(self, keywords):
            super().__init__()
            self.keywords = keywords

        def filter(self, record):
            return not any(keyword in record.getMessage() for keyword in self.keywords)

    keywords_to_filter = ['updateAccountValue', 'accountUpdateMulti',
        'commissionReport', 'COMMISSION_AND_FEES_REPORT',
        'ACCOUNT_UPDATE_MULTI', 'ACCT_UPDATE_TIME', 'updateAccountTime',
        'updatePortfolio', 'PORTFOLIO_VALUE', 'ACCT_VALUE', 
        'REQ_ACCOUNT_UPDATES_MULTI', 'reqAccountUpdatesMultiAsync'
    ]
    logging.getLogger('ib_insync.client').addFilter(KeywordFilter(keywords_to_filter))
    logging.getLogger('ib_insync.wrapper').addFilter(KeywordFilter(keywords_to_filter))

    ibi.IB.run(main())
