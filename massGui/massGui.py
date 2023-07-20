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
from .massless import HistCalibrator, HistPlotter, diagnoseViewer, rtpViewer, AvsBSetup, linefitSetup, hdf5Opener, qualityCheckLinefitSetup, ExternalTriggerSetup, RoiRtpSetup, progressPopup
from .canvas import MplCanvas
from .ProjectorsGui import projectorsGui
import progress
import traceback
from mass.calibration import algorithms

import mass
from mass.off import ChannelGroup, Channel, getOffFileListFromOneFile

import numpy as np
import h5py


def ds_learnCalibrationPlanFromEnergiesAndPeaks(self, attr, states, ph_fwhm, line_names, maxacc):
    peak_ph_vals, _peak_heights = algorithms.find_local_maxima(self.getAttr(attr, indsOrStates=states), ph_fwhm)
    _name_e, energies_out, opt_assignments = algorithms.find_opt_assignment(peak_ph_vals, line_names, maxacc=maxacc)

    self.calibrationPlanInit(attr)
    for ph, name in zip(opt_assignments, _name_e):
        self.calibrationPlanAddPoint(ph, name, states=states)
    return _name_e, opt_assignments
mass.off.Channel.learnCalibrationPlanFromEnergiesAndPeaks = ds_learnCalibrationPlanFromEnergiesAndPeaks

