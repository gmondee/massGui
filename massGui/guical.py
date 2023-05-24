# earlier demo, only for reference
# 
# #!/usr/bin/python
# -*- coding: utf-8 -*-
import sys, traceback
import matplotlib
matplotlib.use("Qt5Agg")
import PyQt5
from PyQt5 import QtCore
from PyQt5.QtWidgets import QDialog, QLabel,QApplication, QMainWindow, QMenu, QVBoxLayout, QHBoxLayout, QSizePolicy, QMessageBox, QWidget, QComboBox, QTextEdit, QLineEdit, QPushButton
from PyQt5.QtGui import QFont, QIcon
from numpy import arange, sin, pi
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from mass.core.files import LJHFile
import h5py
import numpy as np
from PyMca5.PyMcaMath.fitting import SpecfitFunctions
from PyMca5.PyMcaMath.fitting.Specfit import Specfit
from PyMca5.PyMcaGui.physics.xrf.PeakTableWidget import PeakTableWidget
from PyMca5.PyMcaGui.physics.xrf.McaCalWidget import InputLine
import mass

DEBUG=1

class MplCanvas(QWidget):
    def __init__(self, parent = None, width=6, height=5, dpi=100):
        QWidget.__init__(self, parent)
        fig = Figure(figsize=(width,height), dpi=dpi)
        self.canvas = FigureCanvas(fig)
        self.axes = fig.add_subplot(111)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.updateGeometry()
        self.mpl_toolbar = NavigationToolbar(self.canvas, self)
        self.vbox = QVBoxLayout()
        self.vbox.addWidget(self.mpl_toolbar)
        self.vbox.addWidget(self.canvas)
        self.setLayout(self.vbox)

    def ylim(self): self.axes.y
    def clear(self): self.axes.clear()
    def plot(self, *args, **kwargs): return self.axes.plot(*args, **kwargs)
    def annotate(self, *args, **kwargs): return self.axes.annotate(*args, **kwargs)
    def set_xlabel(self, *args, **kwargs): return self.axes.set_xlabel(*args, **kwargs)
    def set_ylabel(self, *args, **kwargs): return self.axes.set_ylabel(*args, **kwargs)
    def hold(self, *args, **kwargs): return self.axes.hold(*args, **kwargs)
    def mpl_connect(self, *args, **kwargs): return self.canvas.mpl_connect(*args, **kwargs)
    def draw(self, *args, **kwargs): return self.canvas.draw(*args, **kwargs)




class CalWidget(QDialog):

    def __init__(self, parent, bc, counts):
        QDialog.__init__(self, parent)
        self.bc = bc
        self.counts = counts
        self.markers = []
        self.annotations = []


        self.build()
        self.connections()


    def build(self):
        # self.setGeometry(800, 800, 600, 600)
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)
        # self.setWindowTitle('Icon')
        # self.setWindowIcon(QIcon('web.png'))
        self.plot = MplCanvas(self)
        self.vbox.addWidget(self.plot)
        self.findPeaksGUI = FindPeaksGUI(self)
        self.vbox.addWidget(self.findPeaksGUI)
        hbox = QHBoxLayout()
        self.calLinesEdit = QLineEdit()
        self.calLinesButton = QPushButton("assign peaks", self)
        hbox.addWidget(self.calLinesEdit)
        hbox.addWidget(self.calLinesButton)
        self.vbox.addLayout(hbox)
        self.peakTable = PeakTableWidget(self)
        self.vbox.addWidget(self.peakTable)

        # calibration
        hbox = QHBoxLayout()
        self.plotCalButton = QPushButton("plot calibration",self)
        hbox.addWidget(self.plotCalButton)
        self.vbox.addLayout(hbox)

        self.replot()

    def connections(self):
        self.findPeaksGUI.findPeaksButton.clicked.connect(self._findPeaks)
        self.plot.mpl_connect("pick_event",self.onMarkerPick)
        self.plotCalButton.clicked.connect(self._plotCal)


    def replot(self):
        self.plot.clear()
        self.plot.plot(self.bc, self.counts)
        self.plot.set_xlabel("p_filt_value_dc")
        bin_spacing = self.bc[1]-self.bc[0]
        self.plot.set_ylabel("counts per %0.2f unit bin"%bin_spacing)

    def _findPeaks(self):
        peakxs = self.findPeaksGUI.findPeaks(self.bc, self.counts)
        print(peakxs)
        self.clearMarkers()
        self.addMarkers(peakxs)

    def addMarkers(self, xs):
        for x in xs:
            self.addMarker(x)
        self.plot.draw()

    def addMarker(self,x):
        y = np.interp(x,self.bc, self.counts)
        marker, = self.plot.plot(x,y,"or",picker=5)
        self.markers.append(marker)

    def onMarkerPick(self, event):
        markerlabel = event.artist.get_label() # like "_line10"
        xdata,ydata=event.artist.get_data()[0][0], event.artist.get_data()[1][0]
        i = int(markerlabel[5:])
        name = "marker %g"%i
        if DEBUG:
            print("event i %g"%i)
            inputline = InputLine(self, peakpars={'name':name,
            'number':i,
            'channel':xdata,
            'use':1}) # calenergy can be passed

        ret = inputline.exec_()
        if ret == QDialog.Accepted:
            ddict=inputline.getDict()
            if DEBUG:
                print("dict got from dialog = ",ddict)
            if ddict != {}:
                if name in self.peakTable.peaks.keys():
                    self.peakTable.configure(*ddict)
                else:
                    nlines=self.peakTable.rowCount()
                    ddict['name'] = name
                    self.peakTable.newpeakline(name, nlines+1)
                    self.peakTable.configure(**ddict)
                    self.annotateMarker(event.artist, ddict)
                peakdict = self.peakTable.getDict()
                usedpeaks = []
                for peak in peakdict.keys():
                    if peakdict[peak]['use'] == 1:
                        usedpeaks.append([peakdict[peak]['channel'],
                                      peakdict[peak]['setenergy']])
                if len(usedpeaks)>0:
                    if DEBUG: print("have %g peaks in table"%len(usedpeaks))
        else:
            if DEBUG:
                print("InputLine Dialog cancelled or closed ")
        print("onMarkerPick",event)

    def clearMarkers(self):
        for marker in self.markers:
            marker.remove()
        for annotations in self.annotations:
            annotations.remove()
        self.markers=[]
        self.annotations=[]
        self.peakTable.clearPeaks()
        print("clearMarkers: done", self.markers)

    def annotateMarker(self, artist, ddict):
        print(ddict)
        artist.set_color("k")
        xdata,ydata=artist.get_data()[0][0], artist.get_data()[1][0]
        element = ddict["element"].split()[0]
        line = ddict["elementline"].split()[0]
        name = element+" "+line
        annotation = self.plot.annotate(element+" "+line,(xdata,ydata),xytext=(0, 5), textcoords='offset points',ha="center")
        self.annotations.append(annotation)
        self.plot.draw()

    def _plotCal(self):
        cal = mass.EnergyCalibration()
        peakdict = self.peakTable.getDict()
        print(peakdict)
        for k,v in peakdict.items():
            if v["use"]==1:
                element = v["element"].split()[0]
                line = v["elementline"].split()[0]
                name = element+" "+line
                cal.add_cal_point(v["channel"],v["setenergy"],name)
        calplot = CalPlot(self, cal)
        calplot.exec_()



