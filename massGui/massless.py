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
import matplotlib.pyplot as plt
from .canvas import MplCanvas
import mass
import matplotlib
from matplotlib.lines import Line2D
import massGui
import h5py
from copy import copy

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

class HistCalibrator(QtWidgets.QDialog):    #plots filtValues on a clickable canvas for manual line ID
    def __init__(self, parent=None):
        super(HistCalibrator, self).__init__(parent)
        #self.setWindowModality(QtCore.Qt.ApplicationModal)
        QtWidgets.QDialog.__init__(self)
        self.lines = list(mass.spectra.keys())

    def setParams(self, parent, data, channum, attr, state_labels, binSize, colors=MPL_DEFAULT_COLORS[:6], lines=DEFAULT_LINES, statesConfig=None, markers=None, artistMarkers=None,markersIndex=None):
        self.parent=parent
        self.binSize=binSize
        if markers==None:
            self.markersDict = {}
        else:
            self.markersDict = markers
        if artistMarkers==None:
            self.artistMarkersDict = {}
        else:
            self.artistMarkersDict = artistMarkers
        if markersIndex==None:
            self.markerIndex = 0
        else:
            self.markerIndex = markersIndex
        self.build(data, channum, attr, state_labels, colors, statesConfig)
        self.connect()

    def build(self, data, channum, attr, state_labels, colors, statesConfig):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/ChannelBrowser.ui"), self) #,  s, attr, state_labels, colors)
        #self.histHistViewer = HistViewer(self, s, attr, state_labels, colors) #histHistViewer is the name of the widget that plots.
        self.data = data
        self.channum = channum
        for channel in self.data.keys():
            self.channelBox.addItem("{}".format(channel))
        self.channelBox.setCurrentText(str(channum))
        self.eRangeLow.insert(str(0))
        self.eRangeHi.insert(str(20000))
        self.binSizeBox.insert(str(50))
        self.histHistViewer.setParams(self, data, channum, attr, state_labels, colors, self.binSize, statesConfig=statesConfig)
        self.importMarkers()


    def connect(self):
        self.histHistViewer.plotted.connect(self.handle_plotted)
        self.histHistViewer.markered.connect(self.handle_markered)
        self.channelBox.currentTextChanged.connect(self.updateChild)
        self.eRangeLow.textChanged.connect(self.updateChild)
        self.eRangeHi.textChanged.connect(self.updateChild)
        self.binSizeBox.textChanged.connect(self.updateChild)

        self.diagCalButton.clicked.connect(self.diagnoseCalibration)
        #self.closeButton.clicked.connect(self.close) #removed
        #self.table.itemChanged.connect(self.updateTable)

    def importMarkers(self):
        for marker in self.markersDict:
            artist = self.markersDict[marker]
            new_ax = self.histHistViewer.canvas.axes
            #self.markersDict[marker].plot()
            artist.remove()
            artist.axes = new_ax
            artist.set_transform(new_ax.transData)  # <-- I added this line
            #new_ax.add_line(artist)
            new_ax.add_artist(artist)

            
            # am = self.artistMarkersDict[i] 
            # #self.markersDict[str(i)]=am[2]
            # self.histHistViewer.add_marker(am[3], am[1], emit=False) 

    def updateTable(self, line): #bad way to do this, but it works. see deleteRow for a better way using slots.
        for r in range(self.table.rowCount()):  #searches for comboboxes with the clicked line and updates the first one's energy. 
            for c in range(self.table.columnCount()):
                widget = self.table.cellWidget(r, c)
                if isinstance(widget, QtWidgets.QComboBox):
                    if widget.currentText() == line and line in mass.spectra.keys():
                        self.table.setItem(r, c+1, QtWidgets.QTableWidgetItem(str(mass.spectra[line].nominal_peak_energy)))
                        self.table.item(r, c+1).setFlags(self.table.item(r, c+1).flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                        #item.setEnabled(False)
                    elif widget.currentText() == "Manual Energy":
                        self.table.setItem(r, c+1, QtWidgets.QTableWidgetItem(""))
                        self.table.item(r, c+1).setFlags(self.table.item(r, c+1).flags() | QtCore.Qt.ItemFlag.ItemIsEditable)


    def clear_table(self):
        # for i in range(self.table.columnCount()):
        #     for j in range(self.table.rowCount()):
        #         self.table.setHorizontalHeaderItem(j, QtWidgets.QTableWidgetItem())
        self.table.setRowCount(0)
        self.markerIndex = 0
        self.markersDict = {}
        self.artistMarkersDict = {}

    def handle_plotted(self):
        log.debug("handle_plotted")
        self.clear_table()

    def handle_markered(self, x, states, marker, i, artist_markers):
        n = self.table.rowCount()
        try: 
            self.table.disconnect()
        except:
            pass
        #self.markersDict[str(n)]=marker[0]
        self.markersDict[self.markerIndex] = marker[0]
        self.artistMarkersDict[self.markerIndex]=[artist_markers, i, marker]
        self.markerIndex+=1 
        #self.artist_markers.remove((i, marker))

        self.table.setRowCount(n+1)
        # log.debug(f"handle_markered, x {x}, states {states}, n {n}")   
        self.table.setItem(n, 0, QtWidgets.QTableWidgetItem(",".join(states)))
        self.table.setItem(n, 1, QtWidgets.QTableWidgetItem("{}".format(x)))
        self.table.setItem(n, 3, QtWidgets.QTableWidgetItem(""))
        cbox = QtWidgets.QComboBox()
        cbox.addItem("Manual Energy")
        cbox.addItems(self.lines) 
        delButton = QtWidgets.QPushButton()
        delButton.setText("Delete")
        delButton.clicked.connect(self.deleteRow)
        self.table.setCellWidget(n, 2, cbox)
        self.table.setCellWidget(n, 4, delButton)
        self.table.resizeColumnsToContents()

        cbox.currentTextChanged.connect(self.updateTable)
        # log.debug(f"{self.getTableRows()}")

    def addDelButton(self, row, col):
        delButton = QtWidgets.QPushButton()
        delButton.setText("Delete")
        delButton.clicked.connect(self.deleteRow)
        self.table.setCellWidget(row, col, delButton)

    @QtCore.pyqtSlot()
    def deleteRow(self):
        button=self.sender()
        if button:
            row = self.table.indexAt(button.pos()).row()
            self.table.removeRow(row)
            #remove markers from the plot. incorrectly identifies the dict key if deleted out of order.
            #get the keys and sort from low to high. Then, find the row, n. Finally, pick the n'th key and delete that one.
            keyslist = []
            for key in self.markersDict:
                keyslist.append(key)
            print("list: ",keyslist, "key: ",row)
            print("dict: ",self.markersDict)
            print("removed: ", self.markersDict[keyslist[row]])
            self.markersDict[keyslist[row]].remove() #removes the plotted marker from the plot
            self.markersDict.pop(keyslist[row])    #removes the (reference to the) plotted marker from the dictionary

            am = self.artistMarkersDict[keyslist[row]] 
            am[0].remove((am[1], am[2]))    #removes the marker from the internal list of markers

            self.histHistViewer.canvas.draw()   #update plot so the marker goes away

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

    
    def importTableRows(self, cal_info):
        n = None
        self.cal_info = cal_info
        for i in range(len(self.cal_info)):
            n=self.table.rowCount()
            rowData = self.cal_info[i] #data like       [state, filtVal, name, energy]
                                #this table looks like  [name, filtVal, state, energy]
            self.table.insertRow(n)
            #print(rowPosition, rowData)
            self.table.setItem(n, 0, QtWidgets.QTableWidgetItem(rowData[2]))
            self.table.setItem(n, 1, QtWidgets.QTableWidgetItem("{}".format(rowData[1])))
            self.table.setItem(n, 3, QtWidgets.QTableWidgetItem("{}".format(rowData[3])))
            cbox = QtWidgets.QComboBox()
            cbox.addItem("Manual Energy")
            cbox.addItems(self.lines) 
            cbox.setCurrentText("{}".format(rowData[0]))
            delButton = QtWidgets.QPushButton()
            delButton.setText("Delete")
            delButton.clicked.connect(self.deleteRow)
            self.table.setCellWidget(n, 2, cbox)
            self.table.setCellWidget(n, 4, delButton)
            self.table.resizeColumnsToContents()
            cbox.currentTextChanged.connect(self.updateTable)

    
    def getChannum(self):
        self.channum = self.channelBox.currentText()
        return self.channum
    
    def getBins(self):
        if self.eRangeLow.displayText() != '':
            self.histHistViewer.binLo = float(self.eRangeLow.displayText())
        else:
            self.histHistViewer.binLo = 0

        if self.eRangeHi.displayText() != '':
            self.histHistViewer.binHi = float(self.eRangeHi.displayText())
        else:
            self.histHistViewer.binHi = 20000

        if self.binSizeBox.displayText() != '':
            self.histHistViewer.binSize = float(self.binSizeBox.displayText())
        else:
            self.histHistViewer.binSize = 50

    def updateChild(self):
        self.histHistViewer.channum = self.getChannum()
        self.getBins()

    def diagnoseCalibration(self):
        lines = self.getTableRows()
        if len(lines) == 0:
            print("Add at least one line to calibrate")
            return
        for line in lines:
            if (line[2] == 'Manual Energy') and (line[3] == ''): #if a line is clicked but no energy is assigned
                print("Assign energies to all lines and try again")
                return
        self.ds = self.data[int(self.getChannum())]
        self.ds.calibrationPlanInit("filtValue")
        
        for (states, fv, line, energy) in lines: 
            # # log.debug(f"states {states}, fv {fv}, line {line}, energy {energy}")
            #print(states.split(","))
            if line != 'Manual Energy':#in mass.spectra.keys() and not energy:
                self.ds.calibrationPlanAddPoint(float(fv), line, states=states.split(","))
                #get a set of states used by a line?


                # try:
                #     self.ds.calibrationPlanAddPoint(float(fv), line, states=states)
                # except:
                #     self.ds.calibrationPlanAddPoint(float(fv),self.common_models[str(line)], states=states)
            elif energy:# and not line in mass.spectra.keys():  
                self.ds.calibrationPlanAddPoint(float(fv), energy, states=states.split(","), energy=float(energy))
            # elif line in mass.spectra.keys() and energy:
            #     ds.calibrationPlanAddPoint(float(fv), line, states=states.split(","), energy=float(energy))

        dlo_dhi = float(self.dlo_dhiBox.text())/2.
        binsize=float(self.calBinBox.text())
        
        #self.data.cutAdd("cutForLearnDC", lambda energyRough: np.logical_and(energyRough > 0, energyRough < 10000), setDefault=False) #ideally, user can set the bounds
        #self.ds.alignToReferenceChannel(referenceChannel=self.ds, binEdges=np.arange(float(self.eRangeLow.text()),float(self.eRangeHi.text()),binsize), attr="filtValue", states=self.ds.stateLabels)
        self.newestName = "filtValue"
        if self.PCcheckbox.isChecked():
            uncorr = self.newestName
            self.newestName+="PC"
            self.ds.learnPhaseCorrection(indicatorName="filtPhase", uncorrectedName=uncorr, correctedName = self.newestName, states=self.ds.stateLabels, overwriteRecipe=True)

        if self.DCcheckbox.isChecked():
            uncorr = self.newestName
            self.newestName+="DC"
            self.ds.learnDriftCorrection(indicatorName="pretriggerMean", uncorrectedName=uncorr, correctedName = self.newestName, states=self.ds.stateLabels, overwriteRecipe=True)#, cutRecipeName="cutForLearnDC")

        if self.TDCcheckbox.isChecked():
            uncorr = self.newestName
            self.newestName+="TC"
            self.ds.learnTimeDriftCorrection(indicatorName="relTimeSec", uncorrectedName=uncorr, correctedName = self.newestName, states=self.ds.stateLabels, overwriteRecipe=True)#,cutRecipeName="cutForLearnDC", _rethrow=True) 
        self.ds.calibrateFollowingPlan(self.newestName, dlo=dlo_dhi,dhi=dlo_dhi, binsize=binsize, overwriteRecipe=True, approximate=self.Acheckbox.isChecked())
        print(f'Calibrated channel {self.ds.channum}')
        self.parent.calibratedChannels = set([self.ds.channum])

        #self.ds.calibrateFollowingPlan("filtValue", dlo=50,dhi=50, binsize=1, overwriteRecipe=True)
        self.plotter = diagnoseViewer(self)
        self.plotter.setParams(self.parent, self.data, self.ds.channum)
        self.plotter.frame.setEnabled(False)
        self.plotter.exec()

        


class HistViewer(QtWidgets.QWidget): #widget for hist calibrator and others. plots a clickable histogram.
    min_marker_ind_diff = 12
    plotted = QtCore.pyqtSignal()
    markered = QtCore.pyqtSignal(float, list, object, object, object)
    def __init__(self, parent, s=None, attr=None, state_labels=None, colors=None):
        QtWidgets.QWidget.__init__(self, parent)#, s, attr, state_labels, colors)
        #super(HistViewer, self).__init__(parent)
        super(HistViewer, self).__init__(parent)
 
        # PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/channel.ui"), self) 

    def setParams(self, parent, data, channum, attr, state_labels, colors, binSize, clickable=True, binLo=None, binHi=None, statesConfig=None):
        # QtWidgets.QWidget.__init__(self, parent)#, s, attr, state_labels, colors)
        #super(HistViewer, self).__init__(parent)
        log.debug(f"set params for histviewer")
        self.parent = parent
        self.plotAllChans = False #used to switch between self.plot and self.plotAll
        if binLo==None:
            self.binLo = 0
        else:
            self.binLo=binLo
        if binHi==None:
            self.binHi = 20000
        else:
            self.binHi=binHi
        self.binSize = binSize
        self.channum = channum
        self.lastUsedChannel = channum
        self.data=data
        self.s = data[channum]
        self.attr = attr
        self.clickable = clickable
        self.build(state_labels, colors) 
        self.connect()
        if statesConfig==None:
            self.statesGrid.fill_simple()
        else:
            self.statesGrid.fill(statesConfig)
        self.handle_plot()
        
    # def importMarkers(self, artistmarkers):
    #     self.artistMarkersDict = artistmarkers    #self.artistMarkersDict[str(n)]=[artist_markers, i, marker, artist]
    #     self.markersDict = self.parent.markersDict
    #     for i in self.artistMarkersDict:
            
    #         am = self.artistMarkersDict[str(i)] 
    #         self.markersDict[str(i)]=am[2]
    #         print("323",self.markersDict)
    #         self.add_marker(am[3], am[1], emit=False) 
        
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
        #print(self.binSize)
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
            #self.canvas.axes = self.data[int(self.channum)].plotHist(bin_edges, attr, states=states, axis=self.canvas.axes)
            # # log.debug(f"plot: loop: states={states} color={color}")
            self.line2marker[line2d] = []
            self.line2states[line2d] = states
        self.canvas.legend([",".join(states) for states in states_list])
        # self.canvas.set_xlabel(attr)
        self.canvas.set_ylabel("counts per %0.1f unit bin" %(self.binSize))

        #axis.set_ylabel("counts per %0.1f unit bin" % (binEdges[1]-binEdges[0]))
        self.canvas.set_title(self.data[int(self.channum)].shortName + ", states = {}".format(states_list))
        # plt.tight_layout()
        self.parent.photonCountBox.setText(str(self.photonCount))
        self.canvas.draw()
        #plt.connect('button_press_event', self.mpl_click_event)
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
        self.canvas.set_title(self.data.shortName + ", states = {}".format(states_list))
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
                log.debug(f"arist not in line2marker.keys() {self.line2marker.keys()}")
                pass
        else:
            pass


    def add_marker(self, artist, i, emit=True):
        artist_markers = self.line2marker[artist]
        c = plt.matplotlib.artist.getp(artist, "markerfacecolor")
        xs, ys = artist.get_data()

        for (i_, marker_) in artist_markers:
            if np.abs(i-i_) < self.min_marker_ind_diff:
                log.debug(f"not adding marker at {i}, x {xs[i]}, y {ys[i]}. too close to marker at {i_} for artist {artist} and color {c}")
                return
        marker = self.canvas.plot(xs[i], ys[i], "o", markersize=12, c=c) # cant be picked unless I pass picker?
        artist_markers.append((i, marker))
        self.line2marker[artist] = artist_markers
        if emit==True:
            self.markered.emit(xs[i], self.line2states[artist], marker, i, self.line2marker[artist])
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
    

class StatesGrid(QtWidgets.QWidget): #widget that makes a grid of checkboxes. allows user to select states and group them into colors
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
        #self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed,QtWidgets.QSizePolicy.Policy.Fixed))
        self.numberOfStates = i+1
    
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
    
    def fill(self, statesConfig): #statesConfig is "states" from get_colors_and_states_list
        for i, states in enumerate(statesConfig):
            #stateIndex=[]
            for state in states:
                #stateIndex[j] = self.state_labels.index(state)
                stateIndex= self.state_labels.index(state)
                self.boxes[stateIndex][i].setChecked(True)
            
    def fill_all(self): #intended for cases where you only have one row of states. can be modified to fill one row of any states grid...
        for (j, color) in enumerate(self.colors):
            for (i, state) in enumerate(self.state_labels):
                box = self.boxes[i][j] 
                box.setChecked(True) 

    def unfill_all(self): #same as fill_all, but unchecks boxes
        for (j, color) in enumerate(self.colors):
            for (i, state) in enumerate(self.state_labels):
                box = self.boxes[i][j] 
                box.setChecked(False) 

    def appendStates(self, newStates): #for real-time plotting: add more state boxes as more states are added during an experiment.
        for (i, state) in enumerate(newStates, self.numberOfStates): #start on i = numberOfStates so we don't override the existing boxes.
            boxes = []
            for (j, color) in enumerate(self.colors):
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
    



class HistPlotter(QtWidgets.QDialog):   #general-purpose histogram plotter. features a canvas, states grid, and energy range/# of counts information
    def __init__(self, parent=None, colors=MPL_DEFAULT_COLORS[:6]):
        super(HistPlotter, self).__init__(parent)
        #self.setWindowModality(QtCore.Qt.ApplicationModal)
        QtWidgets.QDialog.__init__(self)

    def setParams(self, parent, data, channum, attr, state_labels, binSize, colors=MPL_DEFAULT_COLORS[:6], lines=DEFAULT_LINES):
        self.parent=parent
        self.binsize=binSize
        self.build(data, channum, attr, state_labels, colors)
        self.connect()

    def build(self, data, channum, attr, state_labels, colors):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/histPlotter.ui"), self) #,  s, attr, state_labels, colors)
        #self.pHistViewer = HistViewer(self, s, attr, state_labels, colors) #pHistViewer is the name of the widget that plots.
        self.data = data
        self.channum = channum
        if len(self.parent.calibratedChannels)==len(self.data.keys()):
            self.channelBox.addItem("All")
        for channum in self.parent.calibratedChannels:#.data.keys():
            self.channelBox.addItem("{}".format(channum))
        self.channelBox.setCurrentText(str(self.channum))
        self.eRangeLow.insert(str(0))
        self.eRangeHi.insert(str(20000))
        self.pHistViewer.setParams(self, data, int(self.channum), attr, state_labels, colors,binSize=self.binsize, clickable=False)


    def connect(self):
        self.channelBox.currentTextChanged.connect(self.updateChild)
        self.eRangeLow.textChanged.connect(self.updateChild)
        self.eRangeHi.textChanged.connect(self.updateChild)

    def getChannum(self):
        self.channum = self.channelBox.currentText()
        return self.channum
    
    def updateChild(self): #send channum and bins to the pHistViewer
        # if arg == 'chan':
        #     self.pHistViewer.channum=self.getChannum()
        # if arg == 'checkbox':
        #     self.pHistViewer.plotAllChans = (not self.pHistViewer.plotAllChans)
        self.pHistViewer.channum=self.getChannum()
        if self.channum == 'All':
            self.pHistViewer.plotAllChans = True
        else:
            self.pHistViewer.plotAllChans = False
        #crashes if the range boxes are empty. Use default values instead to avoid crash.
        if self.eRangeLow.displayText() != '':
            self.pHistViewer.binLo = float(self.eRangeLow.displayText())
        else:
            self.pHistViewer.binLo = 0.

        if self.eRangeHi.displayText() != '':
            self.pHistViewer.binHi = float(self.eRangeHi.displayText())
        else:
            self.pHistViewer.binHi = 20000.
        ##energy range updating



class diagnoseViewer(QtWidgets.QDialog):    #displays the plots from the Mass diagnoseCalibration function
    def __init__(self, parent=None):
        super(diagnoseViewer, self).__init__(parent)
        QtWidgets.QDialog.__init__(self)

    def setParams(self, parent, data, channum, colors=MPL_DEFAULT_COLORS[:6], calibratedName=None):
        self.parent=parent
        self.colors = colors
        if calibratedName==None:
            self.calibratedName = "energy"
        else:
            self.calibratedName = calibratedName
        self.build(data, channum)
        self.connect()

    def build(self, data, channum):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/diagnosePlotWindow.ui"), self) #,  s, attr, state_labels, colors)
        #self.pHistViewer = HistViewer(self, s, attr, state_labels, colors) #pHistViewer is the name of the widget that plots.
        self.data = data
        self.channum = channum
        for channum in self.parent.calibratedChannels:
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

    def diagnoseCalibration(self):
        ds = self.data[self.getChannum()]
        calibration = ds.recipes[self.calibratedName].f
        uncalibratedName = calibration.uncalibratedName
        results = calibration.results
        n_intermediate = len(calibration.intermediate_calibrations)
        self.canvas.fig.clear()
        self.canvas.fig.suptitle(
            ds.shortName+", cal diagnose for '{}'\n with {} intermediate calibrations".format(self.calibratedName, n_intermediate))
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
                      axis=ax, coAddStates=False) #todo: get better ranges using max of energy value
        #ax.vlines(ds.calibrationPlan.uncalibratedVals, 0, self.canvas.fig.ylim()[1])
        #plt.tight_layout()




