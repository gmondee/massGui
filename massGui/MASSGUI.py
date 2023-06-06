import PyQt6.QtWidgets as QtWidgets
import PyQt6.uic
from PyQt6 import QtCore, QtGui, QtWidgets

from PyQt6.QtCore import QSettings, pyqtSlot
from PyQt6.QtWidgets import QFileDialog
import sys
import os
from pytestqt.qtbot import QtBot
import pytest
import pytestqt
from matplotlib.lines import Line2D
from .massless import HistCalibrator, HistPlotter, diagnoseViewer, rtpViewer, AvsBSetup
from .canvas import MplCanvas


import mass
from mass.off import ChannelGroup, Channel, getOffFileListFromOneFile

import numpy as np

# def main():
#     app = qt.QApplication([])
#     label = qt.QLabel("Hello")
#     label.show()

#     #button.clicked.connect(on_button_clicked)
#     #os.path.join(os.path.dirname(__file__), ... )

#     #def selectFile():
#     #   lineEdit.setText(QFileDialog.getOpenFileName())

#     app.exec_()


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        mass.line_models.VALIDATE_BIN_SIZE = False
        QtWidgets.QWidget.__init__(self)
        self.data = None 
        self.build()
        self.connect()

    def build(self):
        PyQt6.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/massGuiW.ui"), self)
        self.calibrationGroup.setEnabled(False)

    def connect(self):
        self.selectFileButton.clicked.connect(self.handle_choose_file)
        self.lineIDButton.clicked.connect(self.handle_manual_cal)
        self.oneChanCalButton.clicked.connect(self.singleChannelCalibration)
        self.resetCalButton.clicked.connect(self.resetCalibration)
        self.allChanCalButton.clicked.connect(self.allChannelCalibration)
        self.diagCalButton.clicked.connect(self.diagnoseCalibration)
        self.startRTPButton.clicked.connect(self.startRTP)
        self.AvsBbutton.clicked.connect(self.startAvsB)

    def load_file(self, filename, maxChans = None):
        self._choose_file_lastdir = os.path.dirname(filename)
        if maxChans is None:
            maxChans = self.maxChansSpinBox.value()
        filenames = getOffFileListFromOneFile(filename, maxChans)
        self.filenames = filenames
        self.data = ChannelGroup(filenames, verbose=False)
        #self.label_loadedChans.setText("loaded {} chans".format(len(self.data)))
        self.fileTextBox.setText("Curret dataset: {}".format(self.data.shortName)) 
        self.channels = []
        for channum in self.data.keys():
            self.channels.append(channum)
            #self.refChannelBox.addItem("{}".format(channum))

    def handle_choose_file(self):
        #options = QFileDialog.options(QFileDialog)
        if not hasattr(self, "_choose_file_lastdir"):
            dir = os.path.expanduser("~")
        else:
            dir = self._choose_file_lastdir
        fileName, _ = QFileDialog.getOpenFileName(
            self, "Find OFF file", dir,
            "OFF Files (*.off);;All Files (*)")#, options=options)
        if fileName:
            # log.debug("opening: {}".format(fileName))
            self.load_file(fileName) # sets self._choose_file_lastdir
            self.set_std_dev_threshold()
            #self.data_no_cal = self.data
        self.calibrationGroup.setEnabled(True) #file is loaded, user should now do the line identification.
        self.calButtonGroup.setEnabled(False) #don't let users run the calibration procedure yet. enabled in importTableRows()

    def set_std_dev_threshold(self):
        for ds in self.data.values():
            ds.stdDevResThreshold = 1000

    def handle_manual_cal(self):
        # log.debug("handle_manual_cal")
        channum = self.channels[0]#int(self.refChannelBox.currentText())
        #self.launch_channel(self.data[channum])
        self.launch_channel(self.data, channum)

    def launch_channel(self, data, channum):
        self.checkHCI()
        self.fileSelectionGroup.setEnabled(False)
        self.hc = HistCalibrator(self, data, channum, "filtValue", data[channum].stateLabels) 
        self.hc.setParams(data, channum, "filtValue", data[channum].stateLabels)
        #hc.setWindowModality(self, QtCore.Qt.ApplicationModal)
        self._selected_window = self.hc
        self.hc.exec()
        self.setChannum()
        self.ds = data[self.channum]
        self.cal_info = self.hc.getTableRows()
        self.clear_table()
        self.importTableRows()
        #self.initCal()
        self._cal_stage = 0 #_cal_stage tracks the most recent calibration activity. 0=cal plan made; 1=single channel calibration done; 2=all channel calibration
                            #I use _cal_stage so I know when I need to reload the self.data object (to switch between single and all channel calibration)
        # log.debug(f"hc dict {cal_info}")
        #self.label_calStatus.setText("{}".format(self.cal_info))

    def initCal(self):
        #self.data = self.data_no_cal

        self.data = ChannelGroup(self.filenames, verbose=False)
        self.set_std_dev_threshold()

        self.ds = self.data[self.channum]
        self.ds.calibrationPlanInit("filtValue")
        for (states, fv, line, energy) in self.cal_info: 
            # # log.debug(f"states {states}, fv {fv}, line {line}, energy {energy}")
            #print(states.split(","))
            if line and not energy:
                self.ds.calibrationPlanAddPoint(float(fv), line, states=states.split(","))
                # try:
                #     self.ds.calibrationPlanAddPoint(float(fv), line, states=states)
                # finally:
                #     self.ds.calibrationPlanAddPoint(float(fv),self.common_models[str(line)], states=states)
            elif energy and not line:  
                self.ds.calibrationPlanAddPoint(float(fv), energy, states=states.split(","), energy=float(energy))
            elif line and energy:
                self.ds.calibrationPlanAddPoint(float(fv), line, states=states.split(","), energy=float(energy))
        self.data.referenceDs = self.ds
        # log.debug(f"{ds.calibrationPlan}")
        self.tabWidget.setEnabled(True) 
        self.lineFitComboBox.setEnabled(True)

  

    def resetCalibration(self):
        self.calButtonGroup.setEnabled(False)
        self.tabWidget.setEnabled(False)
        self.clear_table()

    def get_line_names(self):
        if self.self.HCIonCheckbox.isChecked()==True:       #optional import of highly charged ions to the dropdown. Does not work now.
            from mass.calibration import _highly_charged_ion_lines
            import mass.calibration.hci_models
        self.LinesDict=list(mass.spectra.keys()) 

    def clear_table(self):
        # for i in range(self.table.columnCount()):
        #     for j in range(self.table.rowCount()):
        #         self.table.setHorizontalHeaderItem(j, QtWidgets.QTableWidgetItem())
        self.calTable.setRowCount(0)

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
    
    def importTableRows(self):
        rowPosition = None
        allowCal = True
        self.lineFitComboBox.clear()
        for i in range(len(self.cal_info)):
            rowPosition = self.calTable.rowCount()
            rowData = self.cal_info[i] #data like       [state, filtVal, name]
                                #this table looks like  [name, filtVal, state]
            #print(rowPosition, rowData)
            self.calTable.insertRow(rowPosition)
            
            if rowData[2] != '':
                self.calTable.setItem(rowPosition, 0, QtWidgets.QTableWidgetItem(rowData[2]))   #name
                self.lineFitComboBox.addItem(rowData[2])
            else:
                self.calTable.setItem(rowPosition, 0, QtWidgets.QTableWidgetItem('Name?'))
                self.calTable.item(rowPosition, 0).setBackground(QtGui.QColor(255,10,10))  #name
                allowCal = False
            self.calTable.setItem(rowPosition, 1, QtWidgets.QTableWidgetItem(rowData[1]))   #filtVal    
            self.calTable.setItem(rowPosition, 2, QtWidgets.QTableWidgetItem(rowData[0]))   #state
        if rowPosition != None and allowCal == True: #if something is added to the calibration plan and each line has a name, let user calibrate. 
            self.calButtonGroup.setEnabled(True)
        else:   #if nothing is added OR if a line isn't identified, stop the user from calibrating.
            self.calButtonGroup.setEnabled(False)


    def getChannum(self):
        channum = self.hc.histHistViewer.lastUsedChannel
        return channum

    def setChannum(self):
        self.channum = int(self.getChannum())
        self.refChannelBox.setText(str(self.channum))


    def checkHCI(self):
        if (self.HCIonCheckbox.isChecked()==True):
            import mass.calibration.hci_models
            #import mass.calibration._highly_charged_ion_lines
            self.common_models = mass.calibration.hci_models.models(has_linear_background=True)


    def singleChannelCalibration(self):
        if self._cal_stage != 1: #reset the calibration unless a single-channel calibration was done. doesn't allow user to enable/disable DC, PC, TC and redo without resetting completely...
            self.initCal()
            self._cal_stage = 1
            #self.data.cutAdd("cutForLearnDC", lambda energyRough: np.logical_and(energyRough > 0, energyRough < 10000), setDefault=False) #ideally, user can set the bounds
            try:    #crashes if user already calibrated (without resetting) and pressed it again. I want it to pull up the same plots again.
                self.ds.alignToReferenceChannel(referenceChannel=self.ds, binEdges=np.arange(0,35000,10), attr="filtValue", states=self.ds.stateLabels)
                self.newestName = "filtValue"
                if self.PCcheckbox.isChecked():
                    uncorr = self.newestName
                    self.newestName+="PC"
                    self.ds.learnPhaseCorrection(indicatorName="filtPhase", uncorrectedName=uncorr, correctedName = self.newestName, states=self.ds.stateLabels)
        
                if self.DCcheckbox.isChecked():
                    uncorr = self.newestName
                    self.newestName+="DC"
                    self.ds.learnDriftCorrection(indicatorName="pretriggerMean", uncorrectedName=uncorr, correctedName = self.newestName, states=self.ds.stateLabels)#, cutRecipeName="cutForLearnDC")

                if self.TDCcheckbox.isChecked():
                    uncorr = self.newestName
                    self.newestName+="TC"
                    self.ds.learnTimeDriftCorrection(indicatorName="relTimeSec", uncorrectedName=uncorr, correctedName = self.newestName, states=self.ds.stateLabels)#,cutRecipeName="cutForLearnDC", _rethrow=True) 
                self.ds.calibrateFollowingPlan(self.newestName, dlo=15,dhi=15, binsize=10, _rethrow=True) #add dlo, dhi, binsize options later
                print(f'Calibrated channel {self.ds.channum}')
            except:
                pass
            self.ds.calibrateFollowingPlan(self.newestName, dlo=15,dhi=15, binsize=1) #add dlo, dhi, binsize options later

        self.plotter = HistPlotter(self) 
        self.plotter.setParams(self.data, self.ds.channum, "energy", self.ds.stateLabels)
        self.plotter.channelBox.setEnabled(False)
        self.plotter.histChannelCheckbox.setEnabled(False)
        self.plotter.exec()
        #self.ds.plotHist(np.arange(0,35000,10),newestName, states=self.ds.stateLabels)

    def allChannelCalibration(self):
        self.initCal()
        self.data.alignToReferenceChannel(referenceChannel=self.ds, binEdges=np.arange(0,35000,10), attr="filtValue", states=self.ds.stateLabels)
        self.newestName = "filtValue"
        try:
            if self.PCcheckbox.isChecked():
                uncorr = self.newestName
                self.newestName+="PC"
                self.data.learnPhaseCorrection(indicatorName="filtPhase", uncorrectedName=uncorr, correctedName = self.newestName, states=self.ds.stateLabels)
        
            if self.DCcheckbox.isChecked():
                uncorr = self.newestName
                self.newestName+="DC"
                self.data.learnDriftCorrection(indicatorName="pretriggerMean", uncorrectedName=uncorr, correctedName = self.newestName, states=self.ds.stateLabels)#, cutRecipeName="cutForLearnDC")

            if self.TDCcheckbox.isChecked():
                uncorr = self.newestName
                self.newestName+="TC"
                self.data.learnTimeDriftCorrection(indicatorName="relTimeSec", uncorrectedName=uncorr, correctedName = self.newestName, states=self.ds.stateLabels)#,cutRecipeName="cutForLearnDC", _rethrow=True) 
            print(f'Calibrated {len(self.data.values())} channels using reference channel {self.ds.channum}')
        except:
            pass
        self.data.calibrateFollowingPlan(self.newestName, dlo=15,dhi=15, binsize=1, _rethrow=True) #add dlo, dhi, binsize options later
        self.plotter = HistPlotter(self) 
        self._selected_window = self.plotter
        self.plotter.setParams(self.data, self.ds.channum, "energy", self.ds.stateLabels)
        
        self.plotter.exec()

    def diagnoseCalibration(self):
        self.plotter = diagnoseViewer(self)
        self.plotter.setParams(self.data, self.ds.channum)
        self.plotter.exec()

    def handle_line_fit(self, method): #unfinished
        if method == 'comboBox':
            self.line = self.lineFitComboBox.currentText()

    def startRTP(self):
        self.binSize = 1
        self.plotter = rtpViewer(self)
        self.plotter.setParams(self)
        self.plotter.exec()

    def startAvsB(self):
        self.handleAvsB("1D")

    def handleAvsB(self, type):
        keys = list(self.ds.recipes.craftedIngredients) + list(self.ds.recipes.baseIngredients)
        if type == "1D":
            self.AvsBsetup = AvsBSetup(self) 
            self.AvsBsetup.setParams(self, keys, self.ds.stateLabels, self.data.keys(), self.data, mode = "1D")
            self.AvsBsetup.show()

        
    @property
    def selected_window(self):
        return self._selected_window

def main(test=False):
    app = QtWidgets.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    # if test:
    #     mw.load_file("/Users/oneilg/mass/src/mass/off/data_for_test/20181205_BCDEFGHI/20181205_BCDEFGHI_chan1.off")
    #     mw.set_std_dev_threshold()
    #     mw.launch_channel(mw.data.firstGoodChannel())
    retval = app.exec() 

# #https://www.youtube.com/watch?v=WjctCBjHvmA
# http://adambemski.pythonanywhere.com/testing-qt-application-python-and-pytest
