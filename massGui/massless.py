# -*- coding: utf-8 -*-
#std lib imports
import sys
import os
import logging  
log = logging.getLogger("massless")
#qt imports
import PyQt5.uic
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QSettings, pyqtSlot
from PyQt5.QtWidgets import QFileDialog

# other imports
import numpy as np
import pylab as plt
from .canvas import MplCanvas
import mass

import massGui

MPL_DEFAULT_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
              '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
              '#bcbd22', '#17becf']

DEFAULT_LINES = list(mass.spectra.keys())

class HistCalibrator(QtWidgets.QDialog):
    def __init__(self, parent=None,s=None, attr=None, state_labels=None, colors=MPL_DEFAULT_COLORS[:6], lines=DEFAULT_LINES):
        super(HistCalibrator, self).__init__(parent)
        #self.setWindowModality(QtCore.Qt.ApplicationModal)
        QtWidgets.QDialog.__init__(self)
        self.lines = self.TOptionsDict=list(mass.spectra.keys())

    def setParams(self, data, channum, attr, state_labels, colors=MPL_DEFAULT_COLORS[:6], lines=DEFAULT_LINES):
        self.build(data, channum, attr, state_labels, colors)
        self.connect()

    def build(self, data, channum, attr, state_labels, colors):
        PyQt5.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/ChannelBrowser.ui"), self) #,  s, attr, state_labels, colors)
        #self.histHistViewer = HistViewer(self, s, attr, state_labels, colors) #histHistViewer is the name of the widget that plots.
        self.data = data
        self.channum = channum
        for channel in self.data.keys():
            self.channelBox.addItem("{}".format(channel))
        self.histHistViewer.setParams(self, data, channum, attr, state_labels, colors)


    def connect(self):
        self.histHistViewer.plotted.connect(self.handle_plotted)
        self.histHistViewer.markered.connect(self.handle_markered)
        self.channelBox.currentTextChanged.connect(self.updateChild)
        self.closeButton.clicked.connect(self.close)

    def clear_table(self):
        # for i in range(self.table.columnCount()):
        #     for j in range(self.table.rowCount()):
        #         self.table.setHorizontalHeaderItem(j, QtWidgets.QTableWidgetItem())
        self.table.setRowCount(0)

    def handle_plotted(self):
        # log.debug("handle_plotted")
        self.clear_table()

    def handle_markered(self, x, states):
        n = self.table.rowCount()
        self.table.setRowCount(n+1)
        # log.debug(f"handle_markered, x {x}, states {states}, n {n}")   
        self.table.setItem(n, 0, QtWidgets.QTableWidgetItem(",".join(states)))
        self.table.setItem(n, 1, QtWidgets.QTableWidgetItem("{}".format(x)))
        self.table.setItem(n, 3, QtWidgets.QTableWidgetItem(""))
        cbox = QtWidgets.QComboBox()
        cbox.addItem("")
        cbox.addItems(self.lines) 
        self.table.setCellWidget(n, 2, cbox)
        self.table.resizeColumnsToContents()
        # log.debug(f"{self.getTableRows()}")

    def getTableRows(self):
        rows = []
        for i in range(self.table.rowCount()):
            row = []
            row.append(self.table.item(i, 0).text())
            row.append(self.table.item(i, 1).text())
            row.append(self.table.cellWidget(i, 2).currentText()) # this is a combobos
            row.append(self.table.item(i, 3).text())
            rows.append(row)
        return rows
    
    def getChannum(self):
        self.channum = self.channelBox.currentText()
        return self.channum
    def updateChild(self):
        self.histHistViewer.channum = self.getChannum()