class rtpViewer(QtWidgets.QDialog): #window that hosts the real-time plotting routine.
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
        if len(self.parent.calibratedChannels)==len(self.parent.data.keys()):
            self.channelBox.addItem("All")
        for channum in self.parent.calibratedChannels:#.data.keys():
            self.channelBox.addItem("{}".format(channum))
        self.channelBox.setCurrentIndex(0)
        self.initRTP()

    def connect(self):
        self.updateButton.clicked.connect(self.updateButtonClicked)
        self.checkAllButton.clicked.connect(self.checkAll)
        self.uncheckAllButton.clicked.connect(self.uncheckAll)

    def updateButtonClicked(self):
        self.timer.stop()
        self.UpdatePlots()

    def uncheckAll(self):
        self.statesGrid.unfill_all()

    def checkAll(self):
        self.statesGrid.fill_all()


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
        self.energyAxis.autoscale(enable=True)
        self.rate = 0.1                     #how much to lower the transparency of lines each update
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)   #kills the timer when the RTP window is closed
        self.timer = QTimer(self)       #timer is used to loop the real-time plotting updates
        #self.timer.setSingleShot(True)    
        self.timer.timeout.connect(self.UpdatePlots)        
        #self.timer.start(self.updateFreq)
        self.UpdatePlots()

    def stopRTP(self):
        try:    #timer might not exist yet
            self.timer.stop()
        finally:
            pass

    def getDataToPlot(self):    #determines the individual channel or channel group (data) to be plotted. restarts RTP if the selection changes.
        old = self.dataToPlot
        if self.channelBox.currentText() == 'All':
            new = self.parent.data
        else:
            new = self.parent.data[int(self.channelBox.currentText())]
        if old != new: #if channel is changed, or if user goes from all channels to one channel, we need to clear the plot.
            print("Restarting RTP because channel selection has changed.")
            self.restartRTP()
        self.energyAxis.set_title(new.shortName)
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
        self.energyAxis.set_ylabel('Counts per '+str(self.parent.getBinsizeCal())+'eV bin')
        self.rtpdata=[]                             #temporary storage of data points
        self.rtpline.append([])                     #stores every line that is plotted according to the updateIndex



    def UpdatePlots(self):  #real-time plotting routine. refreshes data, adjust alphas, and replots graphs
        print(f"iteration {self.updateIndex}")
        
        self.RTPdelay = self.intervalBox.text() 
        self.updateFreq = int(self.RTPdelay)*1000             #in ms after the multiplication
        self.timer.start(self.updateFreq)

        self.updateFilesAndStates()
        
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
            self.rtpdata.append(self.dataToPlot.hist(np.arange(0, 14000, float(self.parent.getBinsizeCal())), "energy", states=States[s]))
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
        c=['#d8434e', '#f67a49', '#fdbf6f', '#feeda1', '#f1f9a9', '#bfe5a0', '#74c7a5', '#378ebb'] #8 colors from seaborn's Spectral_r colormap
        maxColors = len(c)

        cIndex =  ord(s[-1])-ord('A')
        if len(s)!=1:   #for states like AA, AB, etc., 27 is added to the value of the ones place
            cIndex=cIndex+26+ord(s[0])-ord('A')+1 #26 + value of first letter (making A=1 so AA != Z)
        while cIndex >= maxColors:       #colors repeat after maxColors states. loops until there is a valid interpolated index from cinter
            cIndex=cIndex-maxColors
        #print(s, cIndex)
        return c[cIndex]
    
    def updateFilesAndStates(self):
        oldStates = self.parent.ds.stateLabels
        self.parent.data.refreshFromFiles()                #Mass function to refresh .off files as they are updated
        newStates = list(set(oldStates).symmetric_difference(set(self.parent.ds.stateLabels)))
        if len(newStates)>0:
            print("New states found: ",newStates)
            self.statesGrid.appendStates(newStates)

    

