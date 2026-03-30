import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Generate data
x = np.linspace(0, 2 * np.pi, 100)
y = np.sin(x)

# Calculate the serial differences
diff = np.diff(y)

# Create subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

# Top subplot: Sinusoidal line chart
line, = ax1.plot(x, y, label='sin(x)')
ax1.set_title('Sinusoidal Function')
ax1.legend()

# Bottom subplot: Bar chart of serial differences
bar_rects = ax2.bar(x[1:], diff, color=['blue' if d > 0 else 'red' for d in diff])
ax2.set_title('Serial Differences')

# Animation function
def update(frame):
    y = np.sin(x + frame * 0.1)
    diff = np.diff(y)
    line.set_ydata(y)
    
    for rect, h in zip(bar_rects, diff):
        rect.set_height(h)
        rect.set_color('blue' if h > 0 else 'red')
    return line, *bar_rects

# Create animation
ani = animation.FuncAnimation(fig, update, frames=100, interval=50, blit=True)

# Display the plot
plt.tight_layout()
plt.show()