class HistViewer(QtWidgets.QWidget): #widget. plots clickable hist.
    min_marker_ind_diff = 12
    plotted = QtCore.pyqtSignal()
    markered = QtCore.pyqtSignal(float, list)
    def __init__(self, parent, s=None, attr=None, state_labels=None, colors=None):
        QtWidgets.QWidget.__init__(self, parent)#, s, attr, state_labels, colors)
        #super(HistViewer, self).__init__(parent)
        super(HistViewer, self).__init__(parent)
 
        # PyQt5.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/channel.ui"), self) 

    def setParams(self, parent, data, channum, attr, state_labels, colors, clickable=True):
        # QtWidgets.QWidget.__init__(self, parent)#, s, attr, state_labels, colors)
        #super(HistViewer, self).__init__(parent)
        self.parent = parent
        self.plotAllChans = False #used to switch between self.plot and self.plotAll
        self.binLo = 0
        self.binHi = 20000
        self.binSize = 10
        self.channum = channum
        self.lastUsedChannel = channum
        self.data=data
        self.s = data[channum]
        self.attr = attr
        self.build(state_labels, colors) 
        self.connect()
        self.statesGrid.fill_simple()
        self.handle_plot()
        self.clickable = clickable
        
    def build(self, state_labels, colors):
        layout = QtWidgets.QVBoxLayout()
        self.canvas = MplCanvas()
        self.statesGrid = StatesGrid(self)
        self.statesGrid.setParams(state_labels, colors)
        self.plotButton = QtWidgets.QPushButton("Plot/Reset", self)
        layout.addWidget(self.canvas)
        layout.addWidget(self.plotButton)
        layout.addWidget(self.statesGrid)
        self.setLayout(layout)

    def connect(self):
        self.plotButton.clicked.connect(self.handle_plot)
 
    def handle_plot(self): #needs to use channel
        #self.channum = self.parent().getChannum()  #can't use parent properly b/c initialised with .ui file. Use an update signal instead.
        colors, states_list = self.statesGrid.get_colors_and_states_list() 
        # log.debug(f"handle_plot: color: {colors}")
        # log.debug(f"handle_plot: states_list: {states_list}")
        if len(colors) == 0:
            #raise Exception("no states clicked: {}  {}".format(colors, states_list))
            pass
        else:
            if self.plotAllChans == False:
                self.plot(states_list, np.arange(self.binLo,self.binHi, self.binSize), self.attr, colors)
            else:
                self.plotAll(states_list, np.arange(self.binLo,self.binHi, self.binSize), self.attr, colors)


    def plot(self, states_list, bin_edges, attr, colors):
        #print(self.data[int(self.channum)].channum)
        self.lastUsedChannel = self.data[int(self.channum)].channum
        self.canvas.clear()
        self.line2marker = {}
        self.line2states = {}
        self.photonCount = 0
        for states, color in zip(states_list, colors):
            x,y = self.data[int(self.channum)].hist(bin_edges, attr, states=states)
            self.photonCount+=sum(y)
            [line2d] = self.canvas.plot(x,y, c=color, ds='steps-mid', lw=2, picker=4) 
            # # log.debug(f"plot: loop: states={states} color={color}")
            self.line2marker[line2d] = []
            self.line2states[line2d] = states
        self.canvas.legend([",".join(states) for states in states_list])
        self.canvas.set_xlabel(attr)
        self.canvas.set_ylabel("counts per bin")
        # plt.tight_layout()
        self.parent.photonCountBox.setText(str(self.photonCount))
        self.canvas.draw()
        self.canvas.mpl_connect('pick_event', self.mpl_click_event)
        self.plotted.emit()

    def plotAll(self, states_list, bin_edges, attr, colors):
        print("plotting all channels")
        self.canvas.clear()
        self.line2marker = {}
        self.line2states = {}
        for states, color in zip(states_list, colors):
            x,y = self.data.hist(bin_edges, attr, states=states)
            [line2d] = self.canvas.plot(x,y, c=color, ds='steps-mid', lw=2, picker=4) 
            # # log.debug(f"plot: loop: states={states} color={color}")
            self.line2marker[line2d] = []
            self.line2states[line2d] = states
        self.canvas.legend([",".join(states) for states in states_list])
        self.canvas.set_xlabel(attr)
        self.canvas.set_ylabel("counts per bin")
        # plt.tight_layout()
        self.canvas.draw()
        self.canvas.mpl_connect('pick_event', self.mpl_click_event)
        self.plotted.emit()


    def mpl_click_event(self, event):
        if self.clickable == True:
            x = event.mouseevent.xdata
            y = event.mouseevent.ydata
            artist = event.artist
            # log.info(artist.get_label()+f" was clicked at {x:.2f},{y:.2f}")
            if artist in self.line2marker.keys():
                xs, ys = artist.get_data()
                i = self.local_max_ind(xs, ys, x, y) 
                if ys[i] > y*0.8:
                    self.add_marker(artist, i)
                else:
                    # log.debug(f"marker not placed becausel local maximum {ys[i]}<=0.8*mouse_click_height {y}.\nclick closer to the peak")
                    pass
            else: 
                # log.debug(f"arist not in line2marker.keys() {line2marker.keys()}")
                pass
        else:
            pass


    def add_marker(self, artist, i):
        artist_markers = self.line2marker[artist]
        c = plt.matplotlib.artist.getp(artist, "markerfacecolor")
        xs, ys = artist.get_data()

        for (i_, marker_) in artist_markers:
            if np.abs(i-i_) < self.min_marker_ind_diff:
                # log.debug(f"not adding marker at {i}, x {xs[i]}, y {ys[i]}. too close to marker at {i_} for artist {artist} and color {c}")
                return
        marker = self.canvas.plot(xs[i], ys[i], "o", markersize=12, c=c) # cant be picked unless I pass picker?
        artist_markers.append((i, marker))
        self.line2marker[artist] = artist_markers
        self.markered.emit(xs[i], self.line2states[artist])
        self.canvas.draw() 
        # log.debug(f"add marker at {i}, x {xs[i]}, y {ys[i]}")
        # # log.debug(f"self.line2marker {self.line2marker}")


    def local_max_ind(self, xs, ys, x, y):
        i0 = np.searchsorted(xs, x)
        # # log.debug(f"local_max_ind: x {x} y {y} len(xs) {len(xs)} len(ys) {len(ys)} i0 {i0}\n{ys[i0-5:i0+5]}")
        if i0 == 0:
            im = 1
        elif i0 == len(ys)-1:
            im = -1
        elif ys[i0-1]>ys[i0]:
            im = -1
        elif ys[i0+1]>ys[i0]:
            im = 1
        else: # i0 is local max

            return i0

        i=i0
        while True:
            i = i + im
            if i == 0 or i == len(ys)-1:
                break
            elif ys[i+im] < ys[i]: 
                break

        return i
    

        

            



