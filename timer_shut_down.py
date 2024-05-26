import sys
import json5
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox, QDialog, \
    QDesktopWidget
from PyQt5.QtCore import QTimer, QTime, Qt
import os


class CountdownDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('关机倒计时')
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.countdown_label = QLabel(self)
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setStyleSheet("font-size: 40px;")
        self.cancel_shutdown_button = QPushButton('取消关机', self)
        self.cancel_shutdown_button.setStyleSheet("background-color: red; color: black;")
        self.cancel_shutdown_button.clicked.connect(self.cancel_shutdown)
        self.shutdown_now_button = QPushButton('立即关机', self)
        self.shutdown_now_button.setStyleSheet("background-color: green; color: black;")
        self.shutdown_now_button.clicked.connect(self.shutdown_now)

        layout = QVBoxLayout(self)
        layout.addWidget(self.countdown_label)
        layout.addWidget(self.cancel_shutdown_button)
        layout.addWidget(self.shutdown_now_button)
        self.setLayout(layout)

        self.countdown_seconds = 5
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)
        self.update_countdown()

    def update_countdown(self):
        self.countdown_label.setText(f"关机倒计时：{self.countdown_seconds}秒")
        if self.countdown_seconds == 0:
            self.shutdown_now()
        self.countdown_seconds -= 1

    def cancel_shutdown(self):
        self.timer.stop()
        self.reject()

    def shutdown_now(self):
        self.timer.stop()
        self.accept()


class ShutdownTimerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.shutdown_times = self.read_shutdown_times()  # 读取关机时间列表
        self.initUI()

    def read_shutdown_times(self):
        try:
            # 尝试打开json5格式的配置文件
            with open('data/closetime.json5', 'r') as file:
                # 解析json5文件中的数据
                data = json5.load(file)
                # 获取关机时间列表
                return data.get('shutdown_times', [])
        except FileNotFoundError:
            # 如果找不到文件，则返回空列表
            return []

    def initUI(self):
        self.setWindowTitle('关机倒计时')
        self.resize(300, 150)  # 设置窗口大小
        self.center()  # 将窗口置于屏幕中心

        # 定时器，每秒检查一次是否到达关机时间
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_shutdown_time)
        self.timer.start(1000)

        # 设置按钮样式
        self.setStyleSheet("""
            QPushButton {
                font-size: 32px; /* Adjust font size */
                font-weight: bold; /* Make font bold */
            }
        """)

    def center(self):
        # 获取屏幕的几何信息
        screen_geometry = QDesktopWidget().screenGeometry()
        window_geometry = self.frameGeometry()
        # 计算窗口在屏幕中心的位置
        x = (screen_geometry.width() - window_geometry.width()) // 2
        y = (screen_geometry.height() - window_geometry.height()) // 2
        # 将窗口移动到计算出的位置
        self.move(x, y)

    def check_shutdown_time(self):
        # 获取当前时间
        current_time = QTime.currentTime()
        # 遍历关机时间列表
        for shutdown_time in self.shutdown_times:
            # 将关机时间从字符串转换为QTime对象，精确到分钟
            shutdown_time = QTime.fromString(shutdown_time, 'hh:mm')
            # 如果当前时间在关机时间的前后1分钟内
            if current_time.addSecs(-60) <= shutdown_time <= current_time.addSecs(60):
                # 显示倒计时对话框
                self.show_countdown_dialog()
                return

    def show_countdown_dialog(self):
        self.timer.stop()
        self.countdown_dialog = CountdownDialog(self)
        if self.countdown_dialog.exec_() == QDialog.Accepted:
            self.shutdown()

    def shutdown(self):
        # 执行系统关机操作
        os.system('shutdown /s /t 1')
        # 退出应用程序
        sys.exit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ShutdownTimerApp()
    # 如果存在关机时间，则显示应用程序界面并运行
    if ex.shutdown_times:
        sys.exit(app.exec_())
    else:
        # 如果不存在关机时间，则弹出警告消息框
        QMessageBox.warning(None, '警告', '未找到关机时间，请先设置关机时间！')
