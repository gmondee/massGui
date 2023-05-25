import PyQt5.QtWidgets as QtWidgets
import PyQt5.uic
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QSettings, pyqtSlot
from PyQt5.QtWidgets import QFileDialog
import sys
import os


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
        QtWidgets.QWidget.__init__(self)
        self.data = None 
        self.build()
        self.connect()

    def build(self):
        PyQt5.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/massGui.ui"), self)

    def connect(self):
        self.selectFileButton.clicked.connect(self.handle_choose_file)
        self.pushButton_manualCal.clicked.connect(self.handle_manual_cal)
        self.pushButton_align.clicked.connect(self.handle_align)
        self.pushButton_calibrate.clicked.connect(self.handle_calibrate)
        self.pushButton_plotEnergy.clicked.connect(self.handle_plot)
        self.pushButton_refresh.clicked.connect(self.handle_refresh)

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