class StatesGrid(QtWidgets.QWidget):
    def __init__(self, parent=None, state_labels=None, colors=None, one_state_per_line=True):
        QtWidgets.QWidget.__init__(self, parent)
        self.one_state_per_line = one_state_per_line

    def setParams(self, state_labels=None, colors=None, one_state_per_line=True):
        self.build(state_labels, colors)
        self.connect()

    def build(self, state_labels, colors):
        self.state_labels = state_labels
        self.colors = colors 
        self.grid = QtWidgets.QGridLayout()
        self.boxes = []
        for (i, state) in enumerate(self.state_labels):
            boxes = []
            for (j, color) in enumerate(colors):
                if j== 0:
                    self.grid.addWidget(QtWidgets.QLabel(state), 0, i+1)
                if i==0:
                    label = QtWidgets.QLabel("|") 
                    label.setStyleSheet("color:{}".format(color))                
                    self.grid.addWidget(label, j+1, 0)
                box = QtWidgets.QCheckBox()
                # bpalette = box.palette()
                # bpalette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(color))
                # label.setPalette(bpalette) 
                box.setStyleSheet("background-color: {}".format(color))
                self.grid.addWidget(box, j+1, i+1)
                boxes.append(box)
            self.boxes.append(boxes)
        self.setLayout(self.grid) 
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Fixed))
    
    def connect(self):
        for (j, color) in enumerate(self.colors):
            for (i, state) in enumerate(self.state_labels):
                box = self.boxes[i][j]    
                box.stateChanged.connect(lambda state, i=i, j=j: self.handle_state_change(state, i, j))     
    
    def fill_simple(self):
        for (j, color) in enumerate(self.colors):
            for (i, state) in enumerate(self.state_labels):
                box = self.boxes[i][j] 
                box.setChecked(i==j)    

    def handle_state_change(self, state, i, j_):
        if state == 2 and self.one_state_per_line: # checked
            for (j, color) in enumerate(self.colors):
                if j != j_:
                    box = self.boxes[i][j]    
                    box.setChecked(False)

    def get_colors_and_states_list(self):
        colors = []
        states_list = []
        for (j, color) in enumerate(self.colors):
            states = []
            for (i, state) in enumerate(self.state_labels):
                box = self.boxes[i][j] 
                if box.isChecked(): 
                    states.append(state)
            if len(states) >0:
                colors.append(color)
                states_list.append(states)
        return colors, states_list
    



