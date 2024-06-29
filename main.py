"""
https://github.com/Return-Log/Education-Clock
GPL-3.0 license
coding: UTF-8
"""

import os
import sys
import json5
import requests
import webbrowser
import pyautogui
import win32com.client
import win32con
import win32gui
import imaplib
import smtplib
import email
import subprocess
import datetime
import pytz
import pyttsx3
from email.header import decode_header
from email.message import EmailMessage
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QCheckBox, QSystemTrayIcon, QMenu, QAction, \
    QMessageBox, QPushButton, QSizePolicy
from PyQt5.QtCore import Qt, QSettings, QTimer, QTime, QDate, QUrl, QPoint, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFontMetrics, QFont, QColor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

# 导入模块
from timetable import ClassSchedule
from weather import WeatherApp
from clock import DigitalClock
import notice_board
import autocctv
import timer_shut_down


class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.settings_file = os.path.join('data', '[模块状态]launch.ini')
        self.init_ui()

        self.clock = None
        self.weather = None
        self.timetable = None
        self.notice_board = None
        self.autocctv = None
        self.timer_shutdown = None

        self.load_initial_settings()
        self.create_tray_icon()
        self.tray_icon.show()

    def init_ui(self):
        self.setWindowTitle("Education Clock模块管理")
        self.setGeometry(100, 100, 300, 250)  # Increased height to accommodate new button
        self.setStyleSheet("background-color: #bbcdc5;")  # 设置背景色

        layout = QVBoxLayout()

        self.clock_label = QLabel("时钟")
        self.clock_checkbox = QCheckBox()
        self.clock_checkbox.setChecked(self.load_setting("clock_enabled", True))
        self.clock_checkbox.stateChanged.connect(self.toggle_clock)

        self.weather_label = QLabel("天气")
        self.weather_checkbox = QCheckBox()
        self.weather_checkbox.setChecked(self.load_setting("weather_enabled", True))
        self.weather_checkbox.stateChanged.connect(self.toggle_weather)

        self.timetable_label = QLabel("课程表")
        self.timetable_checkbox = QCheckBox()
        self.timetable_checkbox.setChecked(self.load_setting("timetable_enabled", True))
        self.timetable_checkbox.stateChanged.connect(self.toggle_timetable)

        self.notice_board_label = QLabel("邮件公告栏")
        self.notice_board_checkbox = QCheckBox()
        self.notice_board_checkbox.setChecked(self.load_setting("notice_board_enabled", True))
        self.notice_board_checkbox.stateChanged.connect(self.toggle_notice_board)

        self.autocctv_label = QLabel("自动新闻联播")
        self.autocctv_checkbox = QCheckBox()
        self.autocctv_checkbox.setChecked(self.load_setting("autocctv_enabled", True))
        self.autocctv_checkbox.stateChanged.connect(self.toggle_autocctv)

        self.timer_shutdown_label = QLabel("定时关机")
        self.timer_shutdown_checkbox = QCheckBox()
        self.timer_shutdown_checkbox.setChecked(self.load_setting("timer_shutdown_enabled", True))
        self.timer_shutdown_checkbox.stateChanged.connect(self.toggle_timer_shutdown)

        self.about_button = QPushButton("关于")
        self.about_button.clicked.connect(self.show_about)
        self.help_button = QPushButton("帮助")
        self.help_button.clicked.connect(self.show_help)
        self.open_data_button = QPushButton("打开data文件夹")
        self.open_data_button.clicked.connect(self.open_data_directory)

        layout.addWidget(self.clock_label)
        layout.addWidget(self.clock_checkbox)
        layout.addWidget(self.weather_label)
        layout.addWidget(self.weather_checkbox)
        layout.addWidget(self.timetable_label)
        layout.addWidget(self.timetable_checkbox)
        layout.addWidget(self.notice_board_label)
        layout.addWidget(self.notice_board_checkbox)
        layout.addWidget(self.autocctv_label)
        layout.addWidget(self.autocctv_checkbox)
        layout.addWidget(self.timer_shutdown_label)
        layout.addWidget(self.timer_shutdown_checkbox)
        layout.addWidget(self.about_button)
        layout.addWidget(self.help_button)
        layout.addWidget(self.open_data_button)

        self.setLayout(layout)

    def load_initial_settings(self):
        if self.clock_checkbox.isChecked():
            self.toggle_clock(Qt.Checked)

        if self.weather_checkbox.isChecked():
            self.toggle_weather(Qt.Checked)

        if self.timetable_checkbox.isChecked():
            self.toggle_timetable(Qt.Checked)

        if self.notice_board_checkbox.isChecked():
            self.toggle_notice_board(Qt.Checked)

        if self.autocctv_checkbox.isChecked():
            self.toggle_autocctv(Qt.Checked)

        if self.timer_shutdown_checkbox.isChecked():
            self.toggle_timer_shutdown(Qt.Checked)

    def load_setting(self, key, default_value):
        if os.path.exists(self.settings_file):
            settings = QSettings(self.settings_file, QSettings.IniFormat)
            return settings.value(key, default_value, type=bool)
        else:
            return default_value

    def save_setting(self, key, value):
        settings = QSettings(self.settings_file, QSettings.IniFormat)
        settings.setValue(key, value)

    def toggle_clock(self, state):
        self.save_setting("clock_enabled", state == Qt.Checked)
        if state == Qt.Checked:
            if self.clock is None:
                self.clock = DigitalClock()
            self.clock.show()
        else:
            if self.clock is not None:
                self.clock.hide()

    def toggle_weather(self, state):
        self.save_setting("weather_enabled", state == Qt.Checked)
        if state == Qt.Checked:
            if self.weather is None:
                self.weather = WeatherApp()
            self.weather.show()
        else:
            if self.weather is not None:
                self.weather.hide()

    def toggle_timetable(self, state):
        self.save_setting("timetable_enabled", state == Qt.Checked)
        if state == Qt.Checked:
            if self.timetable is None:
                self.timetable = ClassSchedule()
            self.timetable.show()
        else:
            if self.timetable is not None:
                self.timetable.hide()

    def toggle_notice_board(self, state):
        self.save_setting("notice_board_enabled", state == Qt.Checked)
        if state == Qt.Checked:
            if self.notice_board is None:
                self.notice_board = notice_board.EmailClient()
            self.notice_board.show()
        else:
            if self.notice_board is not None:
                self.notice_board.hide()

    def toggle_autocctv(self, state):
        self.save_setting("autocctv_enabled", state == Qt.Checked)
        if state == Qt.Checked:
            if self.autocctv is None:
                self.autocctv = autocctv.AutoCCTVController()
        else:
            if self.autocctv is not None:
                self.autocctv.start_timer.stop()  # 停止开始时间检查定时器
                self.autocctv.end_timer.stop()  # 停止结束时间检查定时器
                self.autocctv = None

    def toggle_timer_shutdown(self, state):
        self.save_setting("timer_shutdown_enabled", state == Qt.Checked)
        if state == Qt.Checked:
            if self.timer_shutdown is None:
                self.timer_shutdown = timer_shut_down.ShutdownTimerApp()
        else:
            if self.timer_shutdown is not None:
                self.timer_shutdown.stop()
                self.timer_shutdown = None

    def show_about(self):
        about_text = """
            <p>Education-Clock<br>
            版本：v1.1<br>
            更新日期：2024/6/30<br>
            许可证：GPLv3<br>
            GitHub仓库：<a href='https://github.com/Return-Log/Education-Clock'>https://github.com/Return-Log/Education-Clock</a><br>
            <a href='https://github.com/Return-Log'>Copyright © 2024 Log All rights reserved.</a></p>
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("关于")
        msg.setTextFormat(Qt.RichText)
        msg.setText(about_text)
        msg.exec_()

    def show_help(self):
        help_text = """
            <p>使用说明：<br>
            1. 选择模块是否启用。<br>
            2. 设置信息存储在软件目录data文件夹中，按照提示更改信息。<br>
            3. 设置如无法保存请用管理员权限运行。<br>
            4. 详细帮助请参见<a href='https://github.com/Return-Log/Education-Clock'>GitHub仓库</a>。</p>
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("帮助")
        msg.setTextFormat(Qt.RichText)
        msg.setText(help_text)
        msg.exec_()

    def create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icon.ico"))

        tray_menu = QMenu(self)
        show_action = QAction("显示", self)
        quit_action = QAction("退出", self)

        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(QApplication.instance().quit)

        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show()

    def open_data_directory(self):
        data_dir = os.path.abspath('data')
        if sys.platform == 'win32':
            os.startfile(data_dir)
        elif sys.platform == 'darwin':
            subprocess.call(['open', data_dir])
        else:
            subprocess.call(['xdg-open', data_dir])

    def closeEvent(self, event):
        self.hide()
        event.ignore()


if __name__ == '__main__':
    if not os.path.exists('data'):
        os.makedirs('data')

    app = QApplication(sys.argv)
    main_app = MainApp()
    main_app.hide()
    sys.exit(app.exec_())
