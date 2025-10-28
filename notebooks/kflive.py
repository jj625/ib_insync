# This project uses Kalman Filter (UKF) created by Roger Labbe and available
# at https://github.com/rlabbe/filterpy, which is distributed under the MIT License.
# See the LICENSE file for more details at https://github.com/rlabbe/filterpy/blob/master/LICENSE
import sys
import io
import datetime
import zoneinfo
tz_NY = zoneinfo.ZoneInfo('America/New_York')
import logging
import re
import argparse
import pathlib
import inspect

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

# import yfinance as yf
import numpy as np
np.set_printoptions(precision=6, suppress=True)

# to import local code
# https://stackoverflow.com/questions/61058798/python-relative-import-in-jupyter-notebook
# https://stackoverflow.com/questions/34478398/import-local-function-from-a-module-housed-in-another-directory-with-relative-im

import os, sys
parent_dir = os.path.abspath('..')
if parent_dir not in sys.path:
    # sys.path.append(parent_dir)
    sys.path.insert(0, parent_dir) # prepend
    # print(f"{parent_dir} added to sys.path")

from filterpy.kalman import UnscentedKalmanFilter as UKF, KalmanFilter
from filterpy.kalman import MerweScaledSigmaPoints
from filterpy.common import Q_discrete_white_noise, Saver

import matplotlib.pyplot as plt
backend_ = plt.get_backend()
if backend_.lower() != 'qtagg':
    print(backend_)

import matplotlib.dates as mdates

import pandas as pd
import matplotlib.animation as animation
# from scipy.signal import find_peaks
# from sklearn.linear_model import LinearRegression
# from PIL import Image  # Import Pillow library
from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.qt_compat import QtWidgets

import eventkit
print(inspect.getfile(eventkit))
import ib_insync
print(inspect.getfile(ib_insync))
from ib_insync import Stock, Future, IB, util, ContractDetails, Contract, BarDataList, BarData

# ib, bars will be set in live mode
ib: IB = None
bars: BarDataList = None

fig: plt.Figure = None

def on_close(event):
    logger.info(f'event={event}')
    plt.close('all')
    if ib and ib.isConnected():
        ib.disconnect()
        loop = util.getLoop()
        loop.stop()

def onInitialBars(bars: BarDataList):
    global high_minus_low
    high_minus_low[:bars._npidx] = bars.high_prices[:bars._npidx] - bars.low_prices[:bars._npidx]
    for frame in range(len(bars)):
        logger.info(f'frame={frame}')
        update(frame)
    fig.canvas.draw()
    fig.canvas.flush_events()

def onBarUpdate(bars: BarDataList, hasNewBar: bool):
    # global dates, prices, log_prices # these arrays are automatically updated
    global high_minus_low
    # dates = bars.npdate_[:bars._npidx]
    # prices = bars._average[:bars._npidx] # already pointing to the numpy array
    # logger.info(f"bar[-1] {bars[-1]}, hasNewBar={hasNewBar}")
    if hasNewBar:
        frame = bars._npidx - 1
        high_minus_low = bars.high_prices[frame] - bars.low_prices[frame]
        logger.info(f'frame={frame}')
        update(frame)
        fig.canvas.draw()
        fig.canvas.flush_events()


# Initialize the plot limits and lines
def init_animation():
    ax1.set_xlim(dates[0], dates[0] + np.timedelta64(60*23, 'm'))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M')) # %Y-%m-%d %H:%M:%S
    # ax1.set_ylim(min(log_prices - log_base_price) * 0.9, max(log_prices - log_base_price) * 1.1)
    ax1.set_ylim(-.01, .01)

    # Make ax1, ax2, ax3 share the same x-axis
    ax2.sharex(ax1)
    ax3.sharex(ax1)

    ax2.set_ylim(-.01, .01)
    ax3.set_ylim(-.001, .001)
    line1.set_data([], [])
    line2.set_data([], [])
    line3.set_data([], [])
    line4.set_data([], [])
    line5.set_data([], [])
    return line1, line2, line3, line4

