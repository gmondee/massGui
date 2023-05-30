import PyQt5.QtWidgets as QtWidgets
import PyQt5.uic
from PyQt5 import QtCore, QtGui, QtWidgets

from PyQt5.QtCore import QSettings, pyqtSlot
from PyQt5.QtWidgets import QFileDialog
import sys
import os
from pytestqt.qtbot import QtBot
import pytest
import pytestqt

from .massless import HistCalibrator


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

        QtWidgets.QWidget.__init__(self)
        self.data = None 
        self.build()
        self.connect()

    def build(self):
        PyQt5.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/massGuiW.ui"), self)

    def connect(self):
        self.selectFileButton.clicked.connect(self.handle_choose_file)
        self.lineIDButton.clicked.connect(self.handle_manual_cal)
        self.oneChanCalButton.clicked.connect(self.singleChannelCalibration)
        # self.pushButton_calibrate.clicked.connect(self.handle_calibrate)
        # self.pushButton_plotEnergy.clicked.connect(self.handle_plot)
        # self.pushButton_refresh.clicked.connect(self.handle_refresh)

    def load_file(self, filename, maxChans = None):
        self._choose_file_lastdir = os.path.dirname(filename)
        if maxChans is None:
            maxChans = self.maxChansSpinBox.value()
        filenames = getOffFileListFromOneFile(filename, maxChans)
        self.data = ChannelGroup(filenames, verbose=False)
        #self.label_loadedChans.setText("loaded {} chans".format(len(self.data)))
        self.fileTextBox.setText("Curret dataset: {}".format(self.data.shortName)) 
        self.channels = []
        for channum in self.data.keys():
            self.channels.append(channum)
            #self.refChannelBox.addItem("{}".format(channum))

    def handle_choose_file(self):
        options = QFileDialog.Options()
        if not hasattr(self, "_choose_file_lastdir"):
            dir = os.path.expanduser("~")
        else:
            dir = self._choose_file_lastdir
        fileName, _ = QFileDialog.getOpenFileName(
            self, "Find OFF file", dir,
            "OFF Files (*.off);;All Files (*)", options=options)
        if fileName:
            # log.debug("opening: {}".format(fileName))
            self.load_file(fileName) # sets self._choose_file_lastdir
            self.set_std_dev_threshold()

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
        self.hc.exec_()
        ds = data[channum]
        self.cal_info = self.hc.getTableRows()
        self.clear_table()
        self.importTableRows()
        self.setChannum()
        # log.debug(f"hc dict {cal_info}")
        #self.label_calStatus.setText("{}".format(self.cal_info))
        ds.calibrationPlanInit("filtValue")
        for (states, fv, line, energy) in self.cal_info: 
            # # log.debug(f"states {states}, fv {fv}, line {line}, energy {energy}")
            if line and not energy:
                ds.calibrationPlanAddPoint(float(fv), line, states=states)
            elif energy and not line:  
                ds.calibrationPlanAddPoint(float(fv), energy, states=states, energy=float(energy))
            elif line and energy:
                ds.calibrationPlanAddPoint(float(fv), line, states=states, energy=float(energy))
        self.data.referenceDs = ds
        # log.debug(f"{ds.calibrationPlan}")

    def get_line_names(self):
        if self.HCvar.get() == 1:       #optional import of highly charged ions to the dropdown
            from mass.calibration import _highly_charged_ion_lines
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
        for i in range(len(self.cal_info)):
            rowPosition = self.calTable.rowCount()
            rowData = self.cal_info[i] #data like       [state, filtVal, name]
                                #this table looks like  [name, filtVal, state]
            #print(rowPosition, rowData)
            self.calTable.insertRow(rowPosition)
            self.calTable.setItem(rowPosition, 0, QtWidgets.QTableWidgetItem(rowData[2]))
            self.calTable.setItem(rowPosition, 1, QtWidgets.QTableWidgetItem(rowData[1]))
            self.calTable.setItem(rowPosition, 2, QtWidgets.QTableWidgetItem(rowData[0]))


    def getChannum(self):
        channum = self.hc.channelBox.currentText()
        return channum

    def setChannum(self):
        channum = self.getChannum()
        self.refChannelBox.setText(str(channum))


    def checkHCI(self):
        if (self.HCIonCheckbox.isChecked()==True):
            import mass.calibration.hci_models
            import mass.calibration._highly_charged_ion_lines


    def singleChannelCalibration(self):
        self.ds = self.data[int(self.getChannum())]
        #self.data.cutAdd("cutForLearnDC", lambda energyRough: np.logical_and(energyRough > 0, energyRough < 10000), setDefault=False) #ideally, user can set the bounds

        newestName = "filtValue"
        if self.PCcheckbox.isChecked():
            self.ds.learnPhaseCorrection(indicatorName="filtPhase", uncorrectedName=newestName, correctedName = "filtValuePC", states=self.ds.stateLabels)
            newestName = "filtValuePC"
        if self.DCcheckbox.isChecked():
            self.ds.learnDriftCorrection(indicatorName="pretriggerMean", uncorrectedName=newestName, correctedName = "filtValuePCDC", states=self.ds.stateLabels)#, cutRecipeName="cutForLearnDC")
            newestName = "filtValuePCDC"
        if self.TDCcheckbox.isChecked():
            self.ds.learnTimeDriftCorrection(indicatorName="relTimeSec", uncorrectedName=newestName, correctedName = "filtValuePCDCTC", states=self.ds.stateLabels)#,cutRecipeName="cutForLearnDC", _rethrow=True) 
            newestName = "filtValuePCDCTC"
        self.ds.plotHist(np.arange(0,35000,10),newestName, states=self.ds.stateLabels)


def main(test=False):
    app = QtWidgets.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    # if test:
    #     mw.load_file("/Users/oneilg/mass/src/mass/off/data_for_test/20181205_BCDEFGHI/20181205_BCDEFGHI_chan1.off")
    #     mw.set_std_dev_threshold()
    #     mw.launch_channel(mw.data.firstGoodChannel())
    retval = app.exec_() 

# #https://www.youtube.com/watch?v=WjctCBjHvmA
# http://adambemski.pythonanywhere.com/testing-qt-application-python-and-pytest
