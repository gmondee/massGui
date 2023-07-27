# -*- coding: utf-8 -*-
#std lib imports
import sys
import os
import logging  
from copy import copy
import traceback
import warnings 

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
import pandas as pd

basedir = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(filename=os.path.join(basedir, 'masslessLog.txt'),
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

def show_popup(parent, text, traceback=None):
        msg = QtWidgets.QMessageBox(text=text, parent=parent)
        msg.setWindowTitle("Error")
        msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        if traceback is not None:
            msg.setDetailedText(traceback)
        ret = msg.exec()

class HistCalibrator(QtWidgets.QDialog):    #plots filtValues on a clickable canvas for manual line ID
    def __init__(self, parent=None):
        super(HistCalibrator, self).__init__(parent)
        #self.setWindowModality(QtCore.Qt.ApplicationModal)
        QtWidgets.QDialog.__init__(self)
        self.lines = list(mass.spectra.keys())

    def setParams(self, parent, data, channum, state_labels, binSize, colors=MPL_DEFAULT_COLORS[:6], 
                  lines=DEFAULT_LINES, statesConfig=None, markers=None, artistMarkers=None,markersIndex=None, linesNames=None, 
                  autoFWHM=None, maxacc=None, enable5lag=False):
        self.parent=parent
        self.binSize=binSize
        self.linesNames = linesNames
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
        if enable5lag:
            self.fvAttr = 'filtValue5Lag'
            self.ptmAttr = 'pretriggerMeanCorrected'
            
        else:
            self.fvAttr = 'filtValue'
            self.ptmAttr = 'pretriggerMean'
        
        self.build(data, channum, self.fvAttr, state_labels, colors, statesConfig, self.linesNames, autoFWHM, maxacc)
        self.connect()

    def build(self, data, channum, attr, state_labels, colors, statesConfig, linesNames, autoFWHM, maxacc):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/ChannelBrowser.ui"), self) #,  s, attr, state_labels, colors)
        #self.histHistViewer = HistViewer(self, s, attr, state_labels, colors) #histHistViewer is the name of the widget that plots.
        self.data = data
        self.channum = channum
        for channel in self.data.keys():
            self.channelBox.addItem("{}".format(channel))
        self.channelBox.setCurrentText(str(channum))
        self.eRangeLow.setValue(0)
        try:
            binHi = np.percentile(self.data[channum].getAttr('filtValue', state_labels), 98) #get the value of the filtValue at the 98th percentile (98th meaning close to the maximum)
        except:
            print('Unable to automatically set bounds')
            binHi = 20000
        self.eRangeHi.setValue(binHi)
        self.binSizeBox.setValue(50)
        self.histHistViewer.setParams(self, data, channum, attr, state_labels, colors, self.binSize, statesConfig=statesConfig, binHi = binHi)
        if autoFWHM == None:
            self.autoFWHMBox.setValue(25)
        else:
            self.autoFWHMBox.setValue(autoFWHM)
        if maxacc == None:
            self.autoMaxAccBox.setValue(0.015)
        else:
            self.autoMaxAccBox.setValue(maxacc)
        self.importMarkers()
        self.importList()


    def connect(self):
        self.histHistViewer.plotted.connect(self.handle_plotted)
        self.histHistViewer.markered.connect(self.handle_markered)
        self.channelBox.currentTextChanged.connect(self.updateChild)
        self.eRangeLow.valueChanged.connect(self.updateChild)
        self.eRangeHi.valueChanged.connect(self.updateChild)
        self.binSizeBox.valueChanged.connect(self.updateChild)

        self.diagCalButton.clicked.connect(self.diagnoseCalibration)
        self.autocalButton.clicked.connect(self.autoCalibration)
        self.linesList.itemSelectionChanged.connect(self.listChanged)
        self.listSearchBox.textChanged.connect(self.searchItem)

        #self.closeButton.clicked.connect(self.close) #removed
        #self.table.itemChanged.connect(self.updateTable)

    def importMarkers(self):
        for marker in self.markersDict:
            artist = self.markersDict[marker]
            new_ax = self.histHistViewer.canvas.axes
            #self.markersDict[marker].plot()
            artist.remove()
            artist.axes = new_ax
            artist.set_transform(new_ax.transData)
            new_ax.add_artist(artist)

    def importList(self):
        self.linesList.addItems(self.lines)
        if self.linesNames != None:
            for line in self.linesNames:
                item = self.linesList.findItems(line, QtCore.Qt.MatchFlag.MatchExactly)
                item[0].setSelected(True)
                self.linesList.setCurrentItem(item[0])

    def listChanged(self):
        self.autoListOfLines.clear()
        self.autoListOfLines.setText(str([item.text() for item in self.linesList.selectedItems()]))
        self.linesNames = [item.text() for item in self.linesList.selectedItems()]

    def searchItem(self):
        search_string = self.listSearchBox.text()
        match_items = self.linesList.findItems(search_string, QtCore.Qt.MatchFlag.MatchContains)
        for i in range(self.linesList.count()):
            it = self.linesList.item(i)
            it.setHidden(it not in match_items)

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
            # print("list: ",keyslist, "key: ",row)
            # print("dict: ",self.markersDict)
            # print("removed: ", self.markersDict[keyslist[row]])
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
        if self.binSizeBox.value() != 0:
            self.histHistViewer.binSize = self.binSizeBox.value()
        else:
            self.histHistViewer.binSize = 50
        self.histHistViewer.binLo = self.eRangeLow.value()


        if self.eRangeHi.value() > self.histHistViewer.binLo+self.histHistViewer.binSize:
            self.histHistViewer.binHi = self.eRangeHi.value()
        else:
            self.histHistViewer.binHi = self.histHistViewer.binLo+self.histHistViewer.binSize*2.0

    def updateChild(self):
        self.histHistViewer.channum = self.getChannum()
        self.getBins()

    def autoCalibration(self):
        self.linesNames = [item.text() for item in self.linesList.selectedItems()]
        colors, states_list = self.histHistViewer.statesGrid.get_colors_and_states_list()
        states_list = states_list[0] 
        autoFWHM = float(self.autoFWHMBox.value())
        maxacc = float(self.autoMaxAccBox.value())
        try:
            self.ds = self.data[int(self.getChannum())]
            #print(self.linesNames)
            names, filtValues = self.ds.learnCalibrationPlanFromEnergiesAndPeaks(self.fvAttr, states=states_list, ph_fwhm=autoFWHM, line_names=self.linesNames, maxacc=maxacc)
            #todo: import the cal stuff into the table.
            self.highestFV=max(filtValues)
            self.diagnoseCalibration(auto=True)
        except Exception as exc:
            print("Failed to autocalibrate!")
            print(traceback.format_exc())
            show_popup(self, "Failed to autocalibrate!", traceback=traceback.format_exc())

    def diagnoseCalibration(self, auto=False):
        if auto == False:
            lines = self.getTableRows()
            if len(lines) == 0:
                print("Add at least one line to calibrate")
                return
            for line in lines:
                if (line[2] == 'Manual Energy') and (line[3] == ''): #if a line is clicked but no energy is assigned
                    print("Assign energies to all lines and try again")
                    return
            self.ds = self.data[int(self.getChannum())]
            self.ds.calibrationPlanInit(self.fvAttr)
            self.highestFV = 0. #used to set better bounds in the diagnose plot
            for (states, fv, line, energy) in lines: 
                # # log.debug(f"states {states}, fv {fv}, line {line}, energy {energy}")
                try:
                    self.highestFV = max(self.highestFV, float(fv))
                except:
                    self.highestFV = None
                try:
                    if line != 'Manual Energy':#in mass.spectra.keys() and not energy:
                        self.ds.calibrationPlanAddPoint(float(fv), line, states=states.split(","))
                    elif energy:# and not line in mass.spectra.keys():  
                        self.ds.calibrationPlanAddPoint(float(fv), energy, states=states.split(","), energy=float(energy))
                    # elif line in mass.spectra.keys() and energy:
                    #     ds.calibrationPlanAddPoint(float(fv), line, states=states.split(","), energy=float(energy))
                except Exception as exc:
                    print(f"Failed to add {line} to calibration plan!")
                    print(traceback.format_exc())
                    show_popup(self, f"Failed to add {line} to calibration plan!", traceback=traceback.format_exc())
                    return
        dlo_dhi = float(self.dlo_dhiBox.value()/2.)
        binsize=float(self.calBinBox.value())
        try:
            #self.data.cutAdd("cutForLearnDC", lambda energyRough: np.logical_and(energyRough > 0, energyRough < 10000), setDefault=False) #ideally, user can set the bounds
            self.newestName = self.fvAttr
            if self.PCcheckbox.isChecked():
                uncorr = self.newestName
                self.newestName+="PC"
                self.ds.learnPhaseCorrection(indicatorName="filtPhase", uncorrectedName=uncorr, correctedName = self.newestName, states=self.ds.stateLabels, overwriteRecipe=True)

            if self.DCcheckbox.isChecked():
                uncorr = self.newestName
                self.newestName+="DC"
                self.ds.learnDriftCorrection(indicatorName=self.ptmAttr, uncorrectedName=uncorr, correctedName = self.newestName, states=self.ds.stateLabels, overwriteRecipe=True)#, cutRecipeName="cutForLearnDC")

            if self.TDCcheckbox.isChecked():
                uncorr = self.newestName
                self.newestName+="TC"
                self.ds.learnTimeDriftCorrection(indicatorName="relTimeSec", uncorrectedName=uncorr, correctedName = self.newestName, states=self.ds.stateLabels, overwriteRecipe=True)#,cutRecipeName="cutForLearnDC", _rethrow=True) 
            self.ds.calibrateFollowingPlan(self.newestName, dlo=dlo_dhi,dhi=dlo_dhi, binsize=binsize, overwriteRecipe=True, approximate=self.Acheckbox.isChecked())
            print(f'Calibrated channel {self.ds.channum}')
            self.parent.calibratedChannels = set([self.ds.channum])
            self.plotter = diagnoseViewer(self)
            self.plotter.setParams(self.parent, self.data, self.ds.channum, highestFV = self.highestFV)
            self.plotter.frame.setEnabled(False)
            self.plotter.exec()
        except Exception as exc:
            print("Failed to diagnose calibration!")
            print(traceback.format_exc())
            show_popup(self, "Failed to diagnose calibration!", traceback=traceback.format_exc())

        


class HistViewer(QtWidgets.QWidget): #widget for hist calibrator and others. plots a clickable histogram.
    min_marker_ind_diff = 12
    plotted = QtCore.pyqtSignal()
    markered = QtCore.pyqtSignal(float, list, object, object, object)
    def __init__(self, parent, s=None, attr=None, state_labels=None, colors=None):
        QtWidgets.QWidget.__init__(self, parent)
        super(HistViewer, self).__init__(parent)
 
        # PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/channel.ui"), self) 

    def setParams(self, parent, data, channum, attr, state_labels, colors, binSize, clickable=True, binLo=None, binHi=None, statesConfig=None):
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
        
    def build(self, state_labels, colors):
        layout = QtWidgets.QVBoxLayout()
        self.canvas = MplCanvas()   ### this line makes an extra plot
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
        colors, states_list = self.statesGrid.get_colors_and_states_list() 
        self.photonCount = 0
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
            self.min_marker_ind_diff = self.binSize/4


    def plot(self, states_list, bin_edges, attr, colors):
        #print(self.data[int(self.channum)].channum)
        self.lastUsedChannel = self.data[int(self.channum)].channum
        self.canvas.clear()
        self.line2marker = {} #pass in a line, get the markers associated with it
        self.line2states = {} #pass in a line, get the states associated with it
        ax = self.data[int(self.channum)].plotHist(bin_edges, attr, states=states_list, axis=self.canvas.axes, coAddStates=False)
        for i, line in enumerate(ax.get_lines()):
            line.set_picker(4) #enables clicking; '4' is the tolerance on picker range
            self.photonCount += sum(line.get_ydata())
            self.line2marker[line] = []
            self.line2states[line] = states_list[i]
            line.set_color(colors[i])
        self.parent.photonCountBox.setText(str(self.photonCount))
        self.canvas.legend([",".join(states) for states in states_list])
        self.canvas.draw()
        self.canvas.mpl_connect('pick_event', self.mpl_click_event)
        self.plotted.emit()

    def plotAll(self, states_list, bin_edges, attr, colors):
        print("plotting all channels")
        self.canvas.clear()
        self.line2marker = {} #pass in a line, get the markers associated with it
        self.line2states = {} #pass in a line, get the states associated with it
        ax = self.data.plotHist(bin_edges, attr, states=states_list, axis=self.canvas.axes, coAddStates=False)
        for i, line in enumerate(ax.get_lines()):
            line.set_picker(4) #enables clicking; '4' is the tolerance on picker range
            self.photonCount += sum(line.get_ydata())
            self.line2marker[line] = []
            self.line2states[line] = states_list[i]
            line.set_color(colors[i])
        self.parent.photonCountBox.setText(str(self.photonCount))
        self.canvas.legend([",".join(states) for states in states_list])
        plt.tight_layout()
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
    
    def clearLayout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clearLayout(item.layout())

    def connect(self):
        for (j, color) in enumerate(self.colors):
            for (i, state) in enumerate(self.state_labels):
                box = self.boxes[i][j]    
                box.stateChanged.connect(lambda state, i=i, j=j: self.handle_state_change(state, i, j))     
    
    def fill_simple(self):
        if len(self.state_labels) == 1: #if START is the only state, then enable it
            self.boxes[0][0].setChecked(True)
        else:
            for (j, color) in enumerate(self.colors):
                for (i, state) in enumerate(self.state_labels):
                    box = self.boxes[i][j] 
                    box.setChecked(i==j+1)   #j+1 because we probably don't want to see START very often. 

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
    
    def fill(self, statesConfig): #reloads your last selection. statesConfig is "states" from get_colors_and_states_list
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

    def appendStates(self, newStates, state_labels): #for real-time plotting: add more state boxes as more states are added during an experiment.
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
                box.setStyleSheet("background-color: {}".format(color))
                self.grid.addWidget(box, j+1, i+1)
                boxes.append(box)
                if j == 0:
                    box.setChecked(True)
            self.boxes.append(boxes)
        self.numberOfStates+= len(newStates)
        self.state_labels = state_labels
        self.connect()
    

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
        self.eRangeLow.setValue(0)
        self.eRangeHi.setValue(10000)
        self.pHistViewer.setParams(self, data, int(self.channum), attr, state_labels, colors,binSize=self.binsize, clickable=False)
        self.updateChild()
        self.pHistViewer.handle_plot()

    def connect(self):
        self.channelBox.currentTextChanged.connect(self.updateChild)
        self.eRangeLow.valueChanged.connect(self.updateChild)
        self.eRangeHi.valueChanged.connect(self.updateChild)

    def getChannum(self):
        self.channum = self.channelBox.currentText()
        return self.channum
    
    def updateChild(self): #send channum and bins to the pHistViewer
        self.pHistViewer.channum=self.getChannum()
        if self.channum == 'All':
            self.pHistViewer.plotAllChans = True
        else:
            self.pHistViewer.plotAllChans = False
        if self.eRangeLow.value() >= 0.0:
            self.pHistViewer.binLo = self.eRangeLow.value()
        else:
            self.pHistViewer.binLo = 0.0

        if self.eRangeHi.value() > self.binsize:
            self.pHistViewer.binHi = self.eRangeHi.value()
        else:
            self.pHistViewer.binHi = 2*self.binsize #minimum of 2 bins needed
        ##energy range updating


class diagnoseViewer(QtWidgets.QDialog):    #displays the plots from the Mass diagnoseCalibration function
    def __init__(self, parent=None):
        super(diagnoseViewer, self).__init__(parent)
        QtWidgets.QDialog.__init__(self)

    def setParams(self, parent, data, channum, colors=MPL_DEFAULT_COLORS[:6], calibratedName=None, highestFV=16000):
        self.parent=parent
        self.colors = colors
        self.highestFV = highestFV #highest filtValue used during calibration to determine what range of filtValues to plot
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
        self.canvas.fig.clear()
        try:
            try:
                filtValuePlotBinEdges=np.arange(0, self.highestFV*1.5, 4)
            except:
                filtValuePlotBinEdges=np.arange(0, 16000.0*1.5, 4)
            ds.diagnoseCalibration(filtValuePlotBinEdges = filtValuePlotBinEdges, fig=plt.get_fignums()[-1])
        except Exception as exc:
            print("Failed to diagnose calibration!")
            print(traceback.format_exc())
            show_popup(self, "Failed to diagnose calibration!", traceback=traceback.format_exc())


class rtpViewer(QtWidgets.QDialog): #window that hosts the real-time plotting routine.
    def __init__(self, parent=None):
        super(rtpViewer, self).__init__(parent)
        QtWidgets.QDialog.__init__(self)

    def setParams(self, parent):
        self.colors =MPL_DEFAULT_COLORS[1]
        
        self.parent = parent
        self.stateLabels = self.parent.ds.stateLabels
        self.dataToPlot = self.parent.data
        self.build()
        self.connect()

    def build(self):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/realtimeviewer.ui"), self)
        self.RTPdelay = self.intervalBox.value() 
        self.statesGrid.setParams(state_labels=self.parent.ds.stateLabels, colors=MPL_DEFAULT_COLORS[:1], one_state_per_line=False)
        self.statesGrid.fill_simple()
        if len(self.parent.calibratedChannels)==len(self.parent.data.keys()):
            self.channelBox.addItem("All")
        for channum in self.parent.calibratedChannels:#.data.keys():
            self.channelBox.addItem("{}".format(channum))
        self.channelBox.setCurrentIndex(0)
        self.eRangeLow.setValue(0)
        self.eRangeHi.setValue(10000)
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
        self.canvas.fig.clear()
        self.energyAxis = self.canvas.fig.add_subplot(111)
        self.energyAxis.grid()
        self.canvas.fig.set_layout_engine('tight')
        self.energyAxis.set_title('Real-time energy')
        self.energyAxis.set_xlabel('Energy (eV)')
        self.energyAxis.set_ylabel('Counts per'+str(self.parent.binSize)+'eV bin')
        self.energyAxis.autoscale(enable=True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)   #kills the timer when the RTP window is closed
        self.timer = QTimer(self)       #timer is used to loop the real-time plotting updates
        self.timer.timeout.connect(self.UpdatePlots)        
        self.UpdatePlots()

    def stopRTP(self): #never called right now, but this is how you might do it
        try:    #timer might not exist yet
            self.timer.stop()
        except:
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
        self.canvas.fig.set_tight_layout(True)
        self.energyAxis.set_title('Real-time energy')
        self.energyAxis.set_xlabel('Energy (eV)')
        self.energyAxis.set_ylabel('Counts per '+str(self.parent.getBinsizeCal())+'eV bin')
        self.rtpdata=[]                             #temporary storage of data points
        self.rtpline.append([])                     #stores every line that is plotted according to the updateIndex

    def getEnergyBounds(self):
        binLo = self.eRangeLow.value()
        if self.eRangeHi.value() > binLo:
            binHi = self.eRangeHi.value()
        else:
            binHi = 10000.
        return binLo, binHi

    def UpdatePlots(self):  #real-time plotting routine. refreshes data, adjust alphas, and replots graphs
        print(f"iteration {self.updateIndex}")
        self.updateFreq_ms = int(self.intervalBox.value()*1000)           #in ms after the multiplication
        self.timer.start(self.updateFreq_ms)
        self.updateFilesAndStates()
        eLow, eHi = self.getEnergyBounds()
        _colors, States = self.statesGrid.get_colors_and_states_list()
        try: #if the user has all states unchecked during a refresh, use the last set of states.
            States = States[0]
            self.oldStates = States
        except:
            States = self.oldStates
            print("No states checked, using last set of valid states:", States)
        self.dataToPlot = self.getDataToPlot()
        for line in self.energyAxis.get_lines():
            line.remove()
        self.plottedStates = []
        for s in range(len(States)):    #looping over each state passed in
            x,y = self.dataToPlot.hist(np.arange(eLow, eHi, float(self.parent.getBinsizeCal())), "energy", states=States[s])
            self.energyAxis.plot(x, y ,alpha=1, color=self.getColorfromState(States[s]))    #plots the [x,y] points and assigns color based on the state
            if States[s] not in self.plottedStates:     #new states are added to the legend; old ones are already there                      
                self.plottedStates.append(States[s])

        customLegend=[]         #temporary list to store the legend
        for s in self.plottedStates:    #loops over all states called during the current real-time plotting routine
            customLegend.append(Line2D([0], [0], color=self.getColorfromState(s)))      #each state is added to the legend with the state's respective color
        self.energyAxis.legend(customLegend, list(self.plottedStates))                  #makes the legend
        self.canvas.draw()
        self.updateIndex=self.updateIndex+1


    def getColorfromState(self, s): #pass in a state label string like 'A' or 'AC' (for states past Z) and get a color index using plt.colormaps() 
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
        new_labels, new_pulses_dict = self.parent.data.refreshFromFiles()                #Mass function to refresh .off files as they are updated
        #print(f'{new_labels=} {new_pulses_dict=}')
        diff = set(self.parent.ds.stateLabels) - set(oldStates) #list(set(oldStates).symmetric_difference(set(self.parent.ds.stateLabels)))
        newStates = [s for s in self.parent.ds.stateLabels if s in diff]
        if len(newStates)>0:
            print("New states found: ",newStates)
            self.statesGrid.appendStates(newStates, self.parent.ds.stateLabels)

        #print(self.parent.ds.statesDict)

    

class AvsBSetup(QtWidgets.QDialog): #for plotAvsB and plotAvsB2D functions. Allows user to select what A and B are.
    def __init__(self, parent=None):
        super(AvsBSetup, self).__init__(parent)
        QtWidgets.QDialog.__init__(self)
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
        if eIndx == -1: #if "energy" isn't found in the list of attrs
            self.Bbox.setCurrentIndex(1)
        else:
            self.Bbox.setCurrentIndex(eIndx)  

        if self.mode == "1D":
            self.binsFrame.hide()
            self.rangeFrame.hide()
        elif self.mode == "2D":
            self.updateBounds()

    def connect(self):
        self.plotButton.clicked.connect(self.handlePlot)
        self.uncheckAllButton.clicked.connect(self.uncheckAll)
        self.checkAllButton.clicked.connect(self.checkAll)
        if self.mode == "2D":
            self.Abox.currentTextChanged.connect(self.updateBounds)
            self.Bbox.currentTextChanged.connect(self.updateBounds)

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
                        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
                        [plt.close(f) for f in plt.get_fignums() if f != plt.get_fignums()[-1]]
                        plt.show()
                    if self.mode == "2D":
                        Ahi = self.aRangeHi.value()
                        Alo = self.aRangeLo.value()
                        
                        Bhi = self.bRangeHi.value()
                        Blo = self.bRangeLo.value()

                        res = int(self.binsBox.value())
                        self.zoomPlot = ZoomPlotAvsB(channel, states, A, B, mins = [Alo, Blo], maxes=[Ahi, Bhi], resolution = res)
                    
                else:
                    print(f"attribute {B} doesn't exist for this channel")
            else:
                print(f"attribute {A} doesn't exist for this channel")

    def uncheckAll(self):
        self.statesGrid.unfill_all()

    def checkAll(self):
        self.statesGrid.fill_all()

    def updateBounds(self):
        A = self.Abox.currentText()
        B = self.Bbox.currentText()
        channel = self.data[int(self.channelBox.currentText())]
        if (A in channel.recipes.baseIngredients) or (A in channel.recipes.craftedIngredients.keys()):
            if (B in channel.recipes.baseIngredients) or ((B in channel.recipes.craftedIngredients.keys())):
                #get some value near the upper percentile of each attr to suggest
                try:
                    Abound = np.percentile(channel.getAttr(A, self.states_list), 95) #get the value of the record at the 95th percentile (95th meaning close to the maximum)
                    self.aRangeHi.setValue(Abound)
                    Abound = np.percentile(channel.getAttr(A, self.states_list), 5) #get the value of the record at the 5th percentile (5th meaning close to the minimum)
                    self.aRangeLo.setValue(Abound)
                except:
                    print(f"Could not automatically set bound for {A}")
                try:
                    Bbound = np.percentile(channel.getAttr(B, self.states_list), 95) #todo: get .A and .B into meaningful attrs
                    self.bRangeHi.setValue(Bbound)
                    Bbound = np.percentile(channel.getAttr(B, self.states_list), 5) #get the value of the record at the 5th percentile (5th meaning close to the minimum)
                    self.bRangeLo.setValue(Bbound)
                except:
                    print(f"Could not automatically set bound for {B}")
            else:
                    show_popup(self, f"attribute {B} doesn't exist for this channel")
                    print(f"attribute {B} doesn't exist for this channel")
                    return
        else:
            print(f"attribute {A} doesn't exist for this channel")
            show_popup(self, f"attribute {A} doesn't exist for this channel")
            return
        

class ZoomPlotAvsB(): #only works for 2D plots.
    def __init__(self, channel, states, A, B, mins, maxes, resolution):
        matplotlib.use("QtAgg")
        self.mins = mins
        self.maxes = maxes
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111)
        fm = plt.get_current_fig_manager() #figure manager, for the toolbar
        fm.toolbar.actions()[0].triggered.connect(self.home_callback)   #when "home" is pressed on the toolbar, do self.home_callback()
        self.xmin = mins[0]; self.xmax = maxes[0]
        self.ymin = mins[1]; self.ymax = maxes[1]
        self.xpress = self.xmin
        self.xrelease = self.xmax
        self.ypress = self.ymin
        self.yrelease = self.ymax
        self.resolution = resolution
        self.channel = channel
        self.states = states
        self.A = A
        self.B = B

        self.fig.canvas.mpl_connect('button_press_event', self.onpress)
        self.fig.canvas.mpl_connect('button_release_event', self.onrelease)
        self.plot_fixed_resolution(self.xmin, self.xmax,
                                   self.ymin, self.ymax)
        plt.colorbar()
        [plt.close(f) for f in plt.get_fignums() if f != plt.get_fignums()[-1]]
        plt.show()


    def home_callback(self):    #plot the original bounds
        self.plot_fixed_resolution(self.mins[0], self.maxes[0],
                                   self.mins[1], self.maxes[1])

    def plotAvsB2D(self, x, y):
        bins = [x,y]
        self.channel.plotAvsB2d(self.A, self.B, binEdgesAB = bins, axis=self.ax, states=self.states)

    def plot_fixed_resolution(self, x1, x2, y1, y2):
        x = np.linspace(x1, x2, self.resolution)
        y = np.linspace(y1, y2, self.resolution)
        bins = [x,y]
        self.ax.clear()
        self.ax.set_xlim(x1, x2)
        self.ax.set_ylim(y1, y2)
        self.plotAvsB2D(x, y)
        self.fig.canvas.draw()

    def onpress(self, event):
        if event.button != 1: return
        self.xpress = event.xdata
        self.ypress = event.ydata

    def onrelease(self, event):
        if event.button != 1: return
        self.xrelease = event.xdata
        self.yrelease = event.ydata
        self.xmin = min(self.xpress, self.xrelease)
        self.xmax = max(self.xpress, self.xrelease)
        self.ymin = min(self.ypress, self.yrelease)
        self.ymax = max(self.ypress, self.yrelease)
        self.plot_fixed_resolution(self.xmin, self.xmax,
                                   self.ymin, self.ymax)


