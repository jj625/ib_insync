import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import TimedAnimation

class AnimatedSinusoidalPlot:
    def __init__(self):
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(10, 8))
        self.x = np.linspace(0, 2 * np.pi, 100)
        self.frame = 0
        
        # Create initial data
        self.y = self.data_generator()
        self.diff = np.diff(self.y)
        
        # Set up the initial plot
        self.line, = self.ax1.plot(self.x, self.y, label='sin(x)')
        self.ax1.set_title('Sinusoidal Function')
        self.ax1.legend()
        
        self.bar_rects = self.ax2.bar(self.x[1:], self.diff, color=['blue' if d > 0 else 'red' for d in self.diff])
        self.ax2.set_title('Serial Differences')
        
        # Start the animation with a timer
        self.timer = self.fig.canvas.new_timer(interval=50)
        self.timer.add_callback(self.update)
        self.timer.start()
    
    def data_generator(self):
        self.frame += 0.1
        return np.sin(self.x + self.frame)

    def update(self):
        self.y = self.data_generator()
        self.diff = np.diff(self.y)
        self.line.set_ydata(self.y)
        
        for rect, h in zip(self.bar_rects, self.diff):
            rect.set_height(h)
            rect.set_color('blue' if h > 0 else 'red')
        
        self.fig.canvas.draw_idle()

    def show(self):
        plt.tight_layout()
        plt.show()

# Create an instance of the class and start the animation
plot = AnimatedSinusoidalPlot()
plot.show()
