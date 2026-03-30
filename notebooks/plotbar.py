import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import asyncio
import time
import datetime

# def _repr_datetime(self):
#     if self.tzinfo is not None and self.tzinfo.utcoffset() is not None:
#         return f'{self.astimezone():%Y-%m-%d %H:%M:%S}'
#     else:
#         return f'{self:%Y-%m-%d %H:%M:%S}'

# datetime.datetime.__repr__ = _repr_datetime

import pandas as pd
import numpy as np
from scipy.ndimage import gaussian_filter1d
import logging
import re
import argparse
import os, sys

# global
logger = None

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

def on_mpl_close(event):
    logger.info(f'Closed Figure! {event}')

def on_mpl_key(event):
    logger.info(f'Key pressed: {event.key}')

def on_mpl_button(event):
    logger.info(f'Button pressed: {event.button}')

# def on_mpl_mouse(event):
#     logger.info(f'Mouse pressed: {event.xdata}, {event.ydata}')

def on_mpl_pick(event):
    logger.info(f'Picked: {event.mouseevent.xdata}, {event.mouseevent.ydata}')

def on_mpl_scroll(event):
    logger.info(f'Scrolled: {event.x}, {event.y}, {event.step}')

def on_mpl_resize(event):
    logger.info(f'Resized: {event.width}, {event.height}')

def on_mpl_draw(event):
    logger.info(f'Drawn: {event}')

def on_mpl_enter(event):
    logger.info(f'Entered: {event}')

def on_mpl_leave(event):
    logger.info(f'Left: {event}')

def on_mpl_focus(event):
    logger.info(f'Focus: {event}')

def on_mpl_blur(event):
    logger.info(f'Blur: {event}')

def on_ib_accountValue(accountValue):
    logger.info(f'Account value: {accountValue}')

def on_ib_accountSummary(accountSummary):
    logger.info(f'Account summary: {accountSummary}')

def on_ib_updatePortfolio(portfolioItem):
    logger.info(f'Portfolio item: {portfolioItem}')

def on_ib_accountDownloadEnd(accountName):
    logger.info(f'Account download end: {accountName}')

def on_ib_accountUpdateMultiEnd(reqId):
    logger.info(f'Account update multi end: {reqId}')

async def go_loop(bars_df, ):
    fig, axs = plt.subplots(2, 1)
    fig.canvas.mpl_connect('close_event', on_mpl_close)
    fig.canvas.mpl_connect('key_press_event', on_mpl_key)
    fig.canvas.mpl_connect('button_press_event', on_mpl_button)
    # fig.canvas.mpl_connect('mouse_press_event', on_mpl_mouse)
    # Filter bars_df for the time range from 9:30am to 4:00pm
    m1 = (bars_df['date'].dt.time >= datetime.time(9, 30)) & (bars_df['date'].dt.time <= datetime.time(16, 0))

    x_axis_values = bars_df[m1]['date']
    vector = np.asarray(bars_df[m1]['average'])

    stop_loop = False
    max_iter = None # 10 # Set to None for infinite loop
    for i in range(1, vector.size + 1):
        if stop_loop or (max_iter and i > max_iter):
            break
        # plot running_vector
        running_vector = vector[:i]
        # plot bar_df ohlc sliding window of size 15 using util.barplot
        # logger.info(bars_df[m1][['open','close','high','low']].iloc[-5:i])
        axs[0].clear()
        axs[1].clear()
        window_size = 15
        if i >= window_size:
            util.barplot_ohlc(bars_df[m1][['open','close','high','low']].iloc[i-window_size:i], 'Bar plots', upColor='green', downColor='red', fig_ax=(fig, axs[0]))
        else:
            util.barplot_ohlc(bars_df[m1][['open','close','high','low']].iloc[:i], 'Bar plots', upColor='green', downColor='red', fig_ax=(fig, axs[0]))
        # ax.plot(x_axis_values[:i], running_vector, label='average')
        axs[1].plot(running_vector, label='average')
        axs[0].xaxis.set_major_locator(ticker.MaxNLocator(10))
        # ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: time.strftime('%H:%M:%S', time.localtime(x))))
        # ax.legend()
        plt.draw()


        
        plt.pause(0.1)
        await asyncio.sleep(0.5)
        # Check if the current figure is closed, if so, break the loop
        if not plt.fignum_exists(fig.number):
            stop_loop = True
            break

        # # Check for mouse click. When the mouse is clicked, the loop will pause until the mouse is clicked again.
        # if plt.waitforbuttonpress(0.1) and plt.fignum_exists(fig.number): # and plt.get_current_fig_manager().canvas.manager.key_press_handler_id == 'q':
        #     while not plt.waitforbuttonpress(0.1) and plt.fignum_exists(fig.number):
        #         plt.pause(0.1)
        #         if not plt.fignum_exists(fig.number):  # Check if the current figure is closed
        #             stop_loop = True
        #             break
        # elif not plt.fignum_exists(fig.number):
        #     stop_loop = True
        #     break
        # else:
        #     plt.pause(0.1)
    
    
        # if plt.fignum_exists(fig.number):
        #     while plt.fignum_exists(fig.number):
        #         if plt.waitforbuttonpress(0.1):
        #             while not plt.waitforbuttonpress(0.1):
        #                 plt.pause(0.1)
        #                 if not plt.fignum_exists(fig.number):  # Check if the current figure is closed
        #                     stop_loop = True
        #                     break
        #         plt.pause(0.1)
        # else:
        #     stop_loop = True
        #     break
    logger.info('Exited for loop')
    await asyncio.sleep(10*60)
    return

