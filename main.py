import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QLabel, QWidget
from PyQt6.uic import loadUi
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtCore import QSettings
from datetime import datetime
import json
from timetable_module import TimetableModule
from auto_cctv_controller import AutoCCTVController  # 导入自动新闻联播模块
from shutdown_module import ShutdownModule  # 导入关机模块
from time_module import TimeModule  # 导入时间模块
from embed_external_window import ExternalWindowEmbedder  # 导入外部窗口嵌入模块

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 加载 .ui 文件
        loadUi('./ui/mainwindow.ui', self)  # 替换为实际路径

        # 初始化各个模块
        self.init_modules()

        # 设置定时器每分钟更新一次
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timetable)
        self.timer.start(60000)  # 每分钟更新

        # 初始更新
        self.update_timetable()

        # 启动定时器以每分钟检查一次设置
        self.settings_timer = QTimer(self)
        self.settings_timer.timeout.connect(self.check_settings)
        self.settings_timer.start(60000)  # 每分钟检查一次设置

        # 初始化时间模块
        self.time_module = TimeModule(self)

        # 保存和恢复窗口大小和位置
        self.restore_window_geometry()

        # 将窗口置于最下层
        self.setWindowState(Qt.WindowState.WindowNoState)  # 确保窗口状态正常
        self.show()
        self.lower()  # 将窗口置于最下层

        # 读取 data/exe.txt 文件
        self.read_exe_file()

    def show_message(self, message):
        # 创建 QMessageBox
        msg_box = QMessageBox(self)
        msg_box.setText(message)
        msg_box.setWindowTitle("提示")
        msg_box.setIcon(QMessageBox.Icon.Information)

        # 显示消息框并设置自动关闭
        msg_box.show()
        QTimer.singleShot(3000, msg_box.close)  # 3秒后关闭消息框

    def read_exe_file(self):
        try:
            with open('data/exe.txt', 'r', encoding='utf-8') as file:
                target_exe_name = file.read().strip()
                if target_exe_name:
                    # 如果文件不为空，初始化外部窗口嵌入器
                    QTimer.singleShot(8000, lambda: self.embed_external_window(target_exe_name))
                else:
                    # 如果文件为空，显示一个消息
                    self.show_message("没有指定要嵌入的程序")
        except FileNotFoundError:
            # 如果文件不存在，显示一个消息
            self.show_message("data/exe.txt 文件不存在")

    def embed_external_window(self, target_exe_name):
        # 找到 widget
        widget = self.findChild(QWidget, "widget")
        if widget is not None:
            # 在 widget 中插入外部窗口
            embedder = ExternalWindowEmbedder(widget, target_exe_name, self.status_callback)
            embedder.find_and_embed_window()
        else:
            self.show_message("找不到 widget，请检查 UI 文件")

    def status_callback(self, message):
        # 使用 show_message 方法显示消息
        self.show_message(message)

    def init_modules(self):
        self.timetable_module = TimetableModule(self)
        self.shutdown_module = None
        self.cctv_controller = None
        self.load_settings()  # 确保设置已加载
        self.init_news_module()
        self.init_shutdown_module()  # 在设置加载后初始化关机模块

    def update_timetable(self):
        current_time = datetime.now().time()
        self.timetable_module.update_timetable(current_time)

    def load_settings(self):
        """加载设置"""
        try:
            with open('data/launch.json', 'r', encoding='utf-8') as file:
                settings = json.load(file)
                self.shutdown_status = settings.get('shutdown', '关闭')
                self.news_status = settings.get('news', '关闭')
        except (FileNotFoundError, json.JSONDecodeError):
            self.shutdown_status = '关闭'
            self.news_status = '关闭'

    def check_settings(self):
        """检查设置并更新状态"""
        self.load_settings()

    def init_news_module(self):
        """根据设置初始化新闻联播模块"""
        if self.news_status == '开启' and not hasattr(self, 'cctv_controller'):
            self.cctv_controller = AutoCCTVController()
        elif self.news_status == '关闭' and hasattr(self, 'cctv_controller'):
            self.cctv_controller.stop_timers()
            del self.cctv_controller

    def init_shutdown_module(self):
        """根据设置初始化关机模块"""
        if self.shutdown_status == '开启':
            if not hasattr(self, 'shutdown_module') or self.shutdown_module is None:
                self.shutdown_module = ShutdownModule(self)  # 传递 self 作为父窗口引用
        elif self.shutdown_status == '关闭' and hasattr(self, 'shutdown_module'):
            if self.shutdown_module is not None:
                self.shutdown_module.stop()  # 确保 self.shutdown_module 不是 None
            del self.shutdown_module
            self.shutdown_module = None  # 清除引用

    def restore_window_geometry(self):
        """恢复窗口大小和位置"""
        settings = QSettings("Log", "EC")

        # 恢复窗口几何信息
        geometry = settings.value("windowGeometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # 如果没有保存的几何信息，使用默认值
            default_width = 400
            default_height = 600
            self.resize(default_width, default_height)

        # 恢复窗口位置
        position = settings.value("windowPosition")
        if position:
            self.move(position)
        else:
            # 如果没有保存的位置信息，使用默认值
            default_x = 100
            default_y = 100
            self.move(default_x, default_y)

    def closeEvent(self, event):
        """在窗口关闭时保存窗口大小和位置"""
        settings = QSettings("Log", "EC")
        settings.setValue("windowGeometry", self.saveGeometry())
        settings.setValue("windowPosition", self.pos())
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 加载 QSS 文件
    with open('data/qss.qss', 'r', encoding="utf-8") as f:
        app.setStyleSheet(f.read())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())