from PyQt5 import QtCore, QtGui, QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

class MplCanvas(QtWidgets.QWidget):
    def __init__(self, parent = None, width=6, height=5, dpi=100):
        QtWidgets.QWidget.__init__(self).__init__(self, parent)
        fig = Figure(figsize=(width,height), dpi=dpi)
        self.canvas = FigureCanvas(fig)
        self.axes = fig.add_subplot(111)
        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.canvas.updateGeometry()
        self.mpl_toolbar = NavigationToolbar(self.canvas, self)
        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(self.mpl_toolbar)
        self.vbox.addWidget(self.canvas)
        self.setLayout(self.vbox)

    def ylim(self): self.axes.y
    def clear(self): self.axes.clear()
    def plot(self, *args, **kwargs): return self.axes.plot(*args, **kwargs)
    def annotate(self, *args, **kwargs): return self.axes.annotate(*args, **kwargs)
    def set_xlabel(self, *args, **kwargs): return self.axes.set_xlabel(*args, **kwargs)
    def set_ylabel(self, *args, **kwargs): return self.axes.set_ylabel(*args, **kwargs)
    def mpl_connect(self, *args, **kwargs): return self.canvas.mpl_connect(*args, **kwargs)
    def draw(self, *args, **kwargs): return self.canvas.draw(*args, **kwargs)
    def legend(self, *args, **kwargs): return self.axes.legend(*args, **kwargs)
    def set_title(self, *args, **kwargs): return self.axes.set_title(*args, **kwargs)