# Update function for animation
def update(frame: int, *fargs):
    global filtered_prices_np, predicted_prices, uncertainty_patch
    global dates, prices

    logger.info(f'frame={frame}, dates[frame]={dates[frame]}, prices[frame]={prices[frame]}')

    # # Clear previous uncertainty patch
    # if uncertainty_patch is not None:
    #     uncertainty_patch.remove()
    #     uncertainty_patch = None

    if frame < len(prices):
        # kf.R = high_minus_low[frame] / 4.0
        kf.predict()
        measurement = log_prices[frame] - log_base_price
        kf.update(np.array([measurement])) # (price - log_base_price) is in log space
        filtered_prices_np[frame] = kf.x[0]
        hidden_var1[frame] = kf.x[1]
        y_np[frame] = kf.y[0]
        logger.info(f'frame={frame}, '  f'date={pd.to_datetime(dates[frame]):%H:%M}, ' # %Y%m%d 
            f'measurement={measurement:.2%} {np.exp(measurement + log_base_price):.2f}, x0={kf.x[0]:.2%} {np.exp(kf.x[0] + log_base_price):.2f}, y={kf.y[0]:.2%}, K0={kf.K[0][0]:.0%}, √P0={np.sqrt(kf.P[0, 0]):.2%}, '
            f'x1={kf.x[1]:.2%}, K1={kf.K[1][0]:.0%}, '
            f'√P1={np.sqrt(kf.P[1, 1]):.2%}, P[0,1]={kf.P[0, 1]:.6f}'
        )        
        line1.set_data(dates[:frame+1], log_prices[:frame+1] - log_base_price)
        line5.set_data(dates[:frame+1], hidden_var1[:frame+1])
        line2.set_data(dates[:frame+1], filtered_prices_np[:frame+1])
        
        # # Predict future prices for the next 10 steps
        # temp_state = kf.x.copy()
        # temp_P = kf.P.copy()
        # temp_predicted_prices = []
        # for _ in range(future_days):
        #     kf.predict()
        #     temp_predicted_prices.append(kf.x[0])
        
        # future_dates = pd.date_range(start=dates[frame], periods=future_days + 1, freq='B')[1:]
        # line3.set_data(future_dates, temp_predicted_prices)

        # # Convert to pandas Series
        # if display_uncertainty:
        #     temp_prices_series = pd.Series(prices)

        #     # Calculate rolling 20-period standard deviation
        #     rolling_std = temp_prices_series.rolling(window=20).std()
        #     rolling_std = rolling_std[-len(temp_predicted_prices):].reset_index(drop=True)

        #     # Calculate lower and upper bounds using the rolling standard deviation
        #     lower_bound = temp_predicted_prices - 1 * rolling_std
        #     upper_bound = temp_predicted_prices + 1 * rolling_std

        #     # Make sure lower_bound and upper_bound are numpy arrays
        #     lower_bound = np.array(lower_bound)
        #     upper_bound = np.array(upper_bound)
        
        #     uncertainty_patch = ax1.fill_between(future_dates, lower_bound, upper_bound, color='blue', alpha=0.05)

        # # Calculate the uncertainty (2 sigma) for the predicted prices  
        # lower_bound2 = np.array(temp_predicted_prices) - 2 * np.sqrt(kf.P[0, 0])
        # upper_bound2 = np.array(temp_predicted_prices) + 2 * np.sqrt(kf.P[0, 0])        
        # fuchsia = '#FF00FF'
        # uncertainty_patch = ax1.fill_between(future_dates, lower_bound2, upper_bound2, color=fuchsia, alpha=0.2)
        
        # # Restore the original state
        # kf.x = temp_state
        # kf.P = temp_P

        # Plot the residuals
        residuals = prices[:frame+1] - filtered_prices_np[:frame+1]
        line4.set_data(dates[:frame+1], y_np[:frame+1])

    else:
        logger.info('not possible, frame is greater than len(prices)')
    return line1, line2, line3, line4

def make_ca_filter(dt, std_R):
    cafilter = KalmanFilter(dim_x=3, dim_z=1)
    # cafilter.x = np.array([0., 0., 0.])
    cafilter.P *= 3
    cafilter.R *= std_R*std_R
    cafilter.Q = Q_discrete_white_noise(dim=3, dt=dt, var=0.02)
    cafilter.F = np.array([[1, dt, 0.5*dt*dt],
                           [0, 1,         dt], 
                           [0, 0,          1]])
    cafilter.H = np.array([[1., 0, 0]])
    return cafilter