def show_popup(parent, text, traceback=None):
        msg = QtWidgets.QMessageBox(text=text, parent=parent)
        msg.setWindowTitle("Error")
        msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        if traceback is not None:
            msg.setDetailedText(traceback)
        ret = msg.exec()

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
        self.calibratedChannels = set()
        self.calibrationGroup.setEnabled(False)
        self.enable5lag = False
        progress.Infinite.file = sys.stderr 
        self.excludeStates = ['STOP', 'END', 'IGNORE']

    def connect(self):
        self.selectFileButton.clicked.connect(self.handle_choose_file)
        self.lineIDButton.clicked.connect(self.handle_manual_cal)
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
        self.qualityButton.clicked.connect(self.startQualityCheck)
        self.allChanAutoCalButton.clicked.connect(self.allChannelAutoCalibration)
        self.extTrigButton.clicked.connect(self.handleExternalTrigger)
        self.readNewButton.clicked.connect(self.readNewFilesAndStates)
        self.startROIRTPButton.clicked.connect(self.startROIRTP)
        self.launchProjectorsButton.clicked.connect(self.startProjectorsGui)
        self.lagSelectButton.clicked.connect(self.handle_choose_file_5lag)
        self.lagClearButton.clicked.connect(self.clear_5lag)

    def load_file(self, filename, maxChans = None):
        self._choose_file_lastdir = os.path.dirname(filename)
        if maxChans is None:
            maxChans = self.maxChansSpinBox.value()
        filenames = getOffFileListFromOneFile(filename, maxChans)
        self.basename, _ = mass.ljh_util.ljh_basename_channum(filename) #basename used later for external trigger
        self.filenames = filenames
        self.filename=filename
        self.data = ChannelGroup(filenames, verbose=True, excludeStates = self.excludeStates)
        #self.label_loadedChans.setText("loaded {} chans".format(len(self.data)))
        print("loaded {} chans".format(len(self.data)))

        self.fileTextBox.setText("Curret dataset: {}".format(self.data.shortName)) 
        
        self.channels = []
        for channum in self.data.keys():
            self.channels.append(channum)
            #self.refChannelBox.addItem("{}".format(channum))

        ### Setting parameters for the single-channel calibration as None.
        ### These will be sent back and forth between main window and the 1-channel cal window (or accessed directly) as needed.
        self.markersDict = None #dictionary of the plottable markers
        self.markerIndex = None #running total number of markers (including deleted ones)
        self.linesNames = None #list of autocal lines
        self.artistMarkersDict = None #basically the same as markersDict but in a different format
        self.autoFWHM = None
        self.maxacc = None
        self.channum = self.channels[0] #reference channel
        self.launch_channel_colors, self.launch_channel_states = None, None #info for the states grid
        

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
            self.loadCalButton.setEnabled(True) #once file is specified, a calibration can be loaded

    def handle_choose_file_5lag(self):
        if not hasattr(self, "_choose_file_lastdir"):
            dir = os.path.expanduser("~")
        else:
            dir = self._choose_file_lastdir
        fileName, _ = QFileDialog.getOpenFileName(
            self, "Find Pulse Model hdf5 file", dir,
            "hdf5 Files (*.hdf5);;All Files (*)")#, options=options)
        if fileName:
            try:
                self.lagFile = fileName
                self.lagTextBox.setText(self.lagFile) 
                with h5py.File(self.lagFile,"r") as h5:
                    models = {int(ch) : mass.pulse_model.PulseModel.fromHDF5(h5[ch]) for ch in h5.keys()}
                for channum, ds in self.data.items():
                    # define recipes for "filtValue5Lag", "peakX5Lag" and "cba5Lag"
                    # where cba refers to the coefficiencts of a polynomial fit to the 5 lags of the filter
                    filter_5lag = models[channum].f_5lag
                    ds.add5LagRecipes(filter_5lag)
                    # this data has artificial offsets of n*2**12 added to pretriggerMean by the phase unwrap algorithm used
                    # define a "pretriggerMeanCorrected" to remove these offsets
                    ds.recipes.add("pretriggerMeanCorrected", lambda pretriggerMean: pretriggerMean%2**12)
                self.enable5lag = True
            except Exception as exc:
                show_popup(self, "Failed to make 5lag filters!", traceback=traceback.format_exc())
                print("Failed to make 5lag filters!")
                print(traceback.format_exc())
                self.lagTextBox.setText('')
                self.enable5lag = False
                return
    def clear_5lag(self):
        self.lagTextBox.setText('')
        self.enable5lag = False

    def set_std_dev_threshold(self):
        for ds in self.data.values():
            ds.stdDevResThreshold = 1000

    def handle_manual_cal(self):
        # log.debug("handle_manual_cal")
        self.launch_channel(self.data, self.channum)

   
    def launch_channel(self, data, channum):
        self.checkHCI()
        self.plotsGroup.setEnabled(False)
        self.fileSelectionGroup.setEnabled(False)
        self.hc = HistCalibrator(self) 
        self.hc.setParams(self, data, channum, data[channum].stateLabels, binSize=50, 
                          statesConfig=self.launch_channel_states, markers=self.markersDict, artistMarkers=self.artistMarkersDict, 
                          markersIndex=self.markerIndex, linesNames=self.linesNames, autoFWHM=self.autoFWHM, maxacc=self.maxacc, enable5lag=self.enable5lag)
        tableData = self.getcalTableRows()
        self.hc.importTableRows(tableData)
        self.hc.PCcheckbox.setChecked(self.PCcheckbox.isChecked())
        self.hc.DCcheckbox.setChecked(self.DCcheckbox.isChecked())
        self.hc.TDCcheckbox.setChecked(self.TDCcheckbox.isChecked())
        self.hc.Acheckbox.setChecked(self.Acheckbox.isChecked())
        self.hc.dlo_dhiBox.setValue(self.dlo_dhiBox.value())
        self.hc.calBinBox.setValue(self.binSizeBox.value())
        self.hc.autoListOfLines.setText(self.autoListOfLines.toPlainText())

        #hc.setWindowModality(self, QtCore.Qt.ApplicationModal)
        self._selected_window = self.hc
        self.hc.exec()
        self.calibrationGroup.setEnabled(True)
        self.get_data_from_channel(data)


    def get_data_from_channel(self, data): #grabs calibration info from the single channel cal window
        self.setChannum()
        self.ds = data[self.channum]
        self.cal_info = self.hc.getTableRows()
        self.launch_channel_colors, self.launch_channel_states = self.hc.histHistViewer.statesGrid.get_colors_and_states_list()
        
        self.markersDict = self.hc.markersDict
        self.artistMarkersDict = self.hc.artistMarkersDict
        self.markerIndex = self.hc.markerIndex
        self.linesNames = self.hc.linesNames
        self.autoFWHM = self.hc.autoFWHMBox.value()
        self.maxacc = self.hc.autoMaxAccBox.value()
        self.PCcheckbox.setChecked(self.hc.PCcheckbox.isChecked())
        self.DCcheckbox.setChecked(self.hc.DCcheckbox.isChecked())
        self.TDCcheckbox.setChecked(self.hc.TDCcheckbox.isChecked())
        self.Acheckbox.setChecked(self.hc.Acheckbox.isChecked())
        self.dlo_dhiBox.setValue(self.hc.dlo_dhiBox.value())
        self.binSizeBox.setValue(self.hc.calBinBox.value())
        self.autoFWHMBox.setValue(self.hc.autoFWHMBox.value())
        self.autoMaxAccBox.setValue(self.hc.autoMaxAccBox.value())
        self.clear_table()
        self.importTableRows()
        self.importAutoList()
        if self.calibratedChannels == {self.ds.channum}:
            self.plotsGroup.setEnabled(True)
            self.qualityButton.setEnabled(False)
        self._cal_stage = 0 #Deprecated: _cal_stage tracks the most recent calibration activity. 0=cal plan made; 1=single channel calibration done; 2=all channel calibration
                            #I use _cal_stage so I know when I need to reload the self.data object (to switch between single and all channel calibration)


    def importAutoList(self):
        self.autoListOfLines.clear()
        self.autoListOfLines.setText(self.hc.autoListOfLines.toPlainText())
        if self.linesNames != None:
            if len(self.linesNames) >= 1:
                self.allChanAutoCalButton.setEnabled(True)

    def initCal(self):
        #self.data = self.data_no_cal
        try:
            self.data = ChannelGroup(self.filenames, verbose=True, excludeStates = self.excludeStates)
            self.set_std_dev_threshold()
            self.pb.addText("Learning standard deviation cut... \n")
            QtWidgets.QApplication.instance().processEvents
            self.data.learnResidualStdDevCut()
            self.pb.nextValue()
            QtWidgets.QApplication.instance().processEvents
            self.ds = self.data[self.channum]
            if self.enable5lag:
                self.init5lag()
                self.fvAttr = 'filtValue5Lag'
                self.ptmAttr = 'pretriggerMeanCorrected'
            else:
                self.fvAttr = 'filtValue'
                self.ptmAttr = 'pretriggerMean'   
            self.ds.calibrationPlanInit(self.fvAttr)
        
            for (states, fv, line, energy) in self.cal_info: 
                # # log.debug(f"states {states}, fv {fv}, line {line}, energy {energy}")
                if line != 'Manual Energy':
                    self.ds.calibrationPlanAddPoint(float(fv), line, states=states.split(","))
                elif energy:
                    self.ds.calibrationPlanAddPoint(float(fv), energy, states=states.split(","), energy=float(energy))
                # elif line in mass.spectra.keys() and energy:
                #     self.ds.calibrationPlanAddPoint(float(fv), line, states=states.split(","), energy=float(energy))
        except Exception as exc:
            show_popup(self, "Failed to align to reference channel!", traceback=traceback.format_exc())
            print("Failed to align to reference channel!")
            print(traceback.format_exc())
            return
        self.data.referenceDs = self.ds
        # log.debug(f"{ds.calibrationPlan}")
        self.plotsGroup.setEnabled(True) 

    def init5lag(self):
        with h5py.File(self.lagFile,"r") as h5:
            models = {int(ch) : mass.pulse_model.PulseModel.fromHDF5(h5[ch]) for ch in h5.keys()}
        for channum, ds in self.data.items():
            # define recipes for "filtValue5Lag", "peakX5Lag" and "cba5Lag"
            # where cba refers to the coefficiencts of a polynomial fit to the 5 lags of the filter
            filter_5lag = models[channum].f_5lag
            ds.add5LagRecipes(filter_5lag)
            # this data has artificial offsets of n*2**12 added to pretriggerMean by the phase unwrap algorithm used
            # define a "pretriggerMeanCorrected" to remove these offsets
            ds.recipes.add("pretriggerMeanCorrected", lambda pretriggerMean: pretriggerMean%2**12)

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
        self.allChanCalButton.setEnabled(False)
        self.allChanAutoCalButton.setEnabled(False)
        self.plotsGroup.setEnabled(False)
        self.saveCalButton.setEnabled(False)
        self.markersDict = None
        self.artistMarkersDict = None
        self.markerIndex = 0
        self.linesNames = None
        self.clear_table()
        self.data = ChannelGroup(self.filenames, verbose=True, excludeStates = self.excludeStates) #marks channels good, removes recipes

    def get_line_names(self):
        if self.self.HCIonCheckbox.isChecked()==True:       #optional import of highly charged ions to the dropdown. Does not work now.
            from mass.calibration import _highly_charged_ion_lines
            import mass.calibration.hci_models
        self.LinesDict=list(mass.spectra.keys()) 

    def clear_table(self):
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
        self.highestFV = 0.
        #self.lineFitComboBox.clear()
        for i in range(len(self.cal_info)):
            rowPosition = self.calTable.rowCount()
            rowData = self.cal_info[i] #data looks like [state, filtVal, name, energy]
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
            self.highestFV = max(self.highestFV, float(rowData[1]))

        self.calButtonGroup.setEnabled(True)
        if rowPosition != None and allowCal == True: #if something is added to the calibration plan and each line has a name, let user calibrate. 
            self.allChanCalButton.setEnabled(True)
        else:   #if nothing is added OR if a line isn't identified, stop the user from calibrating.
            self.allChanCalButton.setEnabled(False)


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

    def allChannelCalibration(self):
        dlo_dhi = self.getDloDhi()
        binsize=self.getBinsizeCal()
        steps = 3 # init, align, and calibrate are the only two steps that are always used
        if self.PCcheckbox.isChecked():
            steps+=1
        if self.DCcheckbox.isChecked():
            steps+=1
        if self.TDCcheckbox.isChecked():
            steps+=1

        self.pb = progressPopup(self)
        self.pb.setParams(steps)
        self.pb.show()
        app = QtWidgets.QApplication.instance()
        app.processEvents()

        self.initCal()

        try:
            self.pb.addText("Aligning channels... \n")
            app.processEvents()
            self.data.alignToReferenceChannel(referenceChannel=self.ds, binEdges=np.arange(0,35000,10), attr=self.fvAttr, states=self.ds.stateLabels)
            self.pb.nextValue()
            app.processEvents()
        except Exception as exc:
            print("Failed to align to reference channel!")
            print(traceback.format_exc())
            show_popup(self, "Failed to align to reference channel!", traceback=traceback.format_exc())
            return
        self.newestName = self.fvAttr
        try:
            if self.PCcheckbox.isChecked():
                uncorr = self.newestName
                self.newestName+="PC"
                self.pb.addText("Starting phase correction... \n")
                app.processEvents()
                self.data.learnPhaseCorrection(indicatorName="filtPhase", uncorrectedName=uncorr, correctedName = self.newestName, states=self.ds.stateLabels, overwriteRecipe=True)
                self.pb.nextValue()
                app.processEvents()
        
            if self.DCcheckbox.isChecked():
                uncorr = self.newestName
                self.newestName+="DC"
                self.pb.addText("Starting drift correction... \n")
                app.processEvents()
                self.data.learnDriftCorrection(indicatorName=self.ptmAttr, uncorrectedName=uncorr, correctedName = self.newestName, states=self.ds.stateLabels, overwriteRecipe=True)#, cutRecipeName="cutForLearnDC")
                self.pb.nextValue()
                app.processEvents()

            if self.TDCcheckbox.isChecked():
                uncorr = self.newestName
                self.newestName+="TC"
                self.pb.addText("Starting time drift correction")
                app.processEvents()
                self.data.learnTimeDriftCorrection(indicatorName="relTimeSec", uncorrectedName=uncorr, correctedName = self.newestName, states=self.ds.stateLabels, overwriteRecipe=True)#,cutRecipeName="cutForLearnDC", _rethrow=True) 
                self.pb.nextValue()
                app.processEvents()
            
        except Exception as exc:
            print("exception in all channel calibration")
            print(traceback.format_exc())
            show_popup(self, "Failed all-channel calibration!", traceback=traceback.format_exc())
            pass
        
        try:
            self.pb.addText("Calibrating...")
            app.processEvents()
            self.data.calibrateFollowingPlan(self.newestName, dlo=dlo_dhi,dhi=dlo_dhi, binsize=binsize, _rethrow=True, overwriteRecipe=True, approximate=self.Acheckbox.isChecked())
            self.pb.nextValue()
            app.processEvents()
            # self.saveCalButton.setEnabled(True)
            self.qualityButton.setEnabled(True)
            self.calibratedChannels.update(self.data.keys())
            print(f'Calibrated {len(self.data.values())} channels using reference channel {self.ds.channum}')
            self.pb.close()
        except Exception as exc:
            print("Failed to calibrate following plan!")
            print(traceback.format_exc())
            show_popup(self, "Failed to calibrate following plan!", traceback=traceback.format_exc())
            return



    def allChannelAutoCalibration(self):
        dlo_dhi = self.getDloDhi()
        binsize=self.getBinsizeCal()
        states = self.launch_channel_states[0]
        linesNames = self.linesNames # self.autoListOfLines.toPlainText()
        try:
            autoFWHM = float(self.autoFWHMBox.value())
        except:
            print("failed to get autoFWHM")
            return

        try:
            maxacc = float(self.autoMaxAccBox.value())
        except:
            print("failed to get Max Acc")  
            return 
        self.data = ChannelGroup(self.filenames, verbose=True, excludeStates = self.excludeStates)
        self.set_std_dev_threshold()
        self.data.learnResidualStdDevCut()
        self.ds = self.data[self.channum]
        self.data.referenceDs = self.ds
        # log.debug(f"{ds.calibrationPlan}")
        self.plotsGroup.setEnabled(True) 
        # print(states, autoFWHM, linesNames, maxacc)
        # print(type(linesNames))
        if self.enable5lag:
            self.init5lag()
            self.fvAttr = 'filtValue5Lag'
            self.ptmAttr = 'pretriggerMeanCorrected'
        else:
            self.fvAttr = 'filtValue'
            self.ptmAttr = 'pretriggerMean'   
        self.ds.calibrationPlanInit(self.fvAttr)

        try:
            self.ds.learnCalibrationPlanFromEnergiesAndPeaks(self.fvAttr, states=states, ph_fwhm=autoFWHM, line_names=linesNames, maxacc=maxacc)
            self.data.alignToReferenceChannel(referenceChannel=self.ds, binEdges=np.arange(0,35000,10), attr=self.fvAttr, states=self.ds.stateLabels)
            self.newestName = self.fvAttr
        except Exception as exc:
            print(traceback.format_exc())
            print("failed to learn autocal")
            show_popup(self, "Failed automatic calibration!", traceback.format_exc())
            return
        try:
            if self.PCcheckbox.isChecked():
                uncorr = self.newestName
                self.newestName+="PC"
                self.data.learnPhaseCorrection(indicatorName="filtPhase", uncorrectedName=uncorr, correctedName = self.newestName, states=self.ds.stateLabels, overwriteRecipe=True)
        
            if self.DCcheckbox.isChecked():
                uncorr = self.newestName
                self.newestName+="DC"
                self.data.learnDriftCorrection(indicatorName="pretriggerMean", uncorrectedName=uncorr, correctedName = self.newestName, states=self.ds.stateLabels, overwriteRecipe=True)#, cutRecipeName="cutForLearnDC")

            if self.TDCcheckbox.isChecked():
                uncorr = self.newestName
                self.newestName+="TC"
                self.data.learnTimeDriftCorrection(indicatorName="relTimeSec", uncorrectedName=uncorr, correctedName = self.newestName, states=self.ds.stateLabels, overwriteRecipe=True)#,cutRecipeName="cutForLearnDC", _rethrow=True) 
            print(f'Calibrated {len(self.data.values())} channels using reference channel {self.ds.channum}')
        except Exception as exc:
            print("exception in all channel calibration")
            print(traceback.format_exc())
            show_popup(self, "Exception in all-channel calibration", traceback.format_exc())
            pass

        try:
            self.data.calibrateFollowingPlan(self.newestName, dlo=dlo_dhi,dhi=dlo_dhi, binsize=binsize, _rethrow=True, overwriteRecipe=True, approximate=self.Acheckbox.isChecked())
        except Exception as exc:
            print("Failed to calibrate following plan!")
            print(traceback.format_exc())
            show_popup(self, "Failed to calibrate following plan!", traceback.format_exc())
            return
        self.saveCalButton.setEnabled(True)
        self.qualityButton.setEnabled(True)
        self.calibratedChannels.update(self.data.keys())


    def getDloDhi(self):
        return float(self.dlo_dhiBox.text())/2.0 #whole energy range is dlo+dhi, so divide by 2 to get them individually
    
    def getBinsizeCal(self):
        return float(self.binSizeBox.text())
    
    def viewEnergyPlot(self):
        plotter = HistPlotter(self)
        self._selected_window = plotter
        plotter.setParams(self, self.data, self.ds.channum, "energy", self.ds.stateLabels, binSize=self.getBinsizeCal())
        plotter.show()

    def diagnoseCalibration(self):
        self.plotter = diagnoseViewer(self)
        self.plotter.setParams(self, self.data, self.ds.channum, highestFV = self.highestFV)
        self.plotter.show()


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

        #coefs is a list of three attributes: pulseMean, derivativeLike, and filtValue. We should be viewing them individually, so I don't include coefs here.
        try:
            keys.remove('coefs')         
        except:
            pass
        if type == "1D":
            self.AvsBsetup = AvsBSetup(self) 
            #print(self.data.keys())
            self.AvsBsetup.setParams(self, keys, self.ds.stateLabels, self.data.keys(), self.data, mode = "1D")
            self.AvsBsetup.show()
        if type == "2D":
            self.AvsBsetup = AvsBSetup(self) 
            self.AvsBsetup.setParams(self, keys, self.ds.stateLabels, self.data.keys(), self.data, mode = "2D")
            self.AvsBsetup.show()

    def handleExternalTrigger(self):
        if not os.path.isfile(os.path.join(f"{self.basename}_external_trigger.bin")):
            print("Error: No external trigger file found in ",self.basename)
            show_popup(self, f"Error: No external trigger file found in {self.basename}")
            return

        self.ETsetup = ExternalTriggerSetup(self) 
        self.ETsetup.setParams(self, self.data.stateLabels, self.data.keys(), self.data, self.basename)
        self.ETsetup.show()


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
        self.lfsetup.dlo.setValue(self.getDloDhi())
        self.lfsetup.dhi.setValue(self.getDloDhi())
        self.lfsetup.binSizeBox.setValue(self.getBinsizeCal())
        self.lfsetup.show()

    def startQualityCheck(self):
        self.goodChannels = self.data.keys()
        self.qcsetup = qualityCheckLinefitSetup(self) 
        lines = list(mass.spectra.keys())
        self.qcsetup.setParams(self, lines, states_list=self.ds.stateLabels, data=self.data)
        self.qcsetup.show()  
          
    def startROIRTP(self):
        self.ROIRTPsetup = RoiRtpSetup(self) 
        self.ROIRTPsetup.setParams(self, self.data, self.ds.channum, state_labels=self.ds.stateLabels)
        self.ROIRTPsetup.show()

    def readNewFilesAndStates(self):
        try:
            self.data.refreshFromFiles()
        except:
            self.data.markAllGood() #if all channels somehow get marked bad, refresh will fail
            self.data.refreshFromFiles()

    def startProjectorsGui(self):
        self.pj = projectorsGui()
        self.pj.show()


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
    try:
        retval = app.exec() 
    except Exception:
        import pdb; pdb.post_mortem() #doesn't work

# #https://www.youtube.com/watch?v=WjctCBjHvmA
# http://adambemski.pythonanywhere.com/testing-qt-application-python-and-pytest