class AvsBSetup(QtWidgets.QDialog): #for plotAvsB and plotAvsB2D functions. Allows user to select what A and B are.
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
        eIndx = self.Bbox.findText("energy")
        if eIndx == -1:
            self.Bbox.setCurrentIndex(1)
        else:
            self.Bbox.setCurrentIndex(eIndx)  

        if self.mode == "1D":
            self.binsFrame.hide()

    def connect(self):
        self.plotButton.clicked.connect(self.handlePlot)
        self.uncheckAllButton.clicked.connect(self.uncheckAll)
        self.checkAllButton.clicked.connect(self.checkAll)

    def handlePlot(self):
        #self.plotter = AvsBViewer(self)
        A = self.Abox.currentText()
        B = self.Bbox.currentText()
        _colors, states = self.statesGrid.get_colors_and_states_list()
        if len(states) == 0: #if no states are checked, don't try to plot 
            print("Error: Select one or more states to plot.")
        else:
            states=states[0]
            # if self.channelCheckbox.isChecked():
            #     channels = self.data
            # else:
            channel = self.data[int(self.channelBox.currentText())]
            if (A in channel.recipes.baseIngredients) or (A in channel.recipes.craftedIngredients.keys()):
                if (B in channel.recipes.baseIngredients) or ((B in channel.recipes.craftedIngredients.keys())):

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
                    
                else:
                    print(f"attribute {B} doesn't exist for this channel")
            else:
                print(f"attribute {A} doesn't exist for this channel")

    def uncheckAll(self):
        self.statesGrid.unfill_all()

    def checkAll(self):
        self.statesGrid.fill_all()

