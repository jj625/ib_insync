# This project uses Kalman Filter (UKF) created by Roger Labbe and available
# at https://github.com/rlabbe/filterpy, which is distributed under the MIT License.
# See the LICENSE file for more details at https://github.com/rlabbe/filterpy/blob/master/LICENSE
import sys
import io
import datetime
import logging

# import yfinance as yf
import numpy as np
np.set_printoptions(precision=6, suppress=True)
from filterpy.kalman import UnscentedKalmanFilter as UKF, KalmanFilter
from filterpy.kalman import MerweScaledSigmaPoints
from filterpy.common import Q_discrete_white_noise, Saver
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import pandas as pd
import matplotlib.animation as animation
# from scipy.signal import find_peaks
# from sklearn.linear_model import LinearRegression
# from PIL import Image  # Import Pillow library
    
# # Fetch the stock price data
# aapl = yf.Ticker("AAPL")
# data = aapl.history(period="1y")

# # Extract the 'Close' prices
# prices = data['Close'].values
# dates = data.index

# Initialize the plot limits and lines
def init():
    ax1.set_xlim(dates[0], dates[-1])
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M')) # %Y-%m-%d %H:%M:%S
    ax1.set_ylim(min(prices) * 0.9, max(prices) * 1.1)
    ax2.set_xlim(dates[0], dates[-1])
    ax2.set_ylim(-.01, .01)
    ax3.set_xlim(dates[0], dates[-1])
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M')) # %Y-%m-%d %H:%M:%S
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

    # # Clear previous uncertainty patch
    # if uncertainty_patch is not None:
    #     uncertainty_patch.remove()
    #     uncertainty_patch = None

    if frame < len(prices):
        # kf.R = high_minus_low[frame] / 4.0
        kf.predict()
        kf.update(np.array([prices[frame]]))
        filtered_prices_np[frame] = kf.x[0]
        hidden_var1[frame] = kf.x[1]
        y_np[frame] = kf.y[0]
        logger.info(f'frame={frame}, '  f'date={pd.to_datetime(dates[frame]):%H:%M}, ' # %Y%m%d 
            f'price={prices[frame]:.6f} {np.exp(prices[frame])*rawprices[0]}, x0={kf.x[0]:.6f}, y={kf.y[0]:.6f}, K0={kf.K[0][0]:.2f}, √P0={np.sqrt(kf.P[0, 0]):.6f}, '
            f'x1={kf.x[1]:.6f}, K1={kf.K[1][0]:.6f}, '
            f'√P1={np.sqrt(kf.P[1, 1]):.6f}, P[0,1]={kf.P[0, 1]:.6f}'
        )        
        line1.set_data(dates[:frame+1], prices[:frame+1])
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
    cvfilter.P *= 3
    cvfilter.R *= std_R*std_R
    cvfilter.Q = Q_discrete_white_noise(dim=2, dt=dt, var=0.02)
    cvfilter.F = np.array([[1, dt],
                           [0, 1]])
    cvfilter.H = np.array([[1., 0]])
    return cvfilter

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

    np.set_printoptions(linewidth=150, precision=2, suppress=True)

    plt.ion()

    sym = 'NVDA'

    date = f'{datetime.datetime.now()+datetime.timedelta(days=-3):%Y%m%d}'
    # date = f'{_today:%Y%m%d}'
    filename = f'{sym}_1d.csv'
    filename = f'{sym}_1m_{date}.csv'
    load_from_csv = True
    bars = None
    if load_from_csv:
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
    rawprices = df['close'].values
    logger.info(f'rawprices={rawprices[:5]}')
    # prevclose = 132.43
    prices = np.log(rawprices/rawprices[0])
    high_minus_low = (df['high'] - df['low']).values
    dates = df['date'].values
    logger.info(f'dates={dates[:5]}')

    # Define the initial state
    dt = 1.0
    initial_price = prices[0]
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

    # Run the filter on historical data
    filtered_prices = []
    # means, covs = kf.batch_filter(prices, saver=saver)
    # filtered_prices = [mean[0] for mean in means]
    # print(means, covs)
    # print(saver.to_array())
    # # sys.exit(0)

    # # for price in prices:
    # #     kf.predict()
    # #     kf.update(np.array([price]))
    # #     filtered_prices.append(kf.x[0])
    filtered_prices_np = np.array(filtered_prices)
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
    gs = fig.add_gridspec(5, 1)
    ax1 = fig.add_subplot(gs[:3, 0])  # ax1 takes the first three rows
    ax2 = fig.add_subplot(gs[3, 0])   # ax2 takes the last row
    ax3 = fig.add_subplot(gs[4, 0])   # ax3 takes the last row
    line1, = ax1.plot([], [], label='Original Prices')
    line2, = ax1.plot([], [], linestyle='--', label='Filtered Prices')
    line3, = ax1.plot([], [], linestyle='--', color='green', label='Predicted Prices')
    uncertainty_patch = None

    ax1.set_ylabel('Price')
    ax1.set_title('AAPL Stock Prices - Original vs. Filtered vs. Predicted (meas=' + str(measurement_noise) + ",proc=" + str(process_noise) + ")")
    ax1.legend()

    line4, = ax2.plot([], [], label='Residuals', color='red')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Residuals')
    ax2.legend()

    line5, = ax3.plot([], [], label='Hidden Variable 1', color='blue')
    ax3.set_xlabel('Date')
    ax3.set_ylabel('Hidden Variable 1')
    ax3.legend()

    # Predict future prices
    future_days = 10  # Number of days to predict into the future
    predicted_prices = []

    # Create animation
    ani = animation.FuncAnimation(fig, update, frames=len(prices), init_func=init, blit=False, interval=500, repeat=False)

    # Save the animation as a GIF
    uncertainty = ""
    if display_uncertainty:
        uncertainty = "_uncertainty"
    # ani.save("stock_prices_animation.m" + str(measurement_noise) + ".p" + str(process_noise) + uncertainty + ".gif", writer='pillow')

    plt.ioff()
    plt.show(block=True)
    logger.info('after plt.show()')

    logger.info('done.')

    # main()
