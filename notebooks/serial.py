import serial
import pandas as pd
import numpy as np
from scipy.signal import butter, lfilter, find_peaks
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Data acquisition from serial port
ser = serial.Serial('COM3', 9600)
data = []

# Bandpass filter
def butter_bandpass(lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def bandpass_filter(data, lowcut, highcut, fs, order=5):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = lfilter(b, a, data)
    return y

# Wave detection
def detect_waves(data, height=None, distance=None):
    peaks, _ = find_peaks(data, height=height, distance=distance)
    return peaks

# Real-time plotting
fig, ax = plt.subplots()
line, = ax.plot(data)

def update(frame):
    line.set_ydata(data)
    return line,

ani = animation.FuncAnimation(fig, update, blit=True)

# Main loop
fs = 1000  # Sampling frequency
lowcut = 0.1
highcut = 10.0

while True:
    line = ser.readline().decode('utf-8').strip()
    data.append(float(line))
    if len(data) > 1000:  # Keep only the last 1000 data points
        data.pop(0)
    
    filtered_data = bandpass_filter(data, lowcut, highcut, fs)
    peaks = detect_waves(filtered_data, height=0.5, distance=50)
    
    ax.clear()
    ax.plot(filtered_data)
    ax.plot(peaks, filtered_data[peaks], "x")
    plt.pause(0.01)

plt.show()
