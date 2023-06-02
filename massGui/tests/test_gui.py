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

@pytest.fixture
def app(qtbot):
    test_gui_app = massGui.massGui.MainWindow()
    qtbot.addWidget(test_gui_app)

    return test_gui_app

def test_open(app):
    assert app.selectFileButton.text()=="Select .OFF File"

def test_cal(app, qtbot):
    qtbot.keyClicks(app.maxChansSpinBox, '2')
    #qtbot.mouseClick(app.selectFileButton, QtCore.Qt.LeftButton)

    #manual bypass of file loading dialog
    app.load_file(r'C:\Users\Grant Mondeel\Box\my EUV\tes\realtime\realtime\Summer2022\20200107\0002\20200107_run0002_chan1.off') # sets self._choose_file_lastdir
    app.set_std_dev_threshold()
    app.calibrationGroup.setEnabled(True)
    app.calButtonGroup.setEnabled(False)
    
    qtbot.mouseClick(app.lineIDButton, QtCore.Qt.LeftButton)
    print("A")
    QtTest.QTest.qWait(0.5*1000.)
    hc = QtWidgets.QApplication.activeWindow()#app.hc#app.activeWindow()
    qtbot.mouseClick(hc, QtCore.Qt.LeftButton, pos=QtCore.QPoint(554, 177))
    qtbot.mouseClick(hc, QtCore.Qt.LeftButton, pos=QtCore.QPoint(604, 112))
    qtbot.keyClicks(hc.table.item(0,2), "AlKAlpha")
    qtbot.keyClicks(hc.table.item(0,2), "SiKAlpha")
    qtbot.mouseClick(hc.closeButton, QtCore.Qt.LeftButton)



def runOpen():
    sys.exit(pytest.main(args=massGui.__path__))

# if __name__=="__main__":
#     sys.exit(pytest.main(args=massGui.__path__))

