import pytest

# import PyQt5.QtWidgets as QtWidgets
# import PyQt5.uic
from PyQt5 import QtCore, QtGui, QtWidgets, QtTest
import PyQt5
# from PyQt5.QtCore import QSettings, pyqtSlot
# from PyQt5.QtWidgets import QFileDialog
import sys
import os
import massGui
#import massGui.massGui
import logging




@pytest.fixture
def app(qtbot):
    logging.basicConfig(filename='testLog.txt',
                        filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.DEBUG)

    logging.info("Test Log")
    log = logging.getLogger("test_gui")
    log.debug(f"made log")
    test_gui_app = massGui.massGui.MainWindow()
    qtbot.addWidget(test_gui_app)

    return test_gui_app

def test_open(app):
    assert app.selectFileButton.text()=="Select .OFF File"

def test_cal(app, qtbot):

    def manual_cal():
        #assert 1 == 0
        #qtbot.waitUntil(lambda: isinstance(app._selected_window, massGui.massless.HistCalibrator))
        hc = app._selected_window#QtWidgets.QApplication.activeWindow()#app.hc
        qtbot.addWidget(hc)
        assert isinstance(hc, massGui.massless.HistCalibrator) #exists but not clicking on it
        
        qtbot.mouseClick(hc.histHistViewer, QtCore.Qt.LeftButton, pos=QtCore.QPoint(554, 177))
        qtbot.mouseClick(hc, QtCore.Qt.LeftButton, pos=QtCore.QPoint(604, 112))
        qtbot.keyClicks(hc.table.item(0,2), "AlKAlpha")
        assert hc.table.item(0, 0).text() == "D"
        #assert 1 == 0
        qtbot.keyClicks(hc.table.item(0,2), "SiKAlpha")
        qtbot.mouseClick(hc.closeButton, QtCore.Qt.LeftButton)
        qtbot.done_man_cal = 1

    def cal_opened():
        plotter = app._selected_window
        qtbot.waitUntil(lambda: isinstance(app._selected_window, massGui.massless.HistPlotter), timeout=10000)
        assert isinstance(plotter, massGui.massless.HistPlotter)
        qtbot.addWidget(plotter)
        assert plotter.eRangeLow.text == ""
        qtbot.done_cal_open = 1

    qtbot.keyClicks(app.maxChansSpinBox, '2')
    #qtbot.mouseClick(app.selectFileButton, QtCore.Qt.LeftButton)

    #manual bypass of file loading dialog
    app.load_file(r'C:\Users\Grant Mondeel\Box\my EUV\tes\realtime\realtime\Summer2022\20200107\0002\20200107_run0002_chan1.off') # sets self._choose_file_lastdir
    app.set_std_dev_threshold()
    app.calibrationGroup.setEnabled(True)
    app.calButtonGroup.setEnabled(False)

    qtbot.done_man_cal = 1
    QtCore.QTimer.singleShot(2000, manual_cal)
    qtbot.mouseClick(app.lineIDButton, QtCore.Qt.LeftButton)
    #qtbot.waitUntil(lambda: qtbot.done_man_cal == 1)
    #QtTest.QTest.qWait(10000)
    assert app.calTable.item(0, 0).text() == "AlKAlpha"

    # qtbot.done_cal_open = 0
    # QtCore.QTimer.singleShot(10000, cal_opened)
    # #qtbot.mouseClick(app.allChanCalButton, QtCore.Qt.LeftButton)
    # app.allChannelCalibration()
    # qtbot.waitUntil(lambda: qtbot.done_cal_open == 1, timeout = 20000)
    # #qtbot.waitUntil(lambda: isinstance(app._selected_window, massGui.massless.HistPlotter), timeout = 30000)
    
    




def runOpen():
    sys.exit(pytest.main(args=massGui.__path__))

# if __name__=="__main__":
#     sys.exit(pytest.main(args=massGui.__path__))

