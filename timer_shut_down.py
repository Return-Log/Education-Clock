"""
https://github.com/Return-Log/Education-Clock
GPL-3.0 license
coding: UTF-8
"""

import sys
import json5
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox, QDialog, QDesktopWidget
from PyQt5.QtCore import QTimer, QTime, QDate, Qt
import os


class CountdownDialog(QDialog):
    """
    关机倒计时对话框类
    """

    def __init__(self, parent=None):
        """
        初始化倒计时对话框
        """
        super().__init__(parent)
        self.setWindowTitle('关机倒计时')
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.countdown_label = QLabel(self)
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setStyleSheet("font-size: 60px; font-weight: bold; font-family: 'SimHei'; color: #003399;")
        self.cancel_shutdown_button = QPushButton('取消关机', self)
        self.cancel_shutdown_button.setStyleSheet("font-size: 70px; font-weight: bold; font-family: 'SimHei'; background-color: #CC0033; color: #000000;")
        self.cancel_shutdown_button.clicked.connect(self.cancel_shutdown)
        self.shutdown_now_button = QPushButton('立即关机', self)
        self.shutdown_now_button.setStyleSheet("font-size: 70px; font-weight: bold; font-family: 'SimHei'; background-color: #99CC00; color: #000000;")
        self.shutdown_now_button.clicked.connect(self.shutdown_now)

        layout = QVBoxLayout(self)
        layout.addWidget(self.countdown_label)
        layout.addWidget(self.cancel_shutdown_button)
        layout.addWidget(self.shutdown_now_button)
        self.setLayout(layout)

        self.countdown_seconds = 10
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)
        self.update_countdown()

    def update_countdown(self):
        """
        更新倒计时标签的文本
        """
        self.countdown_label.setText(f"关机倒计时：{self.countdown_seconds}秒")
        if self.countdown_seconds == 0:
            self.shutdown_now()
        self.countdown_seconds -= 1

    def cancel_shutdown(self):
        """
        取消关机操作
        """
        self.timer.stop()
        self.reject()

    def shutdown_now(self):
        """
        立即关机
        """
        self.timer.stop()
        self.accept()


class ShutdownTimerApp(QWidget):
    """
    关机计时器应用程序类
    """

    def __init__(self):
        """
        初始化关机计时器应用程序
        """
        super().__init__()
        self.shutdown_times = self.read_shutdown_times()
        self.initUI()
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_shutdown_time)
        self.timer.start(1000)
        self.countdown_active = False
        self.delay_timer = QTimer()
        self.delay_timer.setSingleShot(True)
        self.delay_timer.timeout.connect(self.reset_countdown_active)

    def read_shutdown_times(self):
        """
        读取并返回关机时间配置
        """
        try:
            with open('data/[关机时间]closetime.json5', 'r', encoding='utf-8') as file:
                data = json5.load(file)
                return data.get('shutdown_times', {})
        except FileNotFoundError:
            return {}

    def initUI(self):
        """
        初始化用户界面
        """
        self.setWindowTitle('关机倒计时')
        self.resize(300, 150)
        self.center()

        self.setStyleSheet("background-color: #bbcdc5;")  # 设置背景色

    def center(self):
        """
        将窗口居中显示
        """
        screen_geometry = QDesktopWidget().screenGeometry()
        window_geometry = self.frameGeometry()
        x = (screen_geometry.width() - window_geometry.width()) // 2
        y = (screen_geometry.height() - window_geometry.height()) // 2
        self.move(x, y)

    def check_shutdown_time(self):
        """
        检查是否应该启动关机倒计时
        """
        if self.countdown_active:
            return

        try:
            current_time = QTime.currentTime()
            current_day = QDate.currentDate().dayOfWeek()

            day_mapping = {
                1: 'Monday',
                2: 'Tuesday',
                3: 'Wednesday',
                4: 'Thursday',
                5: 'Friday',
                6: 'Saturday',
                7: 'Sunday'
            }

            day_name = day_mapping.get(current_day, '')

            shutdown_times_today = self.shutdown_times.get(day_name, [])

            for shutdown_time in shutdown_times_today:
                shutdown_time = QTime.fromString(shutdown_time, 'hh:mm')
                # 检查当前时间是否在关机时间的前后1秒内，以确定是否需要关机
                if current_time.addSecs(-1) <= shutdown_time <= current_time.addSecs(1):
                    self.show_countdown_dialog()
                    return
        except Exception as e:
            pass  # 处理异常（如有必要，您可以在此处添加日志记录）

    def show_countdown_dialog(self):
        """
        显示关机倒计时对话框
        """
        self.countdown_active = True
        self.countdown_dialog = CountdownDialog(self)
        if self.countdown_dialog.exec_() == QDialog.Accepted:
            self.shutdown()
        else:
            self.start_delay_timer()

    def shutdown(self):
        """
        执行关机操作
        """
        os.system('shutdown /s /t 1')
        sys.exit()

    def start_delay_timer(self):
        """
        启动延迟计时器，用于在倒计时对话框被取消后等待一段时间再允许新的倒计时启动
        """
        self.delay_timer.start(120000)  # 2分钟延迟

    def reset_countdown_active(self):
        """
        重置倒计时活动状态
        """
        self.countdown_active = False

    def stop(self):
        """
        停止计时器
        """
        self.timer.stop()
        self.delay_timer.stop()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ShutdownTimerApp()
    if ex.shutdown_times:
        sys.exit(app.exec_())
    else:
        QMessageBox.warning(None, '警告', '未找到关机时间，请先设置关机时间！')
