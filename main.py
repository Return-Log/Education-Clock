import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.uic import loadUi
from PyQt6.QtCore import QTimer
from datetime import datetime
import json
from timetable_module import TimetableModule

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 加载 .ui 文件
        loadUi('path_to_your_file.ui', self)  # 替换为实际路径
        # 初始化各个模块
        self.init_modules()
        # 设置定时器每分钟更新一次
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timetable)
        self.timer.start(60000)  # 每分钟更新
        # 初始更新
        self.update_timetable()

    def init_modules(self):
        from module_with_settings import ModuleWithSettings
        self.module_with_settings = ModuleWithSettings(self)
        self.timetable_module = TimetableModule(self)

    def update_timetable(self):
        current_time = datetime.now().time()
        self.timetable_module.update_timetable(current_time)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 加载 QSS 文件
    with open('./data/qss.qss', 'r') as f:
        app.setStyleSheet(f.read())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())