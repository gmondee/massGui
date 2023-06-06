# -*- coding: utf-8 -*-
#std lib imports
import sys
import os
import logging  

#qt imports
import PyQt6.uic
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import QSettings, QTimer, pyqtSlot
from PyQt6.QtWidgets import QFileDialog
QtGui.QCursor
# other imports
import numpy as np
import pylab as plt
from .canvas import MplCanvas
import mass
from matplotlib.lines import Line2D
import massGui

logging.basicConfig(filename='masslessLog.txt',
                    filemode='w',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)

logging.info("Massless Log")
log = logging.getLogger("massless")

MPL_DEFAULT_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
              '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
              '#bcbd22', '#17becf']

DEFAULT_LINES = list(mass.spectra.keys())

class HistCalibrator(QtWidgets.QDialog):
    def __init__(self, parent=None,s=None, attr=None, state_labels=None, colors=MPL_DEFAULT_COLORS[:6], lines=DEFAULT_LINES):
        super(HistCalibrator, self).__init__(parent)
        #self.setWindowModality(QtCore.Qt.ApplicationModal)
        QtWidgets.QDialog.__init__(self)
        self.lines = list(mass.spectra.keys())

    def setParams(self, data, channum, attr, state_labels, colors=MPL_DEFAULT_COLORS[:6], lines=DEFAULT_LINES):
        self.build(data, channum, attr, state_labels, colors)
        self.connect()

    def build(self, data, channum, attr, state_labels, colors):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/ChannelBrowser.ui"), self) #,  s, attr, state_labels, colors)
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
        log.debug("handle_plotted")
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
            row.append(self.table.cellWidget(i, 2).currentText()) # this is a combobox
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
 
        # PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/channel.ui"), self) 

    def setParams(self, parent, data, channum, attr, state_labels, colors, clickable=True):
        # QtWidgets.QWidget.__init__(self, parent)#, s, attr, state_labels, colors)
        #super(HistViewer, self).__init__(parent)
        log.debug(f"set params for histviewer")
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
            # pos = QtGui.QCursor.pos()
            # print(self.mapFromGlobal(pos))
            artist = event.artist
            log.info(artist.get_label()+f" was clicked at {x:.2f},{y:.2f}")
            if artist in self.line2marker.keys():
                xs, ys = artist.get_data()
                i = self.local_max_ind(xs, ys, x, y) 
                if ys[i] > y*0.8:
                    self.add_marker(artist, i)
                else:
                    log.debug(f"marker not placed becausel local maximum {ys[i]}<=0.8*mouse_click_height {y}.\nclick closer to the peak")
                    pass
            else: 
                #log.debug(f"arist not in line2marker.keys() {line2marker.keys()}")
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
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed,QtWidgets.QSizePolicy.Policy.Fixed))
    
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
    
    def fill_all(self): #intended for cases where you only have one row of states
        for (j, color) in enumerate(self.colors):
            for (i, state) in enumerate(self.state_labels):
                box = self.boxes[i][j] 
                box.setChecked(True) 
    



class HistPlotter(QtWidgets.QDialog):
    def __init__(self, parent=None, colors=MPL_DEFAULT_COLORS[:6]):
        super(HistPlotter, self).__init__(parent)
        #self.setWindowModality(QtCore.Qt.ApplicationModal)
        QtWidgets.QDialog.__init__(self)

    def setParams(self, data, channum, attr, state_labels, colors=MPL_DEFAULT_COLORS[:6], lines=DEFAULT_LINES):
        self.build(data, channum, attr, state_labels, colors)
        self.connect()

    def build(self, data, channum, attr, state_labels, colors):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/histPlotter.ui"), self) #,  s, attr, state_labels, colors)
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


