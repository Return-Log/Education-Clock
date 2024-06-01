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

        self.countdown_seconds = 10
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
        try:
            with open('data/closetime.json5', 'r', encoding='utf-8') as file:
                data = json5.load(file)
                return data.get('shutdown_times', {})
        except FileNotFoundError:
            return {}

    def initUI(self):
        self.setWindowTitle('关机倒计时')
        self.resize(300, 150)
        self.center()

        self.setStyleSheet("""
            QPushButton {
                font-size: 32px;
                font-weight: bold;
            }
        """)

    def center(self):
        screen_geometry = QDesktopWidget().screenGeometry()
        window_geometry = self.frameGeometry()
        x = (screen_geometry.width() - window_geometry.width()) // 2
        y = (screen_geometry.height() - window_geometry.height()) // 2
        self.move(x, y)

    def check_shutdown_time(self):
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
                if current_time.addSecs(-60) <= shutdown_time <= current_time.addSecs(60):
                    self.show_countdown_dialog()
                    return
        except Exception as e:
            pass  # 处理异常（如有必要，您可以在此处添加日志记录）

    def show_countdown_dialog(self):
        self.countdown_active = True
        self.countdown_dialog = CountdownDialog(self)
        if self.countdown_dialog.exec_() == QDialog.Accepted:
            self.shutdown()
        else:
            self.start_delay_timer()

    def shutdown(self):
        os.system('shutdown /s /t 1')
        sys.exit()

    def start_delay_timer(self):
        self.delay_timer.start(120000)  # 2分钟延迟

    def reset_countdown_active(self):
        self.countdown_active = False

    def stop(self):
        self.timer.stop()
        self.delay_timer.stop()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ShutdownTimerApp()
    if ex.shutdown_times:
        sys.exit(app.exec_())
    else:
        QMessageBox.warning(None, '警告', '未找到关机时间，请先设置关机时间！')