def main():
    global logger
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--clientid', type=int, help='IBKR API Client ID')
    argparser.add_argument('--host', type=str, default='127.0.0.1', help='Host name')
    argparser.add_argument('--port', type=int, default=7497, help='Port number') # IB Gateway 4001, TWS 7496
    argparser.add_argument('--loglevel', type=str, default='INFO', help='Logging level')
    args = argparser.parse_args()

    # Set up logging
    logging.basicConfig(level=args.loglevel, format='%(asctime)s:%(levelname)s:%(name)s:%(funcName)s:%(message)s')
    logger = logging.getLogger(__name__)
    
    logger.info(args)

    wlogger = logging.getLogger('ib_insync.wrapper')
    wlogger.addFilter(LoggerFilter('ib_insync.wrapper', 
        r'^(connectAck|nextValidId|accountDownloadEnd|execDetailsEnd|updateAccountTime|accountUpdateMulti|execDetails'
        r'|updateAccountValue|position|updatePortfolio|commissionReport|historicalData|Info 2104|Info 2106|Info 2158)'
    ))

    # Connect to IB Gateway
    ib = IB()
    ib_insync.util.logToConsole(logging.INFO)
    # ib.connect(args.host, args.port, clientId=args.clientid or np.random.randint(1_000, 10_000))
    # # logger.info(ib.portfolio())

    # util.logToConsole(logging.INFO)
    sym = 'SPY'

    date = f'{datetime.datetime.now()+datetime.timedelta(days=-2):%Y%m%d}'
    filename = f'{sym}_1m_{date}.csv'
    load_from_csv = True
    bars = None
    if load_from_csv:
        bars_df = pd.read_csv(rf'.\data\{filename}', parse_dates=['date'])

    # set up handlers before connecting
    ib.accountDownloadEndEvent += on_ib_accountDownloadEnd
    ib.accountUpdateMultiEndEvent += on_ib_accountUpdateMultiEnd
    ib.accountSummaryEvent += on_ib_accountSummary
    ib.accountValueEvent += on_ib_accountValue
    ib.updatePortfolioEvent += on_ib_updatePortfolio

    ib.connect(args.host, args.port, clientId=args.clientid or np.random.randint(1_000, 10_000))
    # logger.info(ib.portfolio())

    # ib.sleep(3.5*60) # sleep for 3.5 minutes
    plt.ion()  # Turn on interactive mode, non-blocking plot
    util.run(go_loop(bars_df))


    # turning off interactive mode will allow the plot to be displayed until the user closes it
    plt.ioff()
    logger.info('Turned off interactive mode')
    plt.show() # ioff -> blocking until user closes the plot
    logger.info('Showed plot')

    plt.close()
    logger.info('Closed plot')
    ib.disconnect()

if __name__ == '__main__':
    main()