class linefitSetup(QtWidgets.QDialog):  #handles linefit function call. lets user choose line, states, channel
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
        if len(self.parent.calibratedChannels)==len(self.data.keys()):
            self.channelBox.addItem("All")
        for channum in self.parent.calibratedChannels:
            self.channelBox.addItem("{}".format(channum))
        self.channelBox.setCurrentIndex(0)

        for line in self.lines:
            self.lineBox.addItem("{}".format(line))
        self.lineBox.setCurrentIndex(0)     

    def connect(self):
        self.plotButton.clicked.connect(self.handlePlot)
        self.checkAllButton.clicked.connect(self.checkAll)
        self.uncheckAllButton.clicked.connect(self.uncheckAll)

    def uncheckAll(self):
        self.statesGrid.unfill_all()

    def checkAll(self):
        self.statesGrid.fill_all()

    def handlePlot(self):
        _colors, states = self.statesGrid.get_colors_and_states_list()
        try: #if the user has all states unchecked during a refresh, use the last set of states.
            states = states[0]
            self.oldStates = states
        except:
            print("No states selected in Line Fit window.")
            #states='A'
            return 0
        line = self.lineBox.currentText()
        has_linear_background = self.lbCheckbox.isChecked()
        has_tails = self.tailCheckbox.isChecked()

        dlo = self.dlo.text()
        if dlo != '': #not empty
            dlo = abs(float(self.dlo.text()))
        else:
            dlo = 15

        dhi = self.dhi.text()
        if dhi != '': #not empty
            dhi = abs(float(self.dhi.text()))
        else:
            dhi = 15

        binsize = self.binSizeBox.text()
        if binsize != '':
            binsize = float(self.binSizeBox.text())
        else:
            binsize = 1.0

        if self.channelBox.currentText() == 'All':
            dataToPlot=self.data
        else:
            dataToPlot = self.data[int(self.channelBox.currentText())]
        dataToPlot.linefit(lineNameOrEnergy=line, attr="energy", states=states, has_linear_background=has_linear_background, 
                           has_tails=has_tails, dlo=dlo, dhi=dhi, binsize=binsize)



