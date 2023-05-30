import pytest

# import PyQt5.QtWidgets as QtWidgets
# import PyQt5.uic
# from PyQt5 import QtCore, QtGui, QtWidgets
# from PyQt5.QtCore import QSettings, pyqtSlot
# from PyQt5.QtWidgets import QFileDialog
import sys
import os
import massGui
import massGui.MASSGUI

@pytest.fixture
def app(qtbot):
    test_gui_app = massGui.MASSGUI.MainWindow()
    qtbot.addWidget(test_gui_app)

    return test_gui_app

def test_open(app):
    assert app.selectFileButton.text()=="Select .OFF File"

def runTest():
    sys.exit(pytest.main(["-ra"], massGui.tests))

if __name__=="__main__":
    sys.exit(pytest.main(["-ra"], massGui.tests))

