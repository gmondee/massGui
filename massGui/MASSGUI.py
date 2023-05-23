import PyQt5.QtWidgets as qt 


def main():
    app = qt.QApplication([])
    label = qt.QLabel("Hello")
    label.show()

    #button.clicked.connect(on_button_clicked)

    app.exec_()