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
import logging




@pytest.fixture
def app(qtbot):
    
    test_gui_app = massGui.massGui.MainWindow()
    qtbot.addWidget(test_gui_app)

    return test_gui_app

def test_open(app):
    assert app.selectFileButton.text()=="Select .OFF File"

@pytest.mark.timeout(200)
def test_cal(app, qtbot):
    logging.basicConfig(filename='testLog.txt',
                        filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.DEBUG)

    logging.info("Test Log")
    log = logging.getLogger("test_gui")
    log.debug(f"made log")


    def manual_cal():
        #assert 1 == 0
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
        hc.table.setItem(0, 0, QtWidgets.QTableWidgetItem("D"))
        hc.table.setItem(0, 1, QtWidgets.QTableWidgetItem("6015.0"))
        #hc.table.setItem(0, 2, QtWidgets.QTableWidgetItem("AlKAlpha"))
        hc.table.setItem(0, 3, QtWidgets.QTableWidgetItem(""))
        cbox = QtWidgets.QComboBox()
        cbox.addItem("AlKAlpha")
        hc.table.setCellWidget(0, 2, cbox)
        hc.table.setItem(1, 0, QtWidgets.QTableWidgetItem("D"))
        hc.table.setItem(1, 1, QtWidgets.QTableWidgetItem("6995.0"))
        #hc.table.setItem(1, 2, QtWidgets.QTableWidgetItem("SiKAlpha"))     
        hc.table.setItem(1, 3, QtWidgets.QTableWidgetItem(""))
        cbox = QtWidgets.QComboBox()
        cbox.addItem("SiKAlpha")
        hc.table.setCellWidget(1, 2, cbox)   


    def cal_opened():
        plotter = app._selected_window
        #assert isinstance(plotter, massGui.massless.HistPlotter)
        qtbot.addWidget(plotter)
        assert plotter.eRangeLow.value() == 0
        qtbot.done_cal_open = 1
        plotter.close()


    app.maxChansSpinBox.setValue(2)
    assert app.maxChansSpinBox.value() == 2

    #manual bypass of file loading dialog
    app.load_file(r'C:\Users\Grant Mondeel\Box\my EUV\tes\realtime\realtime\Summer2022\20200107\0002\20200107_run0002_chan1.off')
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

    # qtbot.mouseClick(app.startRTPButton, QtCore.Qt.MouseButton.LeftButton)
    # qtbot.addWidget(app.plotter)

    # qtbot.mouseClick(app.AvsB2Dbutton, QtCore.Qt.MouseButton.LeftButton)
    # qtbot.addWidget(app.AvsBsetup)

    # qtbot.mouseClick(app.ptmButton, QtCore.Qt.MouseButton.LeftButton)
    # qtbot.addWidget(app.AvsBsetup)

    # qtbot.mouseClick(app.linefitButton, QtCore.Qt.MouseButton.LeftButton)
    # qtbot.addWidget(app.lfsetup)

    #qtbot.mouseClick(app.saveCalButton, QtCore.Qt.MouseButton.LeftButton)
    #qtbot.mouseClick(app.loadCalButton, QtCore.Qt.MouseButton.LeftButton)
    #qtbot.addWidget(app.hdf5Opener)

    # qtbot.mouseClick(app.extTrigButton, QtCore.Qt.MouseButton.LeftButton)
    # qtbot.addWidget(app.ETsetup)

    # qtbot.mouseClick(app.diagCalButton, QtCore.Qt.MouseButton.LeftButton)
    # qtbot.addWidget(app.plotter)

    #qtbot.mouseClick(app.energyHistButton, QtCore.Qt.MouseButton.LeftButton)
    ##qtbot.addWidget(app.plotter)

    # qtbot.mouseClick(app.qualityButton, QtCore.Qt.MouseButton.LeftButton)
    # qtbot.addWidget(app.qcsetup)

    qtbot.mouseClick(app.startROIRTPButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.addWidget(app.ROIRTPsetup)

    qtbot.stop()
    
    
def test_realtime(app, qtbot):
    logging.basicConfig(filename='testLog.txt',
                        filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.DEBUG)

    logging.info("Test Log")
    log = logging.getLogger("test_gui")
    log.debug(f"made log")


    def manual_cal():
        #assert 1 == 0
        #qtbot.waitUntil(lambda: isinstance(app._selected_window, massGui.massless.HistCalibrator))
        hc = app._selected_window#QtWidgets.QApplication.activeWindow()#app.hc
        qtbot.addWidget(hc)
        assert isinstance(hc, massGui.massless.HistCalibrator) #exists but not clicking on it
        #QtGui.QMouseEvent(QtCore.QEvent)
        #qtbot.mouseClick(hc.histHistViewer.canvas, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(379, 225))
        #qtbot.mouseClick(hc, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(411, 106))
        #QtTest.QTest.mouseClick(hc.histHistViewer, QtCore.Qt.MouseButton.LeftButton ,pos=QtCore.QPoint(379, 225))
        
        #qtbot.keyClicks(hc.table.item(0,2), "AlKAlpha")
        #assert hc.table.item(0, 0).text() == "D"
        #assert 1 == 0
        #qtbot.keyClicks(hc.table.item(0,2), "SiKAlpha")

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
        #assert isinstance(plotter, massGui.massless.HistPlotter)
        qtbot.addWidget(plotter)
        assert plotter.eRangeLow.value() == 0
        qtbot.done_cal_open = 1
        plotter.close()


    app.maxChansSpinBox.setValue(2)
    assert app.maxChansSpinBox.value() == 2

    #manual bypass of file loading dialog
    app.load_file(r"C:\Users\Grant Mondeel\Box\my EUV\tes\realtime\realtime\Data\FakeData\20200107_fake\20200107_run0002_chan1.off") # sets self._choose_file_lastdir
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

    # qtbot.mouseClick(app.startRTPButton, QtCore.Qt.MouseButton.LeftButton)
    # qtbot.addWidget(app.plotter)

    # qtbot.mouseClick(app.AvsB2Dbutton, QtCore.Qt.MouseButton.LeftButton)
    # qtbot.addWidget(app.AvsBsetup)

    # qtbot.mouseClick(app.ptmButton, QtCore.Qt.MouseButton.LeftButton)
    # qtbot.addWidget(app.AvsBsetup)

    # qtbot.mouseClick(app.linefitButton, QtCore.Qt.MouseButton.LeftButton)
    # qtbot.addWidget(app.lfsetup)

    #qtbot.mouseClick(app.saveCalButton, QtCore.Qt.MouseButton.LeftButton)
    #qtbot.mouseClick(app.loadCalButton, QtCore.Qt.MouseButton.LeftButton)
    #qtbot.addWidget(app.hdf5Opener)

    qtbot.mouseClick(app.extTrigButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.addWidget(app.ETsetup)

    qtbot.stop()



def runOpen():
    sys.exit(pytest.main(args=massGui.__path__))

# if __name__=="__main__":
#     sys.exit(pytest.main(args=massGui.__path__))