class linefitSetup(QtWidgets.QDialog):  #handles linefit function call. lets user choose line, states, channel
    def __init__(self, parent=None):
        super(linefitSetup, self).__init__(parent)
        QtWidgets.QDialog.__init__(self)

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
            show_popup(self, "No states selected in Line Fit window.")
            return 0
        line = self.lineBox.currentText()
        has_linear_background = self.lbCheckbox.isChecked()
        has_tails = self.tailCheckbox.isChecked()

        dlo = self.dlo.value()
        if dlo != 0: #not zero
            dlo = abs(self.dlo.value())
        else:
            dlo = 15

        dhi = self.dhi.value()
        if dhi != 0: #not empty
            dhi = abs(self.dhi.value())
        else:
            dhi = 15

        binsize = self.binSizeBox.value()
        if binsize > 0:
            binsize = abs(self.binSizeBox.value())
        else:
            binsize = 1.0

        if self.channelBox.currentText() == 'All':
            dataToPlot=self.data
        else:
            dataToPlot = self.data[int(self.channelBox.currentText())]
        result = dataToPlot.linefit(lineNameOrEnergy=line, attr="energy", states=states, has_linear_background=has_linear_background, 
                           has_tails=has_tails, dlo=dlo, dhi=dhi, binsize=binsize)
        [plt.close(f) for f in plt.get_fignums() if f != plt.get_fignums()[-1]]
        plt.show()


