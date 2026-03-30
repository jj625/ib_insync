import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QScrollBar, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QEvent, QTimer

class ScrollablePlot(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.plot_data()

        self.installEventFilter(self)

        # Create a timer to handle resize events
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.on_resize)

    def initUI(self):
        self.setWindowTitle('Scrollable Plot')
        self.setGeometry(100, 100, 800, 600)

        # Create a vertical layout
        layout = QVBoxLayout()
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_widget.setLayout(layout)

        # Create the figure and canvas
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # Add the navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)

        # Create the scrollbar
        self.scrollbar = QScrollBar(Qt.Horizontal, self)
        self.scrollbar.valueChanged.connect(self.update_plot)
        layout.addWidget(self.scrollbar)

    def plot_data(self):
        x = self.x = np.linspace(0, 1000, 1000)
        y = self.y = np.sin(x)
        self.update_plot(0)

    def update_plot(self, value):
        # Update the plot based on the scrollbar value
        self.value = value
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_xlim(value, value + 100)
        ax.plot(self.x, self.y)
        self.figure.tight_layout()
        self.canvas.draw()

    def eventFilter(self, source, event):
        # Call tight_layout on window resize
        if event.type() == QEvent.Resize:
            self.resize_timer.start(100)
            # self.figure.tight_layout()
            # self.canvas.draw()
            # self.update_plot(self.value)
        return super().eventFilter(source, event)

    def on_resize(self):
        # Call tight_layout on window resize
        self.figure.tight_layout()
        self.canvas.draw()
    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ScrollablePlot()
    window.show()
    sys.exit(app.exec_())
