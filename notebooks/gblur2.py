import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import time
import datetime
import pandas as pd
import numpy as np
from scipy.ndimage import gaussian_filter1d
import logging

plt.ion()  # Turn on interactive mode
# util.logToConsole(logging.INFO)
sym = 'SPY'

date = f'{datetime.datetime.now()+datetime.timedelta(days=-1):%Y%m%d}'
filename = f'{sym}_1m_{date}.csv'
load_from_csv = True
bars = None
if load_from_csv:
    bars_df = pd.read_csv(rf'.\data\{filename}', parse_dates=['date'])

# Filter bars_df for the time range from 9:30am to 4:00pm
m1 = (bars_df['date'].dt.time >= datetime.time(9, 30)) & (bars_df['date'].dt.time <= datetime.time(16, 0))

x_axis_values = bars_df[m1]['date']
vector = np.asarray(bars_df[m1]['average'])
der1_full = gaussian_filter1d(vector, sigma=16, mode='nearest', order=1)

plt.figure(figsize=(9, 6))
for i in range(1, vector.size + 1):
    plt.clf()  # Clear the current figure
    plt.ylim(vector.min(), vector.max())
    running_vector = vector[:i]
    smoothed_vector_3n = gaussian_filter1d(running_vector, sigma=16, mode='nearest')
    der1 = gaussian_filter1d(running_vector, sigma=16, mode='nearest', order=1)
    
    plt.plot(running_vector, label='Running Vector', alpha=0.5)
    plt.plot(smoothed_vector_3n, label="Smoothed Vector (sigma=16, mode='nearest')")
    # plt.xticks(ticks=np.arange(max(0, i-60), i), labels=x_axis_values[max(0, i-60):i].dt.strftime('%H:%M'))
    # plt.gca().xaxis.set_major_locator(ticker.MultipleLocator(5))
    # ax2 = plt.twinx()
    # ax2.plot(der1, color='g', alpha=0.5) # , label="slope (sigma=3, mode='nearest', order=1)"
    # ax2.set_ylim(der1_full.min(), der1_full.max())
    last_point_slope = der1[-1]
    last_point_slope_text = 'positive' if last_point_slope > 0 else 'negative'
    plt.text(0.95, 0.95, f'Slope: {last_point_slope*100:.1%} {last_point_slope_text}', horizontalalignment='right', verticalalignment='top', transform=plt.gca().transAxes)
    plt.legend()
    plt.title('Running and Smoothed Vectors')
    plt.xlabel('Index')
    plt.ylabel('Value')
    plt.grid(True)
    
    plt.pause(0.5)  # Pause for 0.2 seconds
    
    if not plt.fignum_exists(plt.gcf().number):  # Check if the current figure is closed
        break
    # if plt.waitforbuttonpress(timeout=0.1):
    #     if plt.get_current_fig_manager().canvas.manager.key_press_handler_id == 'q':
    #         break

plt.ioff()  # Turn off interactive mode
plt.show()
