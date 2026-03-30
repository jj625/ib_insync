import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

class AnimatedSinusoidalPlot:
    def __init__(self):
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(10, 8))
        self.x = np.linspace(0, 2 * np.pi, 100)
        self.y = np.sin(self.x)
        self.diff = np.diff(self.y)

        # Set up the initial plot
        self.line, = self.ax1.plot(self.x, self.y, label='sin(x)')
        self.ax1.set_title('Sinusoidal Function')
        self.ax1.legend()

        self.bar_rects = self.ax2.bar(self.x[1:], self.diff, color=['blue' if d > 0 else 'red' for d in self.diff])
        self.ax2.set_title('Serial Differences')

    def update(self, frame):
        self.y = np.sin(self.x + frame * 0.1)
        self.diff = np.diff(self.y)
        self.line.set_ydata(self.y)
        
        for rect, h in zip(self.bar_rects, self.diff):
            rect.set_height(h)
            rect.set_color('blue' if h > 0 else 'red')
        return self.line, *self.bar_rects

    def animate(self):
        self.ani = animation.FuncAnimation(self.fig, self.update, frames=100, interval=50, blit=True)
        plt.tight_layout()
        plt.show()

# Create an instance of the class and start the animation
plot = AnimatedSinusoidalPlot()
plot.animate()