class HistPlotter(QtWidgets.QDialog):
    def __init__(self, parent=None, colors=MPL_DEFAULT_COLORS[:6]):
        super(HistPlotter, self).__init__(parent)
        #self.setWindowModality(QtCore.Qt.ApplicationModal)
        QtWidgets.QDialog.__init__(self)

    def setParams(self, data, channum, attr, state_labels, colors=MPL_DEFAULT_COLORS[:6], lines=DEFAULT_LINES):
        self.build(data, channum, attr, state_labels, colors)
        self.connect()

    def build(self, data, channum, attr, state_labels, colors):
        PyQt5.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/histPlotter.ui"), self) #,  s, attr, state_labels, colors)
        #self.pHistViewer = HistViewer(self, s, attr, state_labels, colors) #pHistViewer is the name of the widget that plots.
        self.data = data
        self.channum = channum
        for channum in self.data.keys():
            self.channelBox.addItem("{}".format(channum))
        self.channelBox.setCurrentText(str(self.channum))
        self.eRangeLow.insert(str(0))
        self.eRangeHi.insert(str(20000))
        self.pHistViewer.setParams(self, data, int(self.channum), attr, state_labels, colors, clickable=False)


    def connect(self):
        self.channelBox.currentTextChanged.connect(self.updateChild)
        self.histChannelCheckbox.stateChanged.connect(self.updateChild)
        self.eRangeLow.textChanged.connect(self.updateChild)
        self.eRangeHi.textChanged.connect(self.updateChild)
        # self.histHistViewer.plotted.connect(self.handle_plotted)
        # self.histHistViewer.markered.connect(self.handle_markered)
        # self.channelBox.currentTextChanged.connect(self.updateChild)



    def getChannum(self):
        self.channum = self.channelBox.currentText()
        return self.channum
    
    def updateChild(self):
        # if arg == 'chan':
        #     self.pHistViewer.channum=self.getChannum()
        # if arg == 'checkbox':
        #     self.pHistViewer.plotAllChans = (not self.pHistViewer.plotAllChans)
        self.pHistViewer.channum=self.getChannum()
        self.pHistViewer.plotAllChans = self.histChannelCheckbox.isChecked()
        #crashes if the range boxes are empty. Use default values instead to avoid crash.
        if self.eRangeLow.displayText() != '':
            self.pHistViewer.binLo = int(self.eRangeLow.displayText())
        else:
            self.pHistViewer.binLo = 0

        if self.eRangeHi.displayText() != '':
            self.pHistViewer.binHi = int(self.eRangeHi.displayText())
        else:
            self.pHistViewer.binHi = 20000
        ##energy range updating