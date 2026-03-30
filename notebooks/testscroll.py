import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
import tkinter as tk

# Generate some sample data
x = np.linspace(0, 100, 10000)
y = np.sin(x)

# Create a figure and axis
fig, ax = plt.subplots()
plt.subplots_adjust(bottom=0.25)
line, = ax.plot(x, y)

# Adjust the viewing window
initial_range = 100  # Number of data points to display at once
ax.set_xlim(0, initial_range)

# Create a slider axis
slider_ax = plt.axes([0.1, 0.1, 0.8, 0.03], facecolor='lightgoldenrodyellow')

# Define the slider
slider = Slider(
    ax=slider_ax,
    label='Scroll',
    valmin=0,
    valmax=len(x) - initial_range,
    valinit=0,
    valstep=1
)

# Update function
def update(val):
    pos = slider.val
    ax.set_xlim(pos, pos + initial_range)
    fig.canvas.draw_idle()

# Assign the update function to the slider
slider.on_changed(update)

# Show the plot
plt.show()
