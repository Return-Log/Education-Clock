
from PyQt6.QtWidgets import QApplication
from PyQt6 import uic
import sys

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ui = uic.loadUi("./ui/mainwindow.ui")

    selected_day = ui.comboBox

    print(selected_day.currentIndex())

    ui.show()
    app.exec()