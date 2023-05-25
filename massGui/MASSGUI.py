import PyQt5.QtWidgets as QtWidgets
import PyQt5 
import mass

def main():
    app = qt.QApplication([])
    label = qt.QLabel("Hello")
    label.show()

    #button.clicked.connect(on_button_clicked)
    #os.path.join(os.path.dirname(__file__), ... )

    #def selectFile():
    #   lineEdit.setText(QFileDialog.getOpenFileName())

    app.exec_()


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.data = None 
        self.build()
        self.connect()

    def build(self):
        PyQt5.uic.loadUi(os.path.join(os.path.dirname(__file__), "ui/mainwindow.ui"), self)

    def connect(self):
        self.pushButton_chooseFile.clicked.connect(self.handle_choose_file)
        self.pushButton_manualCal.clicked.connect(self.handle_manual_cal)
        self.pushButton_align.clicked.connect(self.handle_align)
        self.pushButton_calibrate.clicked.connect(self.handle_calibrate)
        self.pushButton_plotEnergy.clicked.connect(self.handle_plot)
        self.pushButton_refresh.clicked.connect(self.handle_refresh)

    def load_file(self, filename, maxChans = None):
        self._choose_file_lastdir = os.path.dirname(filename)
        if maxChans is None:
            maxChans = self.spinBox_maxChans.value()
        filenames = getOffFileListFromOneFile(filename, maxChans)
        self.data = ChannelGroup(filenames, verbose=False)
        self.label_loadedChans.setText("loaded {} chans".format(len(self.data)))
        self.label_chosenFile.setText("Curret dataset: {}".format(self.data.shortName)) 
        for channum in self.data.keys():
            self.comboBox_refChannel.addItem("{}".format(channum))