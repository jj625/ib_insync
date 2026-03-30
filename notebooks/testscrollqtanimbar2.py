import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QScrollArea
from PyQt5.QtCore import QTimer, Qt, QEvent
import threading
import time

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

class ScrollablePlot(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Create a scroll area
        self.scroll_area = QScrollArea(self)
        self.scroll_area_widget = QWidget()
        self.scroll_area.setWidget(self.scroll_area_widget)
        self.scroll_area.setWidgetResizable(True)
        self.layout.addWidget(self.scroll_area)

        # Create matplotlib figure and axes
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(10, 8))
        self.canvas = FigureCanvas(self.fig)
        self.scroll_area_layout = QVBoxLayout(self.scroll_area_widget)
        self.scroll_area_layout.addWidget(self.canvas)

        # Initialize data generator
        self.data_generator = DataGenerator()
        self.data_generator.start()

        # Initialize plot
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
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(50)

        # Event filter to capture key events
        self.installEventFilter(self)

        self.show()

    def update_plot(self):
        if self.data_generator.data is not None:
            self.y = self.data_generator.data
            self.diff = np.diff(self.y)
            self.line.set_ydata(self.y)

            for rect, h in zip(self.bar_rects, self.diff):
                rect.set_height(h)
                rect.set_color('blue' if h > 0 else 'red')

            self.canvas.draw_idle()

    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Q:
            self.close()
        return super().eventFilter(source, event)

    def closeEvent(self, event):
        self.data_generator.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = ScrollablePlot()
    sys