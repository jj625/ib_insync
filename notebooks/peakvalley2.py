import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

class IntradayPeakValleyDetector:
    def __init__(self, window_size=50):
        self.window_size = window_size
        self.prices = []
        self.peaks = []
        self.valleys = []
        self.current_time = None
        self.all_times = []
        self.all_prices = []

    def process_price(self, timestamp, price):
        self.current_time = timestamp
        self.prices.append(price)
        self.all_times.append(timestamp)
        self.all_prices.append(price)

        if len(self.prices) >= self.window_size:
            mid = self.window_size // 2
            window = self.prices[-self.window_size:]

            if all(window[mid] > p for p in window[:mid]) and all(window[mid] > p for p in window[mid+1:]):
                self.peaks.append((self.current_time, window[mid]))
            elif all(window[mid] < p for p in window[:mid]) and all(window[mid] < p for p in window[mid+1:]):
                self.valleys.append((self.current_time, window[mid]))

            self.prices.pop(0)

    def get_results(self):
        return {
            'peaks': self.peaks,
            'valleys': self.valleys,
            'times': self.all_times,
            'prices': self.all_prices
        }

# Set up the plot
plt.figure(figsize=(12, 6))
plt.title("Intraday Stock Price with Peaks and Valleys")
plt.xlabel("Time")
plt.ylabel("Price")

line, = plt.plot([], [], 'b-')
peaks_scatter = plt.scatter([], [], color='red', marker='^', s=100, label='Peak')
valleys_scatter = plt.scatter([], [], color='green', marker='v', s=100, label='Valley')
plt.legend()

detector = IntradayPeakValleyDetector()

# Simulate streaming prices (replace this with real-time data feed)
timestamps = pd.date_range(start='2025-02-05 09:30:00', end='2025-02-05 16:00:00', freq='1min')
prices = np.random.randn(len(timestamps)).cumsum() + 100

def animate(i):
    if i < len(timestamps):
        detector.process_price(timestamps[i], prices[i])
        results = detector.get_results()
        
        line.set_data(results['times'], results['prices'])
        
        peak_times, peak_prices = zip(*results['peaks']) if results['peaks'] else ([], [])
        peaks_scatter.set_offsets(np.c_[peak_times, peak_prices])
        
        valley_times, valley_prices = zip(*results['valleys']) if results['valleys'] else ([], [])
        valleys_scatter.set_offsets(np.c_[valley_times, valley_prices])
        
        plt.xlim(min(results['times']), max(results['times']))
        plt.ylim(min(results['prices']) - 1, max(results['prices']) + 1)
        
    return line, peaks_scatter, valleys_scatter

ani = FuncAnimation(plt.gcf(), animate, frames=len(timestamps), interval=50, blit=True, repeat=False)
plt.show()

# Print final results
results = detector.get_results()
print("\nPeaks:")
for peak in results['peaks']:
    print(f"Time: {peak[0]}, Price: {peak[1]:.2f}")

print("\nValleys:")
for valley in results['valleys']:
    print(f"Time: {valley[0]}, Price: {valley[1]:.2f}")
