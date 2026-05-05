import asyncio
import logging
import ib_insync as ibi 

async def main():
    ib = ibi.IB()
    await ib.connectAsync("127.0.0.1", 7496, clientId=1234,
        # _MaxClientVer = 223,
        _opts =  {
            'sync_multi_accounts': False, 
            'reqPositions': False, 
            'reqExecutions': False,
            'skip_reqOpenOrders': True,
            'skip_reqCompletedOrders': True,
        }
    )
    accounts = ib.managedAccounts()
    print(accounts)

    # Future('CL', '202606', 'NYMEX')
    # Future('ES', '202606', 'CME')
    print(await ib.qualifyContractsAsync(
        ibi.Future('CL', '202605', 'NYMEX'),
        ibi.Future('CL', '202606', 'NYMEX'),
        ibi.Future('CL', '202607', 'NYMEX'),
        ibi.Future('CL', '202608', 'NYMEX'),
    ))
    await asyncio.sleep(10)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # bump client/decoder to DEBUG for protocol-level visibility
    # logging.getLogger('ib_insync.client').setLevel(logging.DEBUG)
    # logging.getLogger('ib_insync.wrapper').setLevel(logging.DEBUG)
    # logging.getLogger('ib_insync.ProtobufDecoder').setLevel(logging.DEBUG)
    asyncio.run(main())