class hdf5Opener(QtWidgets.QDialog): #dialog with a combobox which lists all of the saved calibraitions.
    def __init__(self, parent=None):
        super(hdf5Opener, self).__init__(parent)
        QtWidgets.QDialog.__init__(self)

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
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/qualityCheckLinefit.ui"), self) 
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
            show_popup(self,"No states selected in Line Fit window.")
            return 0
        line = self.lineBox.currentText()

        dlo = self.dlo.value()
        dhi = self.dhi.value()
        binsize = self.binSizeBox.value()
        if binsize == 0:
            print("Bin size must be larger than zero.")
            return
        fwhm = self.fwhmBox.value()     

        if self.radioSigma.isChecked():
            sigma = self.sigmaBox.value()
        else:
            sigma = None
        
        if self.radioAbsolute.isChecked():
            absolute = self.absoluteBox.value()
        else:
            absolute = None

        if dlo == None:
            dlo = 50
        if dhi == None:
            dhi = 50

        try:
            self.data.qualityCheckLinefit(line, sigma, fwhm, absolute, 'energy', states, dlo, dhi, binsize, binEdges=None,
                                guessParams=None, cutRecipeName=None, holdvals=None, resolutionPlot=True, hdf5Group=None,
                                _rethrow=False)
            [plt.close(f) for f in plt.get_fignums() if f != plt.get_fignums()[-1]]
            plt.show()
        except Exception as exc:
            print("Failed quality check line fit!")
            print(traceback.format_exc())
            show_popup(self, "Failed quality check line fit!", traceback=traceback.format_exc())
        finally:
            for channel in self.parent.goodChannels:
                self.data[channel].markGood()
        
    def closeEvent(self, event):
        for channel in self.parent.goodChannels:
            self.parent.data[channel].markGood()   