def make_cv_filter(dt, std_R):
    cvfilter = KalmanFilter(dim_x=2, dim_z=1)
    # cvfilter.x = np.array([0., 0.])
    # cvfilter.P *= 3
    cvfilter.R *= std_R*std_R
    cvfilter.Q = Q_discrete_white_noise(dim=2, dt=dt, var=0.02)
    cvfilter.F = np.array([[1, dt],
                           [0, 1]])
    cvfilter.H = np.array([[1., 0]])
    return cvfilter

def download_bars(contract_: Contract, durationStr, barSizeSetting, endDateTime: datetime.datetime = datetime.datetime.now().date(), **kwargs):
    sym = contract_.symbol
    logger.info(f"Requesting '{durationStr}' '{barSizeSetting}' historical bars for {sym}...")
    histbars: BarDataList = ib.reqHistoricalDataExt( # this method is blocking
        contract_,
        endDateTime='',
        durationStr=durationStr,
        barSizeSetting=barSizeSetting,
        whatToShow='TRADES',
        useRTH=False,
        formatDate=1,
        keepUpToDate=True,
    )
    if histbars is None or len(histbars) == 0:
        logger.error(f"Failed to get historical bars for {sym}")
    else:
        logger.info(f"Received {len(histbars)} bars")
        # global dates, prices
        # dates = histbars.npdate_ # [:histbars._npidx]
        # prices = histbars._average # [:histbars._npidx]
        # logger.info(f'len(dates)={len(dates)}, len(prices)={len(prices)}, idx={histbars._npidx}')

        # histdf = util.df(histbars)
        # if 'open_' in histdf.columns: # rename open_ to open
        #     histdf.rename(columns={'open_':'open'}, inplace=True)
        # if 'timestamp' in histdf.columns: # drop it
        #     histdf.drop(columns=['timestamp'], inplace=True)
        # filename = pathlib.Path(f'./data/{sym}_5s_{endDateTime:%Y%m%d}.csv').resolve()
        # logger.info(f"Writing to {str(filename)}")
        # histdf.to_csv(filename, index=False)
    return histbars

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, 
                        format='%(name)s - %(levelname)s - %(message)s', # %(asctime)s - 
                        handlers=[
                            logging.FileHandler(f"./logs/kalman_filter_{datetime.datetime.now():%Y%m%d_%H%M%S}.log", encoding='utf-8'),
                            logging.StreamHandler(sys.stdout)
                        ])
    logger = logging.getLogger(__name__)

    _today = datetime.datetime.today()
    while _today.weekday() > 4:  # 0 is Monday, 6 is Sunday
        _today -= datetime.timedelta(days=1)


    plt.ion()

    argparser = argparse.ArgumentParser()
    argparser.add_argument('symbols', nargs='*', type=str, help='Just run for this symbol') # nargs='+' means one or more
    argparser.add_argument('--clientid', type=int, help='IBKR API Client ID')
    argparser.add_argument('--host', type=str, default='127.0.0.1', help='Host name')
    argparser.add_argument('--port', type=int, default=7497, help='Port number') # IB Gateway 4001, TWS 7496
    argparser.add_argument('--loglevel', type=str, help='Logging level')
    argparser.add_argument('--date', type=str, help='Date to download data for')
    argparser.add_argument('--live', action='store_true', help='Use IB live data')
    argparser.add_argument('--barsize', type=str, default='1 min', help='Bar size')

    args = argparser.parse_args()
    if args.loglevel and args.loglevel.upper() not in {'INFO'}:
        logger.setLevel(args.loglevel.upper())
    logger.info(args)
    
    wlogger = logging.getLogger('ib_insync.wrapper')
    wlogger.addFilter(LoggerFilter('ib_insync.wrapper', 
        r'^(connectAck|nextValidId|accountDownloadEnd|execDetailsEnd|updateAccountTime|accountUpdateMulti|execDetails'
        r'|updateAccountValue|position|updatePortfolio|commissionReport|historicalData|Info 2104|Info 2106|Info 2158)'
    ))

    if args.symbols is None or len(args.symbols) == 0:
        syms = args.symbols or ['NVDA']
    else:
        syms = args.symbols
    dayoffset: int = 0

    if args.date:
        endDateTime = pd.to_datetime(args.date)
    else:       
        if datetime.datetime.now().time() < datetime.time(9, 30):
            dayoffset = -1
        else:
            dayoffset = 0
        endDateTime = datetime.datetime.combine(datetime.datetime.now().date() + datetime.timedelta(days=dayoffset), datetime.time(21, 0), tzinfo=tz_NY)
    # endDateTime = datetime.datetime.now() + datetime.timedelta(days=0)
    # endDateTime = pd.to_datetime('2024-11-20 21:00:00-05:00')
    if args.live:
        # Connect to IB Gateway
        ib = IB()
        ib.connect(args.host, args.port, clientId=args.clientid or np.random.randint(1_000, 10_000))
        util.patchAsyncio()
        # util.useQt() # can't use here

        for sym in syms:
            contract_ = Stock(sym, 'SMART', 'USD')
            # contract_ = Future('ES', '202503', 'CME')
            temp: ContractDetails = ib.reqContractDetails(contract_)
            if len(temp) == 0:
                logger.error(f"Contract details not found for {sym}")
                continue
            elif len(temp) > 1:
                logger.info(f"Multiple contract details found for {contract_}")
                continue
                # contract_ = temp[0].contract
            else:
                logger.info(f"Contract details {temp[0].contract}")
                contract_ = temp[0].contract
            # logger.info(f"Requesting historical bars for {sym}... ending {endDateTime}")
            bars = download_bars(contract_, '1 D', args.barsize)
            if not bars:
                # logger.error(f"Failed to get historical bars for {sym}")
                sys.exit(1)
            # initialize prices, log_prices, dates, high_minus_low (arrays)
            # the arrays will grow
            # initialize base_price, log_base_price (scalars)

            # prices = np.array([bar.close for bar in bars])
            prices = bars._average
            base_price = prices[0] if (n:=len(prices)) > 0 else 1
            log_base_price = np.log(base_price)
            log_prices = bars.log_average_
            high_minus_low = bars.high_prices - bars.low_prices
            dates = bars.npdate_
            logger.info(f'len(dates)={len(dates)}, len(prices)={len(prices)}, idx={bars._npidx}')
    
    else: # not live
        sym = syms[0] # 'NVDA'

        date = f'{datetime.datetime.now()+datetime.timedelta(days=-5):%Y%m%d}'
        # date = f'{_today:%Y%m%d}'
        filename = f'{sym}_1d.csv'
        filename = f'{sym}_1m_{date}.csv'
        bars = None
        bars_df = pd.read_csv(rf'C:\Users\Jimmy\source\erdewit\ib_insync\notebooks\data\{filename}', parse_dates=['date'])
        buffer = io.StringIO()
        bars_df.info(buf=buffer)
        logger.info(f'{buffer.getvalue()}')

        # Filter bars_df for the time range from 9:30am to 4:00pm
        bars_df['date'] = bars_df['date'].dt.tz_localize(None)
        m0 = bars_df['date'].dt.time >= datetime.time(9, 30)
        m99 = bars_df['date'].dt.time <= datetime.time(16, 0)
        m1 = m0 & m99
        df = bars_df.loc[m1]

        # initialize prices, log_prices, dates, high_minus_low (arrays)
        # the arrays are static and do not grow
        # initialize base_price, log_base_price (scalars)

        prices = df['average'].values
        base_price = prices[0]
        log_base_price = np.log(base_price)
        log_prices = np.log(prices)
        high_minus_low = (df['high'] - df['low']).values
        dates = df['date'].values

    logger.info(f'dates={dates[:3]}' f', prices={prices[:3]}, log_prices={log_prices[:3]}')
    logger.info(f'base_price={base_price}, log_base_price={log_base_price}')
    logger.info(f'high_minus_low={high_minus_low[:3]}')

    # set up kalman filter
    # Define the initial state
    dt = 1.0
    initial_price = 0 # log_prices[0] - log_base_price # shifted log price = log return centered around base price
    # logger.info(f"prices: {prices[max(0, bars._npidx-5):bars._npidx]}")
    x_initial = np.array([initial_price, 0])  # Initial state [price, velocity]
    measurement_noise_scale = .006**2  # increase to make the curve smoother
    process_noise = .006**2      # reduce to make the curve smoother
    display_uncertainty = True

    # Define the process and measurement noise
    # points = MerweScaledSigmaPoints(2, alpha=0.1, beta=2., kappa=0)
    # kf = KalmanFilter(dim_x=2, dim_z=1, fx=fx, hx=hx, dt=dt, points=points)
    kf = make_cv_filter(dt, 0.1)
    kf.x = x_initial
    logger.info(f'initial state: {kf.x}')
    kf.P *= (0.01**2)  # Initial covariance
    logger.info(f"initial covariance: {kf.P}")
    measurement_noise = measurement_noise_scale # 5% of price
    kf.R = measurement_noise  # Measurement noise
    logger.info(f"measurement noise: {kf.R}")
    kf.Q = Q_discrete_white_noise(dim=2, dt=dt, var=1) * process_noise  # Process noise
    kf.Q[1, 1] = process_noise
    logger.info(f"process noise: {kf.Q}")

    saver = Saver(kf)

    logger.info(f"{kf}")
    # Run the filter on historical data
    # filtered_prices = []
    # means, covs = kf.batch_filter(prices, saver=saver)
    # filtered_prices = [mean[0] for mean in means]
    # print(means, covs)
    # print(saver.to_array())
    # # sys.exit(0)

    # # for price in prices:
    # #     kf.predict()
    # #     kf.update(np.array([price]))
    # #     filtered_prices.append(kf.x[0])
    if args.live:
        filtered_prices_np = np.zeros_like(prices)
        hidden_var1 = np.zeros_like(prices)
        y_np = np.zeros_like(prices)
        K_np = np.zeros_like(prices)

    else:
        filtered_prices_np = np.zeros_like(prices)
        hidden_var1 = np.zeros_like(prices)
        y_np = np.zeros_like(prices)
        K_np = np.zeros_like(prices)

    # Initialize peak and trough tracking
    min_peaks_required = 2
    peaks = []
    troughs = []

    # Prepare the figure for animation
    fig = plt.figure()
    fig.canvas.mpl_connect('close_event', on_close)

    gs = fig.add_gridspec(5, 1)
    ax1 = fig.add_subplot(gs[:3, 0])  # ax1 takes the first three rows
    ax2 = fig.add_subplot(gs[3, 0])   # ax2 takes the last row
    ax3 = fig.add_subplot(gs[4, 0])   # ax3 takes the last row
    line1, = ax1.plot([], [], label='Original Prices')
    line2, = ax1.plot([], [], linestyle='--', label='Filtered Prices')
    line3, = ax1.plot([], [], linestyle='--', color='green', label='Predicted Prices')
    uncertainty_patch = None

    ax1.set_ylabel('Price')
    ax1.set_title('Original vs. Filtered vs. Predicted (meas=' + str(measurement_noise) + ",proc=" + str(process_noise) + ")")
    ax1.legend()

    line4, = ax2.plot([], [], label='Residuals', color='red')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Residuals')
    ax2.legend()

    line5, = ax3.plot([], [], label='Hidden Variable 1', color='blue')
    ax3.set_xlabel('Date')
    ax3.set_ylabel('Hidden Variable 1')
    ax3.legend()

    qapp = QtWidgets.QApplication.instance()
    if not qapp:
        qapp = QtWidgets.QApplication(sys.argv)
        logger.info(f'Starting QApplication {qapp}')
    else:
        logger.info(f'Using existing QApplication {qapp}')
    # plt.show(block=False)

    # Predict future prices
    future_days = 10  # Number of days to predict into the future
    predicted_prices = []

    if args.live and bars:
        util.useQt()
    else:
        # Create animation
        ani = animation.FuncAnimation(fig, update, frames=len(prices), init_func=init_animation, blit=False, interval=500, repeat=False)

    # Save the animation as a GIF
    uncertainty = ""
    if display_uncertainty:
        uncertainty = "_uncertainty"
    # ani.save("stock_prices_animation.m" + str(measurement_noise) + ".p" + str(process_noise) + uncertainty + ".gif", writer='pillow')

    init_animation()
    if args.live:
        onInitialBars(bars) # run through the initial bars
        ib.barUpdateEvent += onBarUpdate # starts processing live bars
        plt.show(block=False)
        IB.run()
    else:
        plt.show(block=True)
    logger.info('done.')

    # main()
