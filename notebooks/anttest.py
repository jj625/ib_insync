import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import time
import datetime
_today = datetime.datetime.today()
while _today.weekday() > 4:  # 0 is Monday, 6 is Sunday
    _today -= datetime.timedelta(days=1)
import pandas as pd
import numpy as np
# from scipy.ndimage import gaussian_filter1d
import antropy as ant
import logging
import collections

plt.ion()  # Turn on interactive mode
# util.logToConsole(logging.INFO)
sym = 'MSFT'

date = f'{datetime.datetime.now()+datetime.timedelta(days=-1):%Y%m%d}'
date = f'{_today:%Y%m%d}'
filename = f'{sym}_1m_{date}.csv'
load_from_csv = True
bars = None
if load_from_csv:
    bars_df = pd.read_csv(rf'.\data\{filename}', parse_dates=['date'])

# Filter bars_df for the time range from 9:30am to 4:00pm
m0 = bars_df['date'].dt.time >= datetime.time(9, 30)
m99 = bars_df['date'].dt.time <= datetime.time(16, 0)
m1 = m0 & m99

x_axis_values = bars_df[m1]['date']
vector = np.asarray(bars_df[m1]['average'])
# der1_full = gaussian_filter1d(vector, sigma=16, mode='nearest', order=1)

# fig = plt.figure() # figsize=(9, 6)
# fig, ax = plt.subplots()
d = collections.defaultdict(list)
for t in pd.date_range(start='9:30', end='16:00', freq='5min'):
# for i in range(10, vector.size + 1):
    i = x_axis_values[x_axis_values.dt.time == t.time()].index[0]
    # plt.clf()  # Clear the current figure
    # plt.ylim(vector.min(), vector.max())
    # fig.clf()
    # ax.set_ylim(vector.min(), vector.max())
    x = vector[:i]
    print(f"i={i}, t={t}")
    d['i'].append(i)
    d['t'].append(t)
    # print(x)
    # print(ant.shannon_entropy(x))
    # print(ant.perm_entropy(x))
    d['perm_entropy'].append(ant.perm_entropy(x))
    # print(ant.spectral_entropy(x, sf=1))
    d['spectral_entropy'].append(ant.spectral_entropy(x, sf=1))
    # print(ant.svd_entropy(x))
    d['svd_entropy'].append(ant.svd_entropy(x))
    # print(ant.app_entropy(x))
    d['app_entropy'].append(ant.app_entropy(x))
    # print(ant.sample_entropy(x))
    d['sample_entropy'].append(ant.sample_entropy(x))
    # print(ant.multiscale_entropy(x, order=2, scale=2))
    # print(ant.multiscale_permutation_entropy(x, order=3, scale=2))
    # print(ant.multiscale_sample_entropy(x, order=2, scale=2))
    # print(ant.fuzzy_entropy(x, order=2, metric='chebyshev'))
    # print(ant.fisher_info(x, tau=1, DE=0.1))
    # print(ant.higuchi_fd(x))
    # print(ant.katz_fd(x))
    d['katz_fd'].append(ant.katz_fd(x))
    # print(ant.hurst_rs(x))
    # print(ant.dfa(x))
    # print(ant.petrosian_fd(x))
    d['petrosian_fd'].append(ant.petrosian_fd(x))
    # print(ant.detrended_fluctuation(x))
    d['detrended_fluctuation'].append(ant.detrended_fluctuation(x))
    # print(ant.hjorth(x))
    # print(ant.hjorth_fd(x))
    # print(ant.pfd(x))
    # print(ant.sefd(x))
    # print(ant.sampen(x, order=2, metric='chebyshev'))

    # smoothed_vector_3n = gaussian_filter1d(running_vector, sigma=16, mode='nearest')
    # der1 = gaussian_filter1d(running_vector, sigma=16, mode='nearest', order=1)
    
    # plt.plot(running_vector, scalex=True, scaley=True, label='Running Vector', alpha=0.5)
    # plt.plot(smoothed_vector_3n, label="Smoothed Vector (sigma=16, mode='nearest')")
    # plt.xticks(ticks=np.arange(max(0, i-60), i), labels=x_axis_values[max(0, i-60):i].dt.strftime('%H:%M'))
    # plt.gca().xaxis.set_major_locator(ticker.MultipleLocator(5))
    # ax2 = plt.twinx()
    # ax2.plot(der1, color='g', alpha=0.5) # , label="slope (sigma=3, mode='nearest', order=1)"
    # ax2.set_ylim(der1_full.min(), der1_full.max())
    # last_point_slope = der1[-1]
    # last_point_slope_text = 'positive' if last_point_slope > 0 else 'negative'
    # plt.text(0.95, 0.95, f'Slope: {last_point_slope*100:.1%} {last_point_slope_text}', horizontalalignment='right', verticalalignment='top', transform=plt.gca().transAxes)
    # plt.legend()
    # ax.set_title('Running and Smoothed Vectors')
    # ax.set_xlabel('Index')
    # ax.set_ylabel('Value')
    # plt.grid(True)
    
    # plt.pause(0.1)  # Pause for 0.2 seconds
    
    # if not plt.fignum_exists(fig.number):  # Check if the current figure is closed
    #     break
    # if plt.waitforbuttonpress(timeout=0.1):
    #     if plt.get_current_fig_manager().canvas.manager.key_press_handler_id == 'q':
    #         break

# plt.ioff()  # Turn off interactive mode
# plt.show()
pd.DataFrame(d).to_csv(f'{sym}_1m_{date}_antropy.csv', index=False) 