class ExternalTriggerSetup(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(ExternalTriggerSetup, self).__init__(parent)
        QtWidgets.QDialog.__init__(self)

    def setParams(self, parent, states_list, channels, data, basename):
        self.colors = MPL_DEFAULT_COLORS[0]
        self.parent = parent
        self.states_list = states_list
        self.channels = channels
        self.data = data
        self.basename = basename
        self.build()
        self.connect()

    def build(self):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/externalTriggerSetup.ui"), self) 
        self.statesGrid.setParams(state_labels=self.states_list, colors=MPL_DEFAULT_COLORS[:1], one_state_per_line=False)
        self.statesGrid.fill_all()
        if len(self.parent.calibratedChannels)==len(self.data.keys()):
            self.channelBox.addItem("All")
        for channum in self.parent.calibratedChannels:
            self.channelBox.addItem("{}".format(channum))

    def connect(self):
        self.plotButton.clicked.connect(self.handlePlot)
        self.uncheckAllButton.clicked.connect(self.uncheckAll)
        self.checkAllButton.clicked.connect(self.checkAll)

    def handlePlot(self):
        #self.plotter = AvsBViewer(self)
        _colors, states = self.statesGrid.get_colors_and_states_list()
        if len(states) == 0: #if no states are checked, don't try to plot 
            print("Error: Select one or more states to plot.")
        else:
            states=states[0]
            channelBox = self.channelBox.currentText()
            if channelBox == 'All':
                channels = self.parent.data.values()
            else:
                channels = [self.parent.data[int(channelBox)]]

            mins, maxes, resolution = self.getBins()

            self.zoomPlot = ZoomPlotExternalTrigger(parent = self.parent, channels=channels, states=states, mins=mins, maxes=maxes, resolution=resolution, basename=self.basename, good_only=self.goodIndsCheckBox.isChecked())
        
    def getBins(self):
        if self.eRangeLo.text() != '':
            elo = float(self.eRangeLo.text())
        else:
            elo = 0.0
        if self.eRangeHi.text() != '':
            ehi = float(self.eRangeHi.text())
        else:
            ehi = 10000.0

        if self.tRangeLo.text() != '':
            tlo = float(self.tRangeLo.text())
        else:
            tlo = 0.0

        if self.tRangeHi.text() != '':
            thi = float(self.tRangeHi.text())
        else:
            thi = 3.0

        if self.resBox.text() != '':
            resolution = int(self.resBox.text())
        else:
            resolution = 500.
        
        return [tlo, elo], [thi, ehi], resolution

    def uncheckAll(self):
        self.statesGrid.unfill_all()

    def checkAll(self):
        self.statesGrid.fill_all()


class ZoomPlotExternalTrigger(): #only works for external trigger plots.
    def __init__(self, parent, states, basename, mins, maxes, resolution, channels, good_only):
        matplotlib.use("QtAgg")
        self.mins = mins
        self.maxes = maxes
        self.parent=parent #parent here is the massGui itself
        self.basename=basename

        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111)
        self.ax.cla()
        self.fig.clear()
        plt.xlabel("time since external trigger (s)")
        plt.ylabel("energy(eV)")
        plt.title(f"{len(channels)} channels,\n states={states}")
        fm = plt.get_current_fig_manager() #figure manager, for the toolbar
        fm.toolbar.actions()[0].triggered.connect(self.home_callback)   #when "home" is pressed on the toolbar, do self.home_callback()
        self.tmin = mins[0]; self.tmax = maxes[0] #time min and max
        self.emin = mins[1]; self.emax = maxes[1] #energy min and max
        self.resolution = resolution
        self.xpress = self.tmin
        self.xrelease = self.tmax
        self.ypress = self.emin
        self.yrelease = self.emax
        self.channels = channels #either data[channum] or all of data
        self.states = states
        self.good_only = good_only

        self.external_trigger_filename =  os.path.join(f"{basename}_external_trigger.bin")
        self.external_trigger_rowcount = self.get_external_triggers(self.external_trigger_filename, good_only=good_only)
        for ds in channels:
            self.calc_external_trigger_timing(ds, self.external_trigger_rowcount)

        self.fig.canvas.mpl_connect('button_press_event', self.onpress)
        self.fig.canvas.mpl_connect('button_release_event', self.onrelease)
        self.plot_fixed_resolution(self.tmin, self.tmax,
                                   self.emin, self.emax)
        cb = plt.colorbar()
        #self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)   #kills the timer when the RTP window is closed
        self.timer = QTimer()       #timer is used to loop the real-time plotting updates  
        #self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.updatePlots)
        self.updateFreq_ms = int(30)*1000             #in ms after the multiplication
        self.timer.start(self.updateFreq_ms)
        self.fig.canvas.mpl_connect('close_event', self.on_close)

    def on_close(self, event):
        self.timer.stop()

    def updatePlots(self):
        print("Updating external trigger plot...")
        self.parent.data.refreshFromFiles()
        self.external_trigger_rowcount = self.get_external_triggers(self.external_trigger_filename, good_only=self.good_only)
        for ds in self.channels:
            self.calc_external_trigger_timing(ds, self.external_trigger_rowcount)
        
        self.plot_fixed_resolution(self.tmin, self.tmax,
                                self.emin, self.emax)

    def home_callback(self):    #plot the original bounds
        self.plot_fixed_resolution(self.mins[0], self.maxes[0],
                                   self.mins[1], self.maxes[1])

    def plotExtTrigger(self, ts, es): #plots the external trigger plot
        with warnings.catch_warnings():
            warnings.simplefilter(action='ignore', category=FutureWarning) #ignore the FutureWarning when using the cuts array in sec = np.concatenate([sec, [array][cuts array]])
            seconds_after_external_triggers = []
            energies = []
            for ds in self.channels:
                sec = []
                energy = []
                for s in self.states:
                    sec = np.concatenate([sec,ds.seconds_after_external_trigger[tuple(ds.getStatesIndicies(states=[s]))][ds.getAttr("cutNone", [s], "cutNone")]]) #change the cut by swapping out the first "cutNone" with another cut.
                    energy = np.concatenate([energy, ds.getAttr("energy", s, "cutNone")])
                seconds_after_external_triggers = np.concatenate([seconds_after_external_triggers, sec])
                energies = np.concatenate([energies, energy])

            plt.figure(self.fig)
            #print(f'{seconds_after_external_triggers.shape=}, {energies.shape=}')
            plt.hist2d(seconds_after_external_triggers, energies, bins=(ts, es))

            [plt.close(f) for f in plt.get_fignums() if f != plt.get_fignums()[-1]]
            plt.show()

    def plot_fixed_resolution(self, x1, x2, y1, y2):
        x = np.linspace(x1, x2, num=self.resolution) #todo: can't use arange because lengths aren't the same
        y = np.linspace(y1, y2, num=self.resolution)
        self.ax.clear()
        self.ax.set_xlim(x1, x2)
        self.ax.set_ylim(y1, y2)
        self.plotExtTrigger(x, y)
        self.fig.canvas.draw()

    def onpress(self, event):
        if event.button != 1: return
        self.xpress = event.xdata
        self.ypress = event.ydata

    def onrelease(self, event):
        if event.button != 1: return
        self.xrelease = event.xdata
        self.yrelease = event.ydata
        self.tmin = min(self.xpress, self.xrelease)
        self.tmax = max(self.xpress, self.xrelease)
        self.emin = min(self.ypress, self.yrelease)
        self.emax = max(self.ypress, self.yrelease)
        self.plot_fixed_resolution(self.tmin, self.tmax,
                                self.emin, self.emax)
        
    def get_external_triggers(self, filename, good_only):
        f = open(filename,"rb")
        f.readline() # discard comment line
        external_trigger_rowcount = np.fromfile(f,"int64")
        if good_only:
            external_trigger_rowcount = external_trigger_rowcount[self.get_good_trig_inds(external_trigger_rowcount)]
        return external_trigger_rowcount

    def get_good_trig_inds(self, external_trigger_rowcount, plot=False):
        d = np.diff(external_trigger_rowcount)
        median_diff = np.median(np.diff(external_trigger_rowcount))
        good_inds = np.where(d > median_diff/2)[0]
        if plot:
            plt.figure()
            plt.plot(d,".",label="all")
            plt.plot(good_inds, d[good_inds],".",label="good")
            plt.legend()
        return good_inds

    def calc_external_trigger_timing(self, ds, external_trigger_rowcount):
        nRows = ds.offFile.header["ReadoutInfo"]["NumberOfRows"]
        rowcount = ds.offFile["framecount"] * nRows
        rows_after_last_external_trigger, rows_until_next_external_trigger = \
            mass.core.analysis_algorithms.nearest_arrivals(rowcount, external_trigger_rowcount)
        ds.rowPeriodSeconds = ds.offFile.framePeriodSeconds/float(nRows)
        ds.rows_after_last_external_trigger = rows_after_last_external_trigger
        ds.rows_until_next_external_trigger = rows_until_next_external_trigger
        ds.seconds_after_external_trigger = rows_after_last_external_trigger*ds.rowPeriodSeconds
        ds.seconds_until_next_external_trigger = rows_until_next_external_trigger*ds.rowPeriodSeconds
    