class diagnoseViewer(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(diagnoseViewer, self).__init__(parent)
        QtWidgets.QDialog.__init__(self)

    def setParams(self, data, channum, colors=MPL_DEFAULT_COLORS[:6]):
        self.colors = colors
        self.build(data, channum)
        self.connect()

    def build(self, data, channum):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/diagnosePlotWindow.ui"), self) #,  s, attr, state_labels, colors)
        #self.pHistViewer = HistViewer(self, s, attr, state_labels, colors) #pHistViewer is the name of the widget that plots.
        self.data = data
        self.channum = channum
        for channum in self.data.keys():
            self.channelBox.addItem("{}".format(channum))
        self.channelBox.setCurrentText(str(self.channum))
        self.plotDiagnosis()
        # self.eRangeLow.insert(str(0))
        # self.eRangeHi.insert(str(20000))
        #self.canvas.setParams(self, data, int(self.channum), state_labels, colors, clickable=False)


    def connect(self):
        #self.channelBox.currentTextChanged.connect(self.updateChild)
        self.diagPlotButton.clicked.connect(self.plotDiagnosis)

    def plotDiagnosis(self):
        #self.clear()
        self.diagnoseCalibration()
        self.canvas.draw()

    def getChannum(self):
        self.channum = int(self.channelBox.currentText())
        return self.channum

    def diagnoseCalibration(self, calibratedName="energy"):
        ds = self.data[self.getChannum()]
        calibration = ds.recipes[calibratedName].f
        uncalibratedName = calibration.uncalibratedName
        results = calibration.results
        n_intermediate = len(calibration.intermediate_calibrations)
        self.canvas.fig.clear()
        self.canvas.fig.suptitle(
            ds.shortName+", cal diagnose for '{}'\n with {} intermediate calibrations".format(calibratedName, n_intermediate))
        n = int(np.ceil(np.sqrt(len(results)+2)))
        for i, result in enumerate(results):
            ax = self.canvas.fig.add_subplot(n, n, i+1)
            ax.cla()
            # pass title to suppress showing the dataset shortName on each subplot
            result.plotm(ax=ax, title=str(result.model.spect.shortname))
        ax = self.canvas.fig.add_subplot(n, n, i+2)
        calibration.plot(axis=ax)
        ax = self.canvas.fig.add_subplot(n, n, i+3)
        ds.plotHist(np.arange(0, 16000, 4), uncalibratedName,
                      axis=ax, coAddStates=False)
        #ax.vlines(ds.calibrationPlan.uncalibratedVals, 0, self.canvas.fig.ylim()[1])
        #plt.tight_layout()




class rtpViewer(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(rtpViewer, self).__init__(parent)
        QtWidgets.QDialog.__init__(self)
        plt.ion()
    def setParams(self, parent):
        self.colors =MPL_DEFAULT_COLORS[1]
        
        self.parent = parent
        self.stateLabels = self.parent.ds.stateLabels
        self.dataToPlot = self.parent.data
        self.build()
        self.connect()


    def build(self):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/realtimeviewer.ui"), self)
        self.RTPdelay = self.intervalBox.text() 
        self.statesGrid.setParams(state_labels=self.stateLabels, colors=MPL_DEFAULT_COLORS[:1], one_state_per_line=False)
        self.statesGrid.fill_simple()
        for channum in self.parent.data.keys():
            self.channelBox.addItem("{}".format(channum))
        self.channelBox.setCurrentIndex(0)
        self.initRTP()

    def connect(self):
        self.updateButton.clicked.connect(self.updateButtonClicked)

    def updateButtonClicked(self):
        self.timer.stop()
        self.UpdatePlots()
        #assert 1 == 0

    #####################################| Real-time plotting routine|#####################################
    def initRTP(self): #creates axes, clears variables, and starts real-time plotting routine

        self.updateIndex=0                  #tracks how many updates have happened
        self.alphas=[]                      #transparencies of lines
        self.rtpline=[]                     #list of all plotted lines
        self.plottedStates=[]               #used for the RTP legend
        
        #self.energyPlot=plt.figure()        #everything is plotted onto this figure
        self.canvas.fig.clear()
        self.energyAxis = self.canvas.fig.add_subplot(111)
        self.energyAxis.grid()
        
        self.energyAxis.set_title('Real-time energy')
        self.energyAxis.set_xlabel('Energy (eV)')
        self.energyAxis.set_ylabel('Counts per'+str(self.parent.binSize)+'eV bin')
        self.rate = 0.1                     #how much to lower the transparency of lines each update
        
        self.timer = QTimer(self)    
        #self.timer.setSingleShot(True)    
        self.timer.timeout.connect(self.UpdatePlots)        
        #self.timer.start(self.updateFreq)
        self.UpdatePlots()

    def stopRTP(self):
        try:
            self.timer.stop()
        finally:
            pass

    def getDataToPlot(self):
        old = self.dataToPlot
        if self.rtpChannelCheckbox.isChecked():
            new = self.parent.data
        else:
            new = self.parent.data[int(self.channelBox.currentText())]
        if old != new: #if channel is changed, or if user goes from all channels to one channel, we need to clear the plot.
            print(new, old)
            print("Restarting RTP because channel selection has changed.")
            self.restartRTP()
            return new
        else:
            return new

    def restartRTP(self):   #this function resets necessary parameters to start monitoring another data set

        self.updateIndex=0                  #tracks how many updates have happened
        self.alphas=[]                      #transparencies of lines
        self.rtpline=[]                     #list of all plotted lines
        self.plottedStates=[]               #used for the RTP legend
        
        #self.energyPlot=plt.figure()        #everything is plotted onto this figure
        self.canvas.fig.clear()
        self.energyAxis = self.canvas.fig.add_subplot(111)
        self.energyAxis.grid()
        
        self.energyAxis.set_title('Real-time energy')
        self.energyAxis.set_xlabel('Energy (eV)')
        self.energyAxis.set_ylabel('Counts per'+str(self.parent.binSize)+'eV bin')
        self.rtpdata=[]                             #temporary storage of data points
        self.rtpline.append([])                     #stores every line that is plotted according to the updateIndex



    def UpdatePlots(self):  #real-time plotting routine. refreshes data, adjust alphas, and replots graphs
        print(f"iteration {self.updateIndex}")
        
        self.RTPdelay = self.intervalBox.text() 
        self.updateFreq = int(self.RTPdelay)*1000             #in ms after the multiplication
        self.timer.start(self.updateFreq)

        self.parent.data.refreshFromFiles()                #Mass function to refresh .off files as they are updated
        _colors, States = self.statesGrid.get_colors_and_states_list()
        try: #if the user has all states unchecked during a refresh, use the last set of states.
            States = States[0]
            self.oldStates = States
        except:
            States = self.oldStates

        
        self.rtpdata=[]                             #temporary storage of data points
        self.rtpline.append([])                     #stores every line that is plotted according to the updateIndex
        self.dataToPlot = self.getDataToPlot()
        for s in range(len(States)):    #looping over each state passed in
            #self.rtpdata.append(self.parent.data.hist(np.arange(0, 14000, float(self.parent.binSize)), "energy", states=States[s]))   #[x,y] points of current energy spectrum, one state at a time
            self.rtpdata.append(self.dataToPlot.hist(np.arange(0, 14000, float(self.parent.binSize)), "energy", states=States[s]))
            self.energyAxis.plot(self.rtpdata[s][0],self.rtpdata[s][1],alpha=1, color=self.getColorfromState(States[s]))    #plots the [x,y] points and assigns color based on the state
            if States[s] not in self.plottedStates:     #new states are added to the legend; old ones are already there                      
                self.plottedStates.append(States[s])
            self.rtpline[self.updateIndex].append(self.energyAxis.lines[-1])    #stores most recent line

        self.alphas.append(1)   #lines in the same refresh cycle share an alpha (transparency) value. a new one is made for the newest lines.
        customLegend=[]         #temporary list to store the legend
        for s in self.plottedStates:    #loops over all states called during the current real-time plotting routine
            customLegend.append(Line2D([0], [0], color=self.getColorfromState(s)))      #each state is added to the legend with the state's respective color
        self.energyAxis.legend(customLegend, list(self.plottedStates))                  #makes the legend

        ###change transparency of current elements, plot adjusted lines
        for lineI in range(len(self.alphas)):   #loops over the number of refresh cycles, which is also the length of the alphas list
            if self.alphas[lineI] > 0.1:        #alpha values cannot be below 0
                self.alphas[lineI] = self.alphas[lineI] - self.rate
            for setI in range(len(self.rtpline[lineI])):    #loops over the states within one refresh cycle
                self.rtpline[lineI][setI].set_alpha(self.alphas[lineI])     #sets adjusted alpha values
        self.canvas.draw()
        self.updateIndex=self.updateIndex+1


    def getColorfromState(self, s): #pass in a state label string like 'A' or 'AC' (for states past Z) and get a color index using plt.colormaps() 
        # c = plt.cm.get_cmap('gist_rainbow')     #can be other colormaps, rainbow is most distinct
        # maxColors=8                             #how many unique colors there are. lower values make it easier to distinguish between neighboring states.
        # cinter=np.linspace(0,1,maxColors)       #colormaps use values between 0 and 1. this interpolation lets us assign integers to colors easily.
        # cIndex=0
        # cIndex=cIndex+ord(s[-1])-ord('A')       #uses unicode values of state labels (e.g. 'A') to get an integer 
        # if len(s)!=1:   #for states like AA, AB, etc., 27 is added to the value of the ones place
        #     cIndex=cIndex+26+ord(s[0])-ord('A')+1 #26 + value of first letter (making A=1 so AA != Z)

        # while cIndex >= maxColors:       #colors repeat after maxColors states. loops until there is a valid interpolated index from cinter
        #     cIndex=cIndex-maxColors
        # #print(c(cinter[cIndex]))
        # return c(cinter[cIndex])        #returns values that can be assigned as a plt color, looks like (X,Y,Z,...) or something similar    
        c=MPL_DEFAULT_COLORS
        maxColors = len(c)

        cIndex =  ord(s[-1])-ord('A')
        if len(s)!=1:   #for states like AA, AB, etc., 27 is added to the value of the ones place
            cIndex=cIndex+26+ord(s[0])-ord('A')+1 #26 + value of first letter (making A=1 so AA != Z)
        while cIndex >= maxColors:       #colors repeat after maxColors states. loops until there is a valid interpolated index from cinter
            cIndex=cIndex-maxColors
        #print(s, cIndex)
        return c[cIndex]
    

class AvsBSetup(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(AvsBSetup, self).__init__(parent)
        QtWidgets.QDialog.__init__(self)
        plt.ion()
    def setParams(self, parent, AvsBDict, states_list, channels, data, mode):
        self.colors = MPL_DEFAULT_COLORS[0]
        self.parent = parent
        self.states_list = states_list
        self.AvsBDict = AvsBDict
        self.channels = channels
        self.data = data
        self.mode = mode
        self.build()
        self.connect()


    def build(self):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/avsbSetup.ui"), self) 
        self.statesGrid.setParams(state_labels=self.states_list, colors=MPL_DEFAULT_COLORS[:1], one_state_per_line=False)
        self.statesGrid.fill_all()
        for channum in self.channels:
            self.channelBox.addItem("{}".format(channum))
        self.channelBox.setCurrentIndex(0)

        for A in self.AvsBDict:
            self.Abox.addItem("{}".format(A))
        self.Abox.setCurrentIndex(0)   

        for B in self.AvsBDict:
            self.Bbox.addItem("{}".format(B))
        self.Bbox.setCurrentIndex(0)   

        if self.mode == "1D":
            self.binsFrame.hide()

    def connect(self):
        self.plotButton.clicked.connect(self.handlePlot)

    def handlePlot(self):
        #self.plotter = AvsBViewer(self)
        A = self.Abox.currentText()
        B = self.Bbox.currentText()
        _colors, states = self.statesGrid.get_colors_and_states_list()
        states=states[0]
        # if self.channelCheckbox.isChecked():
        #     channels = self.data
        # else:
        channel = self.data[int(self.channelBox.currentText())]

        if self.mode == "1D":
            channel.plotAvsB(A, B, axis=None, states=states)
        if self.mode == "2D":
            Ahi = max(channel.getAttr(A, states))
            Alo = min(channel.getAttr(A, states))
            
            Bhi = max(channel.getAttr(B, states))
            Blo = min(channel.getAttr(B, states))

            num = int(self.binsBox.text())#500

            bins = [np.linspace(Alo, Ahi, num=num), np.linspace(Blo,Bhi,num=num)]#self.binsBox.text()
            channel.plotAvsB2d(A, B, binEdgesAB = bins, axis=None, states=states)
            #plotAvsB2d(self, nameA, nameB, binEdgesAB, axis=None, states=None, cutRecipeName=None, norm=None)
        # self.plotter.setParams(self, A, B, states, channels, self.data, self.mode)
        # self.plotter.show()

class linefitSetup(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(linefitSetup, self).__init__(parent)
        QtWidgets.QDialog.__init__(self)
        plt.ion()
    def setParams(self, parent, lines, states_list, channels, data):
        self.colors = MPL_DEFAULT_COLORS[0]
        self.parent = parent
        self.states_list = states_list
        self.lines = lines
        self.channels = channels
        self.data = data
        self.build()
        self.connect()


    def build(self):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/linefitSetup.ui"), self) 
        self.statesGrid.setParams(state_labels=self.states_list, colors=MPL_DEFAULT_COLORS[:1], one_state_per_line=False)
        self.statesGrid.fill_simple()
        for channum in self.channels:
            self.channelBox.addItem("{}".format(channum))
        self.channelBox.setCurrentIndex(0)

        for line in self.lines:
            self.lineBox.addItem("{}".format(line))
        self.lineBox.setCurrentIndex(0)     

    def connect(self):
        self.plotButton.clicked.connect(self.handlePlot)

    def handlePlot(self):
        _colors, states = self.statesGrid.get_colors_and_states_list()
        states=states[0]
        line = self.lineBox.currentText()
        has_linear_background = self.lbCheckbox.isChecked()
        has_tails = self.tailCheckbox.isChecked()

        dlo = self.dlo.text()
        if dlo != '': #not empty
            dlo = abs(int(self.dlo.text()))
        else:
            dlo = 15

        dhi = self.dhi.text()
        if dhi != '': #not empty
            dhi = abs(int(self.dhi.text()))
        else:
            dhi = 15

        channel = self.data[int(self.channelBox.currentText())]
        channel.linefit(lineNameOrEnergy=line, attr="energy", states=states, has_linear_background=has_linear_background, has_tails=has_tails, dlo=dlo, dhi=dhi)


# class AvsBViewer(QtWidgets.QDialog):      #not used. avsb is plotted in a popup plt window so you can have many at once.
#     def __init__(self, parent=None):
#         super(AvsBViewer, self).__init__(parent)
#         QtWidgets.QDialog.__init__(self)
#         plt.ion()
#     def setParams(self, parent, A, B, States, channels, data, mode):
#         self.parent = parent
#         self.states = States
#         self.A = A
#         self.B = B
#         self.channels = channels
#         self.data = data
#         self.build(mode)

#     def build(self, mode):
#         PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/avsbViewer.ui"), self) 
#         self.canvas.fig.clear()
#         self.axis = self.canvas.fig.add_subplot(111)
#         self.axis.grid()
#         if mode == "1D":
#             self.axis = self.channels.plotAvsB(self.A, self.B, axis=self.axis, states=self.states)
#         if mode == "2D":
#             pass
#         self.canvas.draw()


