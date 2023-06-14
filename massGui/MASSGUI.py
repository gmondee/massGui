import PyQt6.QtWidgets as QtWidgets
import PyQt6.uic
from PyQt6 import QtCore, QtGui, QtWidgets

from PyQt6.QtCore import QSettings, pyqtSlot
from PyQt6.QtWidgets import QFileDialog
import sys
import os
#from pytestqt.qtbot import QtBot
#import pytest
#import pytestqt
from matplotlib.lines import Line2D
from .massless import HistCalibrator, HistPlotter, diagnoseViewer, rtpViewer, AvsBSetup, linefitSetup, hdf5Opener
from .canvas import MplCanvas


import mass
from mass.off import ChannelGroup, Channel, getOffFileListFromOneFile

import numpy as np
import h5py

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
        self.AvsB2Dbutton.clicked.connect(self.startAvsB2D)
        self.ptmButton.clicked.connect(self.plotPTM)
        self.linefitButton.clicked.connect(self.startLineFit)
        self.energyHistButton.clicked.connect(self.viewEnergyPlot)
        self.saveCalButton.clicked.connect(self.save_to_hdf5)
        self.loadCalButton.clicked.connect(self.handle_load_from_hdf5)

    def load_file(self, filename, maxChans = None):
        self._choose_file_lastdir = os.path.dirname(filename)
        if maxChans is None:
            maxChans = self.maxChansSpinBox.value()
        filenames = getOffFileListFromOneFile(filename, maxChans)
        self.filenames = filenames
        self.filename=filename
        self.data = ChannelGroup(filenames, verbose=False)
        #self.label_loadedChans.setText("loaded {} chans".format(len(self.data)))
        print("loaded {} chans".format(len(self.data)))

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
            self.plotMarkers, self.listMarkers = None, None
        
        self.calibrationGroup.setEnabled(True) #file is loaded, user should now do the line identification.
        self.calButtonGroup.setEnabled(False) #don't let users run the calibration procedure yet. enabled in importTableRows()
        self.loadCalButton.setEnabled(True) #once file is specified, a calibration can be loaded

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
        self.plotsGroup.setEnabled(False)
        self.fileSelectionGroup.setEnabled(False)
        self.hc = HistCalibrator(self) 
        self.hc.setParams(data, channum, "filtValue", data[channum].stateLabels, binSize=50)
        tableData = self.getcalTableRows()
        self.hc.importTableRows(tableData)
        self.hc.importMarkers(self.plotMarkers, self.listMarkers)
        #hc.setWindowModality(self, QtCore.Qt.ApplicationModal)
        self._selected_window = self.hc
        self.hc.exec()

        self.setChannum()
        self.ds = data[self.channum]
        self.cal_info = self.hc.getTableRows()
        self.plotMarkers, self.listMarkers = self.hc.getMarkers()
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
        self.data.learnResidualStdDevCut()
        self.ds = self.data[self.channum]
        self.ds.calibrationPlanInit("filtValue")
        for (states, fv, line, energy) in self.cal_info: 
            # # log.debug(f"states {states}, fv {fv}, line {line}, energy {energy}")
            #print(states.split(","))
            if line in mass.spectra.keys() and not energy:
                self.ds.calibrationPlanAddPoint(float(fv), line, states=states.split(","))
                # try:
                #     self.ds.calibrationPlanAddPoint(float(fv), line, states=states)
                # finally:
                #     self.ds.calibrationPlanAddPoint(float(fv),self.common_models[str(line)], states=states)
            elif energy and not line in mass.spectra.keys():  
                self.ds.calibrationPlanAddPoint(float(fv), energy, states=states.split(","), energy=float(energy))
            elif line in mass.spectra.keys() and energy:
                self.ds.calibrationPlanAddPoint(float(fv), line, states=states.split(","), energy=float(energy))
        self.data.referenceDs = self.ds
        # log.debug(f"{ds.calibrationPlan}")
        self.plotsGroup.setEnabled(True) 
        #self.lineFitComboBox.setEnabled(True)

    def getcalTableRows(self):
        rows = []
        for i in range(self.calTable.rowCount()):
            row = []
            row.append(self.calTable.item(i, 0).text())
            row.append(self.calTable.item(i, 1).text())
            row.append(self.calTable.item(i, 2).text())
            row.append(self.calTable.item(i, 3).text())
            rows.append(row)
        return rows

    def resetCalibration(self):
        self.calButtonGroup.setEnabled(False)
        self.plotsGroup.setEnabled(False)
        self.saveCalButton.setEnabled(False)
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
        #self.lineFitComboBox.clear()
        for i in range(len(self.cal_info)):
            rowPosition = self.calTable.rowCount()
            rowData = self.cal_info[i] #data like       [state, filtVal, name, energy]
                                #this table looks like  [name, filtVal, state, energy]
            #print(rowPosition, rowData)
            self.calTable.insertRow(rowPosition)
            
            if rowData[2] != 'Manual Energy': #if there is a filtValue without a line name from mass.spectra
                self.calTable.setItem(rowPosition, 0, QtWidgets.QTableWidgetItem(rowData[2]))   #name
                #self.lineFitComboBox.addItem(rowData[2])
            else:
                self.calTable.setItem(rowPosition, 0, QtWidgets.QTableWidgetItem('Manual Energy'))
                if rowData[3] == '': #if the energy isn't filled in either, prevent user from calibrating
                    self.calTable.item(rowPosition, 0).setBackground(QtGui.QColor(255,10,10))  #name
                    allowCal = False
            self.calTable.setItem(rowPosition, 1, QtWidgets.QTableWidgetItem(rowData[1]))   #filtVal    
            self.calTable.setItem(rowPosition, 2, QtWidgets.QTableWidgetItem(rowData[0]))   #state
            self.calTable.setItem(rowPosition, 3, QtWidgets.QTableWidgetItem(rowData[3]))
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
        dlo_dhi = self.getDloDhi()
        binsize=self.getBinsizeCal()
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
                self.ds.calibrateFollowingPlan(self.newestName, dlo=dlo_dhi,dhi=dlo_dhi, binsize=binsize, overwriteRecipe=True) 
                print(f'Calibrated channel {self.ds.channum}')
            except:
                print('exception in singleChannelCalibration')



        # self.plotter = HistPlotter(self) 
        # self.plotter.setParams(self.data, self.ds.channum, "energy", self.ds.stateLabels, binSize=binsize)
        # self.plotter.channelBox.setEnabled(False)
        # self.plotter.exec()


    def allChannelCalibration(self):
        dlo_dhi = self.getDloDhi()
        binsize=self.getBinsizeCal()
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

        self.data.calibrateFollowingPlan(self.newestName, dlo=dlo_dhi,dhi=dlo_dhi, binsize=binsize, _rethrow=True, overwriteRecipe=True)
        self.saveCalButton.setEnabled(True)

        # self.plotter = HistPlotter(self) 
        # self._selected_window = self.plotter
        # self.plotter.setParams(self.data, self.ds.channum, "energy", self.ds.stateLabels, binSize=binsize)
        
        # self.plotter.exec()

    def getDloDhi(self):
        return float(self.dlo_dhiBox.text())/2.0 #whole energy range is dlo+dhi, so divide by 2 to get them individually
    
    def getBinsizeCal(self):
        return float(self.binSizeBox.text())
    
    def viewEnergyPlot(self):
        plotter = HistPlotter(self)
        self._selected_window = plotter
        plotter.setParams(self.data, self.ds.channum, "energy", self.ds.stateLabels, binSize=self.getBinsizeCal())
        plotter.exec()

    def diagnoseCalibration(self):
        self.plotter = diagnoseViewer(self)
        self.plotter.setParams(self.data, self.ds.channum)
        self.plotter.exec()


    def startRTP(self):
        self.binSize = 1
        self.plotter = rtpViewer(self)
        self.plotter.setParams(self)
        self.plotter.show()
        # self.plotter.timer.stop()
        # self.plotter.close()

    def startAvsB(self):
        self.handleAvsB("1D")

    def startAvsB2D(self):
        self.handleAvsB("2D")

    def handleAvsB(self, type):
        keys = list(self.ds.recipes.craftedIngredients) + list(self.ds.recipes.baseIngredients)
        if type == "1D":
            self.AvsBsetup = AvsBSetup(self) 
            #print(self.data.keys())
            self.AvsBsetup.setParams(self, keys, self.ds.stateLabels, self.data.keys(), self.data, mode = "1D")
            self.AvsBsetup.show()
        if type == "2D":
            self.AvsBsetup = AvsBSetup(self) 
            self.AvsBsetup.setParams(self, keys, self.ds.stateLabels, self.data.keys(), self.data, mode = "2D")
            self.AvsBsetup.show()

    def plotPTM(self):
        keys = list(self.ds.recipes.craftedIngredients) + list(self.ds.recipes.baseIngredients)
        self.AvsBsetup = AvsBSetup(self) 
        self.AvsBsetup.setParams(self, keys, self.ds.stateLabels, self.data.keys(), self.data, mode = "1D")
        self.AvsBsetup.Abox.setCurrentText("relTimeSec")
        self.AvsBsetup.Bbox.setCurrentText("pretriggerMean")
        self.AvsBsetup.show()

    def startLineFit(self):
        self.lfsetup = linefitSetup(self) 
        lines = list(mass.spectra.keys())
        self.lfsetup.setParams(self, lines, states_list=self.ds.stateLabels, channels=self.data.keys(), data=self.data)
        self.lfsetup.dlo.setText(str(self.getDloDhi()))
        self.lfsetup.dhi.setText(str(self.getDloDhi()))
        self.lfsetup.binSizeBox.setText(str(self.getBinsizeCal()))
        self.lfsetup.show()

    def save_to_hdf5(self, name=None):
        with  h5py.File('saves.h5', 'a') as hf:

            str.split(self.ds.shortName)
            run_filename = str.split(self.ds.shortName)[0] +" "+ str(self.ds.channum) +" "+ str(len(self.data.values())) #filename is date_run + referenceChannel + numberOfChannels
            if run_filename in hf:
                hdf5_group = hf[run_filename]
            else:
                hdf5_group = hf.create_group(run_filename)

            name = 'testing'
            if name in hdf5_group:
                del hdf5_group[name]


            cal = self.ds.recipes['energy'].f
            print(name)
            cal_group = hdf5_group.create_group(name) #like a nested folder, as in .saves/shortName/name/[saved calibration]
            cal_group["name"] = [_name.encode() for _name in cal._names]
            cal_group["ph"] = cal._ph
            cal_group["energy"] = cal._energies
            cal_group["dph"] = cal._dph
            cal_group["de"] = cal._de
            cal_group.attrs['nonlinearity'] = cal.nonlinearity
            cal_group.attrs['curvetype'] = cal.CURVETYPE[cal._curvetype]
            cal_group.attrs['approximate'] = cal._use_approximation
            print('saved')


    def handle_load_from_hdf5(self):
        self.hdf5Opener = hdf5Opener(self) 
        self.hdf5Opener.setParams(self)
        self.hdf5Opener.exec()
        cal_name = str.split(self.hdf5Opener.fileBox.currentText(), " ")
        group_name = f'{cal_name[0]} {cal_name[1]} {cal_name[2]}' #filename is date_run + referenceChannel + numberOfChannels
        with h5py.File('saves.h5', 'r') as hf:
            group = hf[group_name]
            self.load_from_hdf5(group, name = cal_name[3], channum = int(cal_name[1]), maxChans = int(cal_name[2]))
        self.plotsGroup.setEnabled(True)


    def load_from_hdf5(self, hdf5_group, name, channum, maxChans):
        cal_group = hdf5_group[name]
        cal = mass.EnergyCalibration(cal_group.attrs['nonlinearity'],
                  cal_group.attrs['curvetype'],
                  cal_group.attrs['approximate'])
        print((cal_group.attrs['nonlinearity'],
                  cal_group.attrs['curvetype'],
                  cal_group.attrs['approximate']))
        
        _names = cal_group["name"][:]
        _ph = cal_group["ph"][:]
        _energies = cal_group["energy"][:]
        _dph = cal_group["dph"][:]
        _de = cal_group["de"][:]

        for thisname, ph, e, dph, de in zip(_names, _ph, _energies, _dph, _de):
            cal.add_cal_point(ph, e, thisname.decode(), dph, de)

        #reload data with the correct number of channels used
        self.load_file(filename=self.filename, maxChans=maxChans)
        self.ds = self.data[channum]

        self.ds.calibrationPlanInit("filtValue")
        
        #missing something here? pass in _peakLocs to data.alignToReferenceChannel
        #passed in _peakLocs, but now ds is the only remaining channel in self.data after alignment.
        self.data.alignToReferenceChannel(referenceChannel=self.ds, binEdges=np.arange(0,35000,10), attr="filtValue", states=self.ds.stateLabels, _peakLocs=_ph)
        # for channel in self.data.keys():
        #     self.data[channel].recipes.add("energy", cal, ["filtValue"], overwrite=True)
        self.ds.recipes.add("energy", cal, ["filtValue"], overwrite=True)
        
        print(self.ds.recipes.keys())

        
        # self.ds.recipes.add("energy", cal,
        #                  ["filtValue"], overwrite=True)
        
        return cal
    
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