class RoiRtpSetup(QtWidgets.QDialog): #real-time regions of interest todo: add realtime 
    def __init__(self, parent=None):
        super(RoiRtpSetup, self).__init__(parent)
        #self.setWindowModality(QtCore.Qt.ApplicationModal)
        QtWidgets.QDialog.__init__(self)
        self.lines = list(mass.spectra.keys())
        self.numberOfRegionsMade = 0 #goes up by 1 when a new ROI is made. Doesn't go down when one is deleted. Used to make unique names for the ROIdict.

    def setParams(self, parent, data, channum, state_labels, colors=MPL_DEFAULT_COLORS[:6]):
        self.parent=parent
        self.build(data, channum, state_labels, colors)
        self.connect()

    def build(self, data, channum, state_labels, colors):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/RoiRtpSetup.ui"), self)
        self.statesGrid.setParams(state_labels=state_labels, colors=MPL_DEFAULT_COLORS[:1], one_state_per_line=False)
        self.statesGrid.fill_all()
        self.data = data
        self.channum = channum
        if len(self.parent.calibratedChannels)==len(self.data.keys()):
            self.channelBox.addItem("All")
        self.channelBox.setCurrentText(str(self.channum))
        for channel in self.data.keys():
            self.channelBox.addItem("{}".format(channel))
        self.channelBox.setCurrentText(str(channum))
        #if all chans
        self.linesBox.addItem("Manual Energy")
        self.linesBox.addItems(self.lines) 

    def connect(self):
        self.startRTPButton.clicked.connect(self.startROIRTP)
        self.checkAllButton.clicked.connect(self.checkAll)
        self.uncheckAllButton.clicked.connect(self.uncheckAll)
        self.linesBox.currentTextChanged.connect(self.updateLinesBox)
        self.addButton.clicked.connect(self.handle_add_row)
        self.readNewButton.clicked.connect(self.updateFilesAndStates)

    def uncheckAll(self):
        self.statesGrid.unfill_all()

    def checkAll(self):
        self.statesGrid.fill_all()

    def updateLinesBox(self, line):
        #called when the user switches the selected line in linesBox
        #switches the autofilled energy in energyBox and, unless the user selects "Manual Energy", prevents user from changing it
        if self.linesBox.currentText() == line and line in mass.spectra.keys():
            self.energyBox.setEnabled(False)
            self.energyBox.setValue(mass.spectra[line].nominal_peak_energy)
        elif self.linesBox.currentText() == "Manual Energy":
            self.energyBox.setEnabled(True)

    def clear_table(self):
        self.table.setRowCount(0)

    def handle_add_row(self):
        #get the info for a new region and add it with add_row()
        line = self.linesBox.currentText() 
        energy = str(self.energyBox.value())
        width = str(self.widthBox.value())
        self.add_row(line, energy, width)

    def add_row(self, line, energy, width):
        n = self.table.rowCount()
        try: #i don't remember why this is here
            self.table.disconnect()
        except:
            pass
        name = f'ROI{self.numberOfRegionsMade}'
        self.numberOfRegionsMade+=1
        self.table.setRowCount(n+1)
        # log.debug(f"handle_markered, x {x}, states {states}, n {n}")   
        self.table.setItem(n, 0, QtWidgets.QTableWidgetItem("{}".format(name)))
        self.table.setItem(n, 1, QtWidgets.QTableWidgetItem("{}".format(line)))
        self.table.setItem(n, 2, QtWidgets.QTableWidgetItem("{}".format(energy)))
        self.table.setItem(n, 3, QtWidgets.QTableWidgetItem("{}".format(width)))

        for row in [1,2,3]: #users shouldn't edit the line, energy, and width once it's added. they SHOULD still edit the name--table.item(n,0)
            self.table.item(n,row).setFlags(self.table.item(n,row).flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)

        #add a delete button on the end of the row
        delButton = QtWidgets.QPushButton()
        delButton.setText("Delete")
        delButton.clicked.connect(self.deleteRow)
        self.table.setCellWidget(n, 4, delButton)
        self.table.resizeColumnsToContents()
       
    def addDelButton(self, row, col): #if you want to add a delete button manually
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

    def getTableRows(self):
        rows = []
        for i in range(self.table.rowCount()):
            row = []
            for j in [0,1,2,3]:
                row.append(self.table.item(i, j).text())
            rows.append(row)
        return rows
    
    def getChannum(self):
        #returns one channel number OR 'All' to indicate that all channels should be used.
        self.channum = self.channelBox.currentText()
        return self.channum

    def startROIRTP(self):
        if len(self.getTableRows()) == 0:
            show_popup(self, "Create at least one region of interest first.\nOnce a line or energy has been specified, click the Add button to add it to the table.")
            return
        ROIdict = {}
        _colors, states = self.statesGrid.get_colors_and_states_list()
        if len(states)==0:
            show_popup(self, "Select at least one state using the state grid.")
            return
        states = states[0] #get_colors_and_states_list returns a list of lists of states; we only use one row of states in the grid, so we only care about the first list of states.
        if self.getChannum() == 'All':
            channums = self.data.keys()
        else:
            channums = [int(self.getChannum())]

        rollingAvgTimeSec = self.intervalBox.value()
        numberOfChunks = self.chunksBox.value()
        self.fig = plt.figure()
        self.channums = channums
        self.states = states
        self.rollingAvgTimeSec = rollingAvgTimeSec
        self.numberOfChunks = numberOfChunks
        self.ROIdict = ROIdict
        [plt.close(f) for f in plt.get_fignums() if f != plt.get_fignums()[-1]]
        plt.ion()
        for row in self.getTableRows():
            #print(row)
            Name = row[0]
            Energy = float(row[2])
            Width = float(row[3])
            ROIdict[Name]=[Energy-Width/2, Energy+Width/2]
        self.plotRollingAverages(self.data, channums, states, rollingAvgTimeSec, numberOfChunks, ROIdict, self.fig)
        self.startRTP()

    def getAvgs(self, arr, windowSize, chunkTimeSec):
        #takes in an array and returns the rolling average of each value and the k=windowSize values to its left.
        #when there are not windowSize number of values to the left, repeat the first value.
        #one chunk is defined as one of numberOfChunks parts of the rollingAvgTimeSec, which is how much of the past you want to consider for the rolling average.
        #if windowSize=1, i.e. if there is only one chunk, then this returns avgs=arr/chunkTimeSec
        #avgs is an array of counts per second in each chunk.
        if windowSize==1:
            return np.array(arr)/chunkTimeSec
        avgs = []
        for i, val in enumerate(arr):
            if i-windowSize<0:
                iInd = i
                values=[]
                while iInd-windowSize < 0:
                    values.append(arr[0])
                    iInd+=1
                arrInd=1
                while len(values)<windowSize:
                    values.append(arr[arrInd])
                    arrInd+=1
            else:
                values = arr[i-windowSize+1:i+1]
            avgs.append(sum(values)/len(values)/chunkTimeSec)
        return avgs

    def plotRollingAverages(self, data, channums, states, rollingAvgTimeSec, numberOfChunks, ROIdict, figure):
        #data is a ChannelGroup
        #channums is a list containing a single channel or all channels
        #states is a list of states
        #rollingAvgTimeSec is the period of time to 'look back' when calculating the rolling average
        #numberOfChunks is how many times we sample/split up the rollingAvgTimeSec time period
        #ROIdict is a dictionary that contains info about the bounds for each region of interest (ROI). it looks like ROIdict['name']=[lower energy bound, upper energy bound]
        #figure is a plt.figure() so we don't keep creating new ones. needed for real-time purposes.
        try:
            channelAvgs = None #this will store how many counts show up in each ROI for each bin of unixnanos. each channel gets added to this total.
            lastState=states[-1] #used to get the counts in the last plotted state
            lastStateCounts=np.zeros(len(ROIdict.keys())) #stores the number of counts in the last state
            for channel in channums:
                ds = data[channel]
                unixnano, energy = ds.getAttr(['unixnano', 'energy'], states)
                chunkTimeSec = rollingAvgTimeSec/numberOfChunks #how long each chunk lasts, in seconds
                chunkStartTime=unixnano[0] #keeps track of the next chunk's start time, in unixnanos
                chunkStartIndecies=[] #defines chunks in terms of indecies of the 'energy' attribute
                t=np.arange(unixnano[0], unixnano[-1], step = chunkTimeSec*10**9)
                while chunkStartTime <= unixnano[-1]: #go until you reach the end of the state(s)
                    #break unixnano into "chunks" according to their indicies
                    chunkStartIndecies.append(np.searchsorted(unixnano, chunkStartTime))
                    chunkStartTime+=chunkTimeSec*10**9
                regionAvgs=[]
                for j, ROIbounds in enumerate(ROIdict.values()):
                    lastStateCounts[j]+=len([pulse for pulse in ds.getAttr('energy',lastState) if (pulse>=ROIbounds[0]) and (pulse<=ROIbounds[1])])
                    chunkCounts = []
                    for i, chunkIndex in enumerate(chunkStartIndecies):
                        if i < len(chunkStartIndecies)-1:
                            pulses = energy[chunkStartIndecies[i]:chunkStartIndecies[i+1]]
                        else:
                            pulses = energy[chunkStartIndecies[i]:] #if its the last chunk, go until the end of that state
                        chunkCounts.append(len([pulse for pulse in pulses if (pulse>=ROIbounds[0]) and (pulse<=ROIbounds[1])]))
                    regionAvgs.append(self.getAvgs(chunkCounts, numberOfChunks, chunkTimeSec)  )
                if np.equal(channelAvgs,None).all():
                    channelAvgs=np.array(regionAvgs)
                else:
                    regionAvgs = np.array(regionAvgs)
                    #make sure regionAvgs and channelAvgs are the same shape. Pad with zeros if necessary.
                    if regionAvgs.shape[1]>channelAvgs.shape[1]:
                        temp = channelAvgs
                        channelAvgs = np.ones(regionAvgs.shape)*0
                        channelAvgs[:,:temp.shape[1]] = temp
                    elif regionAvgs.shape[1]<channelAvgs.shape[1]:
                        temp = regionAvgs
                        regionAvgs = np.ones(channelAvgs.shape)*0
                        regionAvgs[:,:temp.shape[1]] = temp

                    channelAvgs = channelAvgs + regionAvgs

            #replace values btwn requested states with np.nan
            #NaN time will be the same for each region, so just loop through the first axis of channelAvgs
            """
            loop through the requested states. For each state:
                get the start and stop times with ds.getAttr('unixnano', state)[0 or -1]
                find the start and stop indecies of 'energy' with np.searchsorted(unixnano, stateStartOrEndTime), make slices (ranges?) of t
            if a values in t/channelAvgs lies outside of the state ranges, set channelAvgs to np.nan
            """
            unixnano = ds.getAttr('unixnano', states)
            stateIndexRanges = []
            stateTimeEnds = np.array([])
            for state in states:
                stateUnixnano = ds.getAttr('unixnano', state)
                stateIndexRanges.append(np.searchsorted(t, [stateUnixnano[0], stateUnixnano[-1]]))
                stateTimeEnds = np.append(stateTimeEnds, [stateUnixnano[-1]]) #last unixnano in each state
            stateIndexRanges = np.array(stateIndexRanges, dtype=int)  
            currentIndex = 0
            for i, iRange in enumerate(stateIndexRanges):
                for region in channelAvgs:
                    region[currentIndex:iRange[0]] = np.nan
                    if i <= len(stateTimeEnds)-2:
                        shortStateIndex = np.searchsorted(t, stateTimeEnds[i])+1 #find the chunk that would contain the end of this state
                        lastStateDurationSec = abs(stateTimeEnds[i] - t[shortStateIndex])*10**-9
                        region[iRange[1]] = region[iRange[1]]*(chunkTimeSec/lastStateDurationSec)

                    else:
                        lastChunkTime = abs((unixnano[-1] - chunkStartTime)*10**-9)
                        #print(f'{lastChunkTime=}')
                        region[-1] = region[-1]*(chunkTimeSec/lastChunkTime)
                currentIndex = iRange[1]
            
            plt.figure(self.fig)
            self.fig.clear()
            self.ax=plt.gca()
            customLegend=[]
            colors=['#d8434e', '#f67a49', '#fdbf6f', '#feeda1', '#f1f9a9', '#bfe5a0', '#74c7a5', '#378ebb']
            for i, region in enumerate(channelAvgs):
                color = colors[i % len(colors)]
                self.ax.plot(t, region*chunkTimeSec, color=color)
                customLegend.append(f"{[k for k in ROIdict.keys()][i]} Counts in {lastState} :{lastStateCounts[i]}")
            self.ax.legend(customLegend)
            plt.xlabel('Time (unixnanos)')
            plt.ylabel(f'Counts per {chunkTimeSec} seconds')
            plt.title(f'{len(channums)} Channels\nStates: {",".join(states)}')
            plt.grid(True)
            x_bounds = self.ax.get_xlim()
            y_bounds = self.ax.get_ylim()
            for s in states:
                stateStart = ds.getAttr('unixnano',s)[0]
                plt.vlines(stateStart,0,y_bounds[1], linestyles='dashed',color='k', label=s) 
                self.ax.annotate(text=s, xy =(((stateStart-x_bounds[0])/(x_bounds[1]-x_bounds[0])),0.98), xycoords='axes fraction', verticalalignment='top', horizontalalignment='center' , rotation = 0)
            plt.draw()
        except Exception as exc: 
            print("Failed to plot regions of interest!")
            print(traceback.format_exc())
            show_popup(self, "Failed to plot regions of interest!", traceback=traceback.format_exc())
            try:
                self.timer.stop()
            except:
                pass

    def startRTP(self):
        #make a timer
        #every [interval] seconds, refresh from files. then, call (basically) the code above but on the same plot
        self.fig.canvas.mpl_connect('close_event', self.on_close)
        self.timer = QTimer()       #timer is used to loop the real-time plotting updates  
        self.timer.timeout.connect(self.updateAndPlot)
        self.updateFreq_ms = int(self.intervalBox.value())*1000             #in ms after the multiplication
        self.timer.start(self.updateFreq_ms)

    def on_close(self, event):
        self.timer.stop()
        plt.ioff()

    def updateFilesAndStates(self):
        try:
            self.timer.stop()
            self.updateFreq_ms = int(self.intervalBox.value())*1000             #in ms after the multiplication
            self.timer.start(self.updateFreq_ms)
        except:
            pass
        oldStates = self.parent.ds.stateLabels
        new_labels, new_pulses_dict = self.parent.data.refreshFromFiles()                #Mass function to refresh .off files as they are updated
        #print(f'{new_labels=} {new_pulses_dict=}')
        diff = set(self.parent.ds.stateLabels) - set(oldStates) #list(set(oldStates).symmetric_difference(set(self.parent.ds.stateLabels)))
        newStates = [s for s in self.parent.ds.stateLabels if s in diff]
        if len(newStates)>0:
            print("New states found: ",newStates)
            self.statesGrid.appendStates(newStates, self.parent.ds.stateLabels)
    
    def updateAndPlot(self):
        self.updateFilesAndStates()
        _colors, states = self.statesGrid.get_colors_and_states_list()
        states = states[0] #get_colors_and_states_list returns a list of lists of states; we only use one row of states in the grid, so we only care about the first list of states.
        if self.getChannum() == 'All':
            self.channums = self.data.keys()
        else:
            self.channums = [int(self.getChannum())]

        self.rollingAvgTimeSec = self.intervalBox.value()
        self.numberOfChunks = self.chunksBox.value()
        self.plotRollingAverages(self.data, self.channums, self.states, self.rollingAvgTimeSec, self.numberOfChunks, self.ROIdict, self.fig)


