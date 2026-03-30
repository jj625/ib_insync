import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time
import threading

class DataGenerator:
    def __init__(self):
        self.frame = 0
        self.data = None
        self.running = True
        self.interval = 0.1

    def generate_data(self):
        while self.running:
            self.frame += self.interval
            self.data = np.sin(np.linspace(0, 2 * np.pi, 100) + self.frame)
            time.sleep(self.interval)

    def start(self):
        self.thread = threading.Thread(target=self.generate_data)
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()

class AnimatedSinusoidalPlot:
    def __init__(self, data_generator):
        self.data_generator = data_generator
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(10, 8))

        # Initialize data
        self.x = np.linspace(0, 2 * np.pi, 100)
        self.y = self.data_generator.data if self.data_generator.data is not None else np.sin(self.x)
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

    def update(self):
        if self.data_generator.data is not None:
            self.y = self.data_generator.data
            self.diff = np.diff(self.y)
            self.line.set_ydata(self.y)
            
            for rect, h in zip(self.bar_rects, self.diff):
                rect.set_height(h)
                rect.set_color('blue' if h > 0 else 'red')
        
            self.fig.canvas.draw_idle()

    def show(self):
        plt.tight_layout()
        plt.show()

# Create a DataGenerator instance
data_gen = DataGenerator()
data_gen.start()

# Create an instance of the plot class and start the animation
plot = AnimatedSinusoidalPlot(data_gen)
plot.show()

# Stop the data generator after showing the plot
data_gen.stop()