class CalPlot(QDialog):
    def __init__(self, parent, cal):
        QDialog.__init__(self, parent)
        self.cal = cal
        self.build()

    def build(self):
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)
        # self.setWindowTitle('Icon')
        # self.setWindowIcon(QIcon('web.png'))
        self.plot = MplCanvas(self)
        self.vbox.addWidget(self.plot)
        self.plotdrops = MplCanvas(self)
        self.vbox.addWidget(self.plotdrops)

        self.cal.plot(self.plot.axes)
        self.plot.draw()
        #
        # self.plot.xlabel("energy (eV)")
        # self.plot.ylabel("pulse height (arb)")




class FindPeaksGUI(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.build()
        self.connections()

    def build(self):
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)
        self.findPeaksButton = QPushButton("find peaks",self)
        self.findPeaksParam1Edit = QLineEdit("8",self)
        self.findPeaksParam2Edit = QLineEdit("2.5",self)
        hbox = QHBoxLayout()
        self.vbox.addWidget(self.findPeaksButton)
        hbox.addWidget(self.findPeaksParam1Edit)
        hbox.addWidget(QLabel("find peaks fwhm"))
        hbox.addWidget(self.findPeaksParam2Edit)
        hbox.addWidget(QLabel("sensitivity"))
        self.vbox.addLayout(hbox)

    def connections(self):
        pass

    def findPeaks(self, x, y):
        try:
            fwhm = int(self.findPeaksParam1Edit.text())
        except:
            print("findPeaks: failed to convert fwhm to int")
            return []
        try:
            sensitivity = float(self.findPeaksParam2Edit.text())
        except:
            print("findPeaks: failed to converm sensitivity to a float")
            return []
        try:
            a=SpecfitFunctions.SpecfitFunctions()
            peakxs = a.seek(y,x, fwhm=fwhm, sensitivity=sensitivity)
        except:
            print("findPeaks: seek failed")
            return []

        return peakxs


if __name__ == '__main__':
    dpath = "test/young_histograms_ph_and_energy_with_bins.hdf5"
    h5 = h5py.File(dpath,"r")
    for key in h5.keys():
        ref_channel = key
        break
    fv = "p_filt_value_dc"
    y = h5[ref_channel][fv][:]
    def midpoints(bin_edges):
        return 0.5*(bin_edges[1:]+bin_edges[:-1])
    be = np.linspace(0,len(y),len(y)+1)
    bc = midpoints(be)

    app = QApplication(sys.argv)
    main = CalWidget(None, bc, y)
    main.show()
    sys.exit(app.exec_())