class hdf5Opener(QtWidgets.QDialog): #dialog with a combobox which lists all of the saved calibraitions.
    def __init__(self, parent=None):
        super(hdf5Opener, self).__init__(parent)
        QtWidgets.QDialog.__init__(self)
        plt.ion()
    def setParams(self, parent):
        self.parent = parent
        self.build()
        self.connect()

    def build(self):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/hdf5Opener.ui"), self) 
        cals = self.getFileList()
        for cal in cals:
            self.fileBox.addItem("{}".format(cal))

    def connect(self):
        self.openButton.clicked.connect(self.close)

    def getFileList(self):
        calList = []
        with h5py.File('saves.h5', 'r') as file:
            runs = list(file.keys())
            for run in runs:    #individual calibrations are grouped by the run information, so we loop through the nested folders.
                for cal in list(file[run].keys()):
                    calList.append(f'{run} {cal}')
        return calList



class qualityCheckLinefitSetup(QtWidgets.QDialog):  #handles linefit function call. lets user choose line, states, channel
    def __init__(self, parent=None):
        super(qualityCheckLinefitSetup, self).__init__(parent)
        QtWidgets.QDialog.__init__(self)
        plt.ion()
    def setParams(self, parent, lines, states_list, data):
        self.colors = MPL_DEFAULT_COLORS[0]
        self.parent = parent
        self.states_list = states_list
        self.lines = lines
        self.data = data
        self.build()
        self.connect()


    def build(self):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/QualityCheckLinefit.ui"), self) 
        self.statesGrid.setParams(state_labels=self.states_list, colors=MPL_DEFAULT_COLORS[:1], one_state_per_line=False)
        self.statesGrid.fill_simple()

        for line in self.lines:
            self.lineBox.addItem("{}".format(line))
        self.lineBox.setCurrentIndex(0)     

    def connect(self):
        self.plotButton.clicked.connect(self.handlePlot)
        self.checkAllButton.clicked.connect(self.checkAll)
        self.uncheckAllButton.clicked.connect(self.uncheckAll)

    def uncheckAll(self):
        self.statesGrid.unfill_all()

    def checkAll(self):
        self.statesGrid.fill_all()

    def handlePlot(self):
        _colors, states = self.statesGrid.get_colors_and_states_list()
        try: #if the user has all states unchecked during a refresh, use the last set of states.
            states = states[0]
            self.oldStates = states
        except:
            print("No states selected in Quality Check Line Fit window.")
            #states='A'
            return 0
        line = self.lineBox.currentText()

        dlo = self.dlo.text()
        dhi = self.dhi.text()
        binsize = self.binSizeBox.text()
        fwhm = self.fwhmBox.text()

        paramsList = [dlo, dhi, binsize, fwhm]
        for i, param in enumerate(paramsList):
            if param != '': #if param has been filled
                paramsList[i] = abs(float(param))
            else:
                paramsList[i] = None
        dlo, dhi, binsize, fwhm = paramsList      

        if self.radioSigma.isChecked():
            if self.sigmaBox.text() != '':
                sigma = abs(float(self.sigmaBox.text()))
            else:
                sigma = None
        else:
            sigma = None
        
        if self.radioAbsolute.isChecked():
            if self.absoluteBox.text() != '':
                absolute = abs(float(self.absoluteBox.text()))
            else:
                absolute = None
        else:
            absolute = None

        print("paramslist ",paramsList, sigma, absolute) 

        if dlo == None:
            dlo = 50
        if dhi == None:
            dhi = 50

        self.data.qualityCheckLinefit(line, sigma, fwhm, absolute, 'energy', states, dlo, dhi, binsize, binEdges=None,
                            guessParams=None, cutRecipeName=None, holdvals=None, resolutionPlot=True, hdf5Group=None,
                            _rethrow=False)
        for channel in self.parent.goodChannels:
            self.data[channel].markGood()
        
    def closeEvent(self, event):
        for channel in self.parent.goodChannels:
            self.parent.data[channel].markGood()   

