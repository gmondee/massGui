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
        # self.pushButton_align.clicked.connect(self.handle_align)
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
        for channum in self.data.keys():
            self.refChannelComboBox.addItem("{}".format(channum))

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
        channum = int(self.refChannelComboBox.currentText())
        self.launch_channel(self.data[channum])

    def launch_channel(self, ds):
        hc = HistCalibrator(self, ds, "filtValue", ds.stateLabels) 
        hc.setParams(ds, "filtValue", ds.stateLabels)
        #hc.setWindowModality(self, QtCore.Qt.ApplicationModal)
        hc.exec_()

        cal_info = hc.getTableRows()
        # log.debug(f"hc dict {cal_info}")
        self.label_calStatus.setText("{}".format(cal_info))
        ds.calibrationPlanInit("filtValue")
        for (states, fv, line, energy) in cal_info: 
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
        self.table.setRowCount(0)

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

def main(test=False):
    app = QtWidgets.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    # if test:
    #     mw.load_file("/Users/oneilg/mass/src/mass/off/data_for_test/20181205_BCDEFGHI/20181205_BCDEFGHI_chan1.off")
    #     mw.set_std_dev_threshold()
    #     mw.launch_channel(mw.data.firstGoodChannel())
    retval = app.exec_() 


# @pytest.fixture()
# def mybot():
#     pass

# def test():
#     pytestqt.qt_compat.qt_api.set_qt_api('pyqt5')

#     app=QtWidgets.QApplication(sys.argv)
#     widget = MainWindow()
#     widget.show()

#     QtBot.addWidget(, widget)
#     QtBot.mouseClick(widget.selectFileButton, QtCore.Qt.LeftButton)

# #https://www.youtube.com/watch?v=WjctCBjHvmA
# http://adambemski.pythonanywhere.com/testing-qt-application-python-and-pytest

# # if __name__ == '__main__':
# #     main()