import logging
import argparse
import numpy as np

# to import local code
# https://stackoverflow.com/questions/61058798/python-relative-import-in-jupyter-notebook
# https://stackoverflow.com/questions/34478398/import-local-function-from-a-module-housed-in-another-directory-with-relative-im

import os, sys
parent_dir = os.path.abspath('..')
if parent_dir not in sys.path:
    # sys.path.append(parent_dir)
    sys.path.insert(0, parent_dir)
    print(parent_dir)

import ib_insync
print(ib_insync.__version_info__)

from ib_insync import IB, util

def main():
    # parse command line arguments
    argparser = argparse.ArgumentParser()
    argparser.add_argument('symbol', type=str, help='Ticker symbol to trade')
    argparser.add_argument('--clientid', type=int, default=np.random.randint(1_000, 10_000), help='IBKR API Client ID')
    argparser.add_argument('--host', type=str, default='127.0.0.1', help='Host name')
    argparser.add_argument('--port', type=int, default=7497, help='Port number') # IB Gateway 4001, TWS 7496
    argparser.add_argument('--loglevel', type=str, default='INFO', help='Logging level')
    argparser.add_argument('--account', type=str, default='paper', help='Account number to use')
    args = argparser.parse_args()
    print(args)

    host_1 = '127.0.0.1'
    host_2 = '192.168.1.90'
    port_1 = 7497
    port_2 = 4002
    port_3 = 7496
    util.logToConsole(logging.DEBUG)
    ib = IB()
    # ib.accountDownloadEndEvent += on_accountDownloadEnd
    # ib.accountUpdateMultiEndEvent += on_accountUpdateMultiEnd
    if args.account == 'paper':
        ib.connect(args.host, args.port, clientId=args.clientid)
    else:
        ib.connect(args.host, args.port, clientId=args.clientid, account=args.account)
    accounts = ib.managedAccounts()
    
    print(ib.portfolio())
    sp_ = [p for p in ib.portfolio() if p.contract.symbol in args.symbol]
    if sp_:
        print(sp_[0].position, sp_[0].marketPrice, sp_[0].marketValue, sp_[0].unrealizedPNL, sp_[0].realizedPNL)
    else:
        print('No positions found')
    print(accounts)

    ib.disconnect() 

if __name__ == '__main__':
    main()
