import datetime
import argparse
import logging
import pandas as pd
import numpy as np
import re
import json
import tqdm

# to import local code
# https://stackoverflow.com/questions/61058798/python-relative-import-in-jupyter-notebook
# https://stackoverflow.com/questions/34478398/import-local-function-from-a-module-housed-in-another-directory-with-relative-im

import os, sys
parent_dir = os.path.abspath('..')
if parent_dir not in sys.path:
    # sys.path.append(parent_dir)
    sys.path.insert(0, parent_dir) # prepend
    # print(f"{parent_dir} added to sys.path")

import ib_insync
from ib_insync import Stock, IB, util

class LoggerFilter(logging.Filter):
    def __init__(self, logger_name, pattern=r'.*'):
        super().__init__()
        self.logger_name = logger_name
        self.pattern = re.compile(pattern)

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not (record.name == self.logger_name and
            self.pattern.search(msg) and 
            record.levelno >= logging.INFO
        )

# Function to flatten the trade structure
def flatten_trade(trade):
    trade_dict = {
        'contract_symbol': trade.contract.symbol,
        'contract_secType': trade.contract.secType,
        'contract_exchange': trade.contract.exchange,
        'contract_currency': trade.contract.currency,
        'order_action': trade.order.action,
        # 'order_totalQuantity': trade.order.totalQuantity,
        'order_orderType': trade.order.orderType,
        'order_lmtPrice': trade.order.lmtPrice,
        # 'order_auxPrice': trade.order.auxPrice,
        # 'order_tif': trade.order.tif,
        'order_status': trade.orderStatus.status,
        'order_filled': trade.orderStatus.filled,
        'order_remaining': trade.orderStatus.remaining,
        # 'order_avgFillPrice': trade.orderStatus.avgFillPrice,
        # 'order_lastFillPrice': trade.orderStatus.lastFillPrice,
        'order_permId': trade.order.permId,
        # 'order_clientId': trade.order.clientId,
        # 'order_orderId': trade.order.orderId,
        # 'order_parentId': trade.order.parentId,
        # 'order_whyHeld': trade.orderStatus.whyHeld,
        # 'order_mktCapPrice': trade.orderStatus.mktCapPrice
    }
    return trade_dict

# Function to flatten the fill structure
def flatten_fill(fill):
    fill_dict = {
        'exec_execId': fill.execution.execId,
        'exec_time': fill.execution.time.astimezone(),
        'exec_acctNumber': fill.execution.acctNumber,
        'exec_exchange': fill.execution.exchange,
        'exec_side': fill.execution.side,
        'exec_shares': fill.execution.shares,
        'exec_price': fill.execution.price,
        'exec_permId': fill.execution.permId,
        # 'exec_clientId': fill.execution.clientId,
        'exec_orderId': fill.execution.orderId,
        'exec_liquidation': fill.execution.liquidation,
        'exec_cumQty': fill.execution.cumQty,
        'exec_avgPrice': fill.execution.avgPrice,
        'exec_orderRef': fill.execution.orderRef,
        # 'exec_evRule': fill.execution.evRule,
        # 'exec_evMultiplier': fill.execution.evMultiplier,
        'commission_report_commission': fill.commissionReport.commission,
        'commission_report_currency': fill.commissionReport.currency,
        'commission_report_realizedPNL': fill.commissionReport.realizedPNL,
        # 'commission_report_yield': fill.commissionReport.yield_,
        # 'commission_report_yieldRedemptionDate': fill.commissionReport.yieldRedemptionDate
    }
    return fill_dict

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('symbols', nargs='*', type=str, help='Just run for this symbol(s)') # nargs='+' means one or more
    # argparser.add_argument('numshares', type=int, nargs='?', help='Number of shares to trade')
    # argparser.add_argument('maxloss', type=float, nargs='?', help='Max loss threshold')
    argparser.add_argument('--clientid', type=int, help='IBKR API Client ID')
    argparser.add_argument('--host', type=str, default='127.0.0.1', help='Host name')
    argparser.add_argument('--port', type=int, default=7497, help='Port number') # IB Gateway 4001, TWS 7496
    argparser.add_argument('--loglevel', type=str, default='INFO', help='Logging level')
    argparser.add_argument('--dryrun', action='store_true', help='Dry run, don\'t actually download data')
    # argparser.add_argument('--live_trading', action='store_true', help='Live trading')
    args = argparser.parse_args()
    print(args)

    # Set up logging
    logging.basicConfig(level=args.loglevel)
    logger = logging.getLogger(__name__)
    
    wlogger = logging.getLogger('ib_insync.wrapper')
    wlogger.addFilter(LoggerFilter('ib_insync.wrapper', 
        r'^(connectAck|nextValidId|accountDownloadEnd|execDetailsEnd|updateAccountTime|accountUpdateMulti|execDetails'
        r'|updateAccountValue|position|updatePortfolio|commissionReport|historicalData|Info 2104|Info 2106|Info 2158)'
    ))

    # Connect to IB Gateway
    ib = IB()
    ib.connect(args.host, args.port, clientId=args.clientid or np.random.randint(1_000, 10_000))

    # download today's trades
    suffix = f"{datetime.datetime.now():%y%m%d_%H%M}"
    trades = ib.trades()
    logger.info(f"Downloaded {len(trades)} trades")

    if len(trades) > 0:
        # Flatten all trades and fills
        flattened_trades = [flatten_trade(trade) for trade in trades]
        flattened_fills = [flatten_fill(fill) for trade in trades for fill in trade.fills]

        # Create hierarchical pandas DataFrames
        df_trades = pd.DataFrame(flattened_trades)
        logger.info(f"df_trades shape: {df_trades.shape}")
        df_fills = pd.DataFrame(flattened_fills)
        logger.info(f"df_fills shape: {df_fills.shape}")

        # Merge trades and fills DataFrames
        df_merged = pd.merge(df_trades, df_fills, left_on='order_permId', right_on='exec_permId', how='outer')
        logger.info(f"df_merged shape: {df_merged.shape}")

        df_merged.to_csv(f'trades_{suffix}.csv', index=False)
        logger.info(f"Saved trades_{suffix}.csv")

        with open(f'trades_{suffix}.json', 'w') as fp:
            json.dump(util.tree(trades), fp, indent=4)
        logger.info(f"Saved trades_{suffix}.json")

    execs = ib.executions()
    logger.info(f"Downloaded {len(execs)} executions")
    if len(execs) > 0:
        execs_df = util.df(execs)
        logger.info(f"execs_df shape: {execs_df.shape}")
        execs_df.to_csv(f'execs_{suffix}.csv', index=False)
        logger.info(f"Saved execs_{suffix}.csv")

        with open(f'execs_{suffix}.json', 'w') as fp:
            json.dump(util.tree(execs), fp, indent=4)
        logger.info(f"Saved execs_{suffix}.json")

    ib.disconnect()

    return # end of main

if __name__ == '__main__':
    main()