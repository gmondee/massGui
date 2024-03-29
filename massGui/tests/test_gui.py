import pytest
# import PyQt6.QtWidgets as QtWidgets
# import PyQt6.uic
from PyQt6 import QtCore, QtGui, QtWidgets, QtTest
import PyQt6
# from PyQt6.QtCore import QSettings, pyqtSlot
# from PyQt6.QtWidgets import QFileDialog
import sys
import os
import massGui
#import massGui.massGui
#import logging
from .offWriterTests import main as offWriterTests
import threading
import time
import matplotlib.pyplot as plt

def OffWriterThread():
    offWriterTests() #start writing the off files

offThread = threading.Thread(target=OffWriterThread, daemon=True)
basedir = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture
def app(qtbot):
    
    test_gui_app = massGui.massGui.MainWindow()
    qtbot.addWidget(test_gui_app)

    return test_gui_app

@pytest.mark.timeout(3)
def test_open(app):
    assert app.selectFileButton.text()=="Select .OFF File"

@pytest.mark.timeout(20)
def test_cal(app, qtbot):
    offThread.start()
    time.sleep(5)
    # logging.basicConfig(filename='testLog.txt',
    #                     filemode='a',
    #                     format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    #                     datefmt='%H:%M:%S',
    #                     level=logging.DEBUG)

    # logging.info("Test Log")
    # log = logging.getLogger("test_gui")
    # log.debug(f"made log")


    def manual_cal():
        #qtbot.waitUntil(lambda: isinstance(app._selected_window, massGui.massless.HistCalibrator))
        hc = app._selected_window#QtWidgets.QApplication.activeWindow()#app.hc
        qtbot.addWidget(hc)
        assert isinstance(hc, massGui.massless.HistCalibrator) #exists but not clicking on it
        mock_cal(hc)
        #qtbot.mouseClick(hc.closeButton, QtCore.Qt.MouseButton.LeftButton)
        hc.reject()
        qtbot.done_man_cal = 1

    def mock_cal(hc): #adds elements to the table instead of clicking. couldn't get clicking to work.
        hc.table.setRowCount(2)
        hc.table.setItem(0, 0, QtWidgets.QTableWidgetItem("A"))
        hc.table.setItem(0, 1, QtWidgets.QTableWidgetItem("6015.0"))
        #hc.table.setItem(0, 2, QtWidgets.QTableWidgetItem("AlKAlpha"))
        hc.table.setItem(0, 3, QtWidgets.QTableWidgetItem(""))
        cbox = QtWidgets.QComboBox()
        cbox.addItem("AlKAlpha")
        hc.table.setCellWidget(0, 2, cbox)
        hc.table.setItem(1, 0, QtWidgets.QTableWidgetItem("A"))
        hc.table.setItem(1, 1, QtWidgets.QTableWidgetItem("6995.0"))
        #hc.table.setItem(1, 2, QtWidgets.QTableWidgetItem("SiKAlpha"))     
        hc.table.setItem(1, 3, QtWidgets.QTableWidgetItem(""))
        cbox = QtWidgets.QComboBox()
        cbox.addItem("SiKAlpha")
        hc.table.setCellWidget(1, 2, cbox)   


    def cal_opened():
        plotter = app._selected_window
        assert isinstance(plotter, massGui.massless.HistCalibrator)
        qtbot.addWidget(plotter)
        assert plotter.eRangeLow.value() == 0
        print(f'{plotter.parent.ds.statesDict}')
        qtbot.done_cal_open = 1
        plotter.close()


    app.maxChansSpinBox.setValue(2)
    assert app.maxChansSpinBox.value() == 2

    #manual bypass of file loading dialog
    app.load_file(os.path.join(basedir,r"DataForTests", r"20200107_Realtime", r"20200107_run0002_chan1.off"))
    app.set_std_dev_threshold()
    app.calibrationGroup.setEnabled(True)
    app.calButtonGroup.setEnabled(False)

    qtbot.done_man_cal = 1
    QtCore.QTimer.singleShot(1000, manual_cal)
    qtbot.mouseClick(app.lineIDButton, QtCore.Qt.MouseButton.LeftButton)

    assert app.calTable.item(0, 0).text() == "AlKAlpha"

    qtbot.done_cal_open = 0
    app.DCcheckbox.setChecked(0)
    app.PCcheckbox.setChecked(0)
    app.TDCcheckbox.setChecked(0)

    QtCore.QTimer.singleShot(1000, cal_opened)
    qtbot.mouseClick(app.allChanCalButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: qtbot.done_cal_open == 1, timeout = 1000)

    ###Test Real-time plotter
    qtbot.mouseClick(app.startRTPButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.addWidget(app.plotter)
    assert app.plotter.eRangeHi.value() == 10000
    ax = app.plotter.energyAxis
    assert 'run0002' in ax.title.get_text()
    assert ax.has_data()
    #qtbot.stop()
    #app.plotter.close()

    ###Test AvsB2d plotting
    plt.close() #hack to avoid multithreading. the plot created will block the rest of the code in plt.ioff.
    plt.ion()
    qtbot.mouseClick(app.AvsB2Dbutton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.addWidget(app.AvsBsetup)
    qtbot.mouseClick(app.AvsBsetup.plotButton, QtCore.Qt.MouseButton.LeftButton)  
    assert '2 chans' in ax.title.get_text()
    assert app.AvsBsetup.zoomPlot.ax.has_data()
    plt.close()

    ###Test AvsB (1D) plotting
    qtbot.mouseClick(app.ptmButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.addWidget(app.AvsBsetup)
    qtbot.mouseClick(app.AvsBsetup.plotButton, QtCore.Qt.MouseButton.LeftButton) 
    ax = plt.gca()
    assert ax.has_data()
    assert 'cutRecipeName' in ax.title.get_text()
    plt.close()
    app.AvsBsetup.close()

    ###Test linefit plotting
    qtbot.mouseClick(app.linefitButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.addWidget(app.lfsetup)
    app.lfsetup.lineBox.setCurrentText('AlKAlpha')
    qtbot.mouseClick(app.lfsetup.plotButton, QtCore.Qt.MouseButton.LeftButton)
    ax = plt.gca()
    assert ax.has_data()
    assert 'AlKAlpha' in ax.title.get_text()
    plt.close()
    app.plotter.close()
    app.lfsetup.close()


    #qtbot.mouseClick(app.saveCalButton, QtCore.Qt.MouseButton.LeftButton)
    #qtbot.mouseClick(app.loadCalButton, QtCore.Qt.MouseButton.LeftButton)
    #qtbot.addWidget(app.hdf5Opener)

    ###Test external trigger plot
    qtbot.mouseClick(app.extTrigButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.addWidget(app.ETsetup)
    qtbot.mouseClick(app.ETsetup.plotButton, QtCore.Qt.MouseButton.LeftButton)
    ax = plt.gca()
    assert 'channels' in ax.title.get_text()
    assert ax.has_data()
    plt.close()
    app.ETsetup.close()

    ###Test ds.diagnoseCalibration plot
    qtbot.mouseClick(app.diagCalButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.addWidget(app.plotter)
    ax = plt.gca()
    #qtbot.stop()
    assert 'chan1' in ax.title.get_text()
    assert ax.has_data()
    plt.close()
    app.plotter.close()

    ###Test energy histogram plot
    qtbot.mouseClick(app.energyHistButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.addWidget(app._selected_window)
    ax = plt.gca()
    assert 'run0002' in ax.title.get_text()
    assert ax.has_data()
    #plt.close()
    app._selected_window.close()

    ###Test quality check linefit plot
    qtbot.mouseClick(app.qualityButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.addWidget(app.qcsetup)
    ax = plt.gca()
    assert ax.has_data()
    assert 'chan1' in ax.title.get_text()
    plt.close()
    app.qcsetup.close()

    ###Test real-time regions of interest plot
    qtbot.mouseClick(app.startROIRTPButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.addWidget(app.ROIRTPsetup)
    app.ROIRTPsetup.linesBox.setCurrentText('AlKAlpha')
    qtbot.mouseClick(app.ROIRTPsetup.addButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.mouseClick(app.ROIRTPsetup.startRTPButton, QtCore.Qt.MouseButton.LeftButton)
    ax = plt.gca()
    assert ax.has_data()
    assert 'Channels' in ax.title.get_text()
    plt.close()
    #app.ROIRTPsetup.close() 



def runOpen():
    sys.exit(pytest.main(args=massGui.__path__))

# if __name__=="__main__":
#     sys.exit(pytest.main(args=massGui.__path__))