class progressPopup(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(progressPopup, self).__init__(parent)
        QtWidgets.QDialog.__init__(self)

    def setParams(self, steps):
        self.build(steps)

    def build(self, steps):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/progressPopup.ui"), self)
        self.progressBar.setMaximum(steps)

    def addText(self, text):
        self.textEdit.insertPlainText(text)

    def nextValue(self):
        self.progressBar.setValue(self.progressBar.value()+1)


class exportList(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(exportList, self).__init__(parent)
        QtWidgets.QDialog.__init__(self)

    def setParams(self, parent):
        self.parent = parent
        self.build()
        self.connect()

    def build(self):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/exportList.ui"), self)

    def connect(self):    
        self.energyHistButton.clicked.connect(self.exportEnergyHist)
    
    def exportEnergyHist(self):
        self.exporter = energyHistExport()
        self.exporter.setParams(self.parent)
        self.exporter.show()


class energyHistExport(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(energyHistExport, self).__init__(parent)
        QtWidgets.QDialog.__init__(self)

    def setParams(self, parent):
        self.parent = parent #parent is the massGui main window
        self.stateLabels = self.parent.ds.stateLabels
        self.build()
        self.connect()

    def build(self):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/energyHistExport.ui"), self)
        self.statesGrid.setParams(state_labels=self.parent.ds.stateLabels, colors=MPL_DEFAULT_COLORS[:1], one_state_per_line=False)
        self.statesGrid.fill_simple()
        if len(self.parent.calibratedChannels)==len(self.parent.data.keys()):
            self.channelBox.addItem("All")
        for channum in self.parent.calibratedChannels:#.data.keys():
            self.channelBox.addItem("{}".format(channum))

    def connect(self):
        self.exportButton.clicked.connect(self.handleExportClicked)
        self.checkAllButton.clicked.connect(self.checkAll)
        self.uncheckAllButton.clicked.connect(self.uncheckAll)
        self.outputPathButton.clicked.connect(self.handle_choose_file)

    def uncheckAll(self):
        self.statesGrid.unfill_all()

    def checkAll(self):
        self.statesGrid.fill_all()

    def exportToCsv(self, filepath, statesList, channel):
        if channel == 'All':
            dataToExport = self.parent.data
        else:
            dataToExport = self.parent.data[int(channel)]

        for sta in statesList:
            histall = np.array(dataToExport.hist(np.arange(self.eRangeLo.value(), self.eRangeHi.value(), self.binSizeBox.value()), "energy", states=sta))
            histall = histall.T
            stadat = pd.DataFrame(data=histall)
            exportName = os.path.join(filepath,self.parent.basename+'_export_'+''.join(sta)+'.csv')
            stadat.to_csv(exportName, index=False)
        show_popup(self, f"Successfully exported to {filepath}!")

    def handleExportClicked(self):
        try:
            fmt = self.exportFormatBox.currentText()
            filepath = self.outputPathLineEdit.text()
            colors, states = self.statesGrid.get_colors_and_states_list()
            channel = self.channelBox.currentText()

            #statesList is always a list. For coadded, it is like [['A','B','C',...]] and for non-coadded it is like ['A','B','C',...] 
            if not self.coAddCheckBox.isChecked():
                #separate states into separate list elements
                statesList = []
                for s in states[0]:
                    statesList.append(s)
            else:
                statesList = states
            if fmt == '.csv':
                self.exportToCsv(filepath, statesList, channel)
        except Exception as exc:
            print("Failed to export!")
            print(traceback.format_exc())
            show_popup(self, "Failed to export!", traceback=traceback.format_exc())

    def handle_choose_file(self):
        if not hasattr(self, "_choose_file_lastdir"):
            dir = os.path.expanduser("~")
        else:
            dir = self._choose_file_lastdir
        folderpath = str(QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder'))
        if folderpath:
            self._choose_file_lastdir = folderpath
            self.outputPathLineEdit.setText(folderpath)
            self.exportButton.setEnabled(True)
            return folderpath
        else:
            self.exportButton.setEnabled(False)