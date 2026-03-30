import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import time
import datetime
import pandas as pd
import numpy as np
from scipy.ndimage import gaussian_filter1d
import logging
import sys
import inspect
import pathlib

import os, sys
parent_dir = os.path.abspath('..')
if parent_dir not in sys.path:
    # sys.path.append(parent_dir)
    sys.path.insert(0, parent_dir)
    print(f"{parent_dir} added to sys.path")

# search_dirs = ['..']
# pkg_needed = ['eventkit', 'ib_insync'] # , 'rlabbe/filterpy', 'jj625/python-telegram-bot', 'jj625/mplfinance'
# pkg_dirs = {}

# for pkg in pkg_needed:
#     for dir in search_dirs:
#         potential_dir = pathlib.Path(dir, pkg).resolve()
#         if potential_dir.exists() and potential_dir.is_dir():
#             pkg_dirs[pkg] = potential_dir
#             break

# for pkg, pkg_dir in pkg_dirs.items():
#     if str(pkg_dir) not in sys.path:
#         sys.path.insert(0, str(pkg_dir))
#         print(f"{pkg_dir} added to sys.path")

# missing_pkgs = [pkg for pkg in pkg_needed if pkg not in pkg_dirs]
# if missing_pkgs:
#     print(f"Expected directories not found for: {', '.join(missing_pkgs)}")

import ib_insync
import ib_insync.util as util
print(inspect.getfile(ib_insync))

plt.ion()  # Turn on interactive mode
# util.logToConsole(logging.INFO)
sym = 'SPY'

date = f'{datetime.datetime.now()+datetime.timedelta(days=-2):%Y%m%d}'
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

# fig = plt.figure(figsize=(9, 6))
fig, ax = plt.subplots()
for i in range(1, vector.size + 1):
    # plt.clf()  # Clear the current figure
    # plt.ylim(vector.min(), vector.max())
    ax.clear()
    ax.set_ylim(vector.min(), vector.max())
    # util.barplot(bars_df[m1].iloc[:i], fig_ax=(fig, ax))
    running_vector = vector[:i]
    smoothed_vector_3n = gaussian_filter1d(running_vector, sigma=16, mode='nearest')
    der1 = gaussian_filter1d(running_vector, sigma=16, mode='nearest', order=1)
    
    ax.plot(running_vector, label='Running Vector', alpha=0.5)
    ax.plot(smoothed_vector_3n, label="Smoothed Vector (sigma=16, mode='nearest')")
    # plt.xticks(ticks=np.arange(max(0, i-60), i), labels=x_axis_values[max(0, i-60):i].dt.strftime('%H:%M'))
    # plt.gca().xaxis.set_major_locator(ticker.MultipleLocator(5))
    ax2 = plt.twinx()
    ax2.plot(der1, color='g', alpha=0.5) # , label="slope (sigma=3, mode='nearest', order=1)"
    ax2.set_ylim(der1_full.min(), der1_full.max())
    last_point_slope = der1[-1]
    last_point_slope_text = 'positive' if last_point_slope > 0 else 'negative'
    ax.text(0.95, 0.95, f'Slope: {last_point_slope*100:.1%} {last_point_slope_text}', horizontalalignment='right', verticalalignment='top', transform=ax.transAxes)
    ax.legend()
    ax.set_title('Running and Smoothed Vectors')
    ax.set_xlabel('Index')
    ax.set_ylabel('Value')
    ax.grid(True)
    
    plt.pause(0.5)  # Pause for 0.5 seconds
    
    if not plt.fignum_exists(fig.number):  # Check if the current figure is closed
        break
    # if plt.waitforbuttonpress(timeout=0.1):
    #     if plt.get_current_fig_manager().canvas.manager.key_press_handler_id == 'q':
    #         break

plt.ioff()  # Turn off interactive mode
plt.show()
