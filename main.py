"""
https://github.com/Return-Log/Education-Clock
GPL-3.0 license
coding: UTF-8
"""

import os
import sys
import json5
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QCheckBox, QSystemTrayIcon, QMenu, QAction, \
    QMessageBox, QPushButton
from PyQt5.QtCore import Qt, QSettings, QTimer, QTime, QDate
from PyQt5.QtGui import QIcon, QFontMetrics, QFont

# 导入模块
from timetable import ClassSchedule
from weather import WeatherApp
from clock import DigitalClock
import autocctv
import timer_shut_down


class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.settings_file = os.path.join('data', 'launch.ini')
        self.init_ui()

        self.clock = None
        self.weather = None
        self.timetable = None
        self.autocctv = None
        self.timer_shutdown = None

        self.load_initial_settings()
        self.create_tray_icon()
        self.tray_icon.show()

    def init_ui(self):
        self.setWindowTitle("Education Clock模块管理")
        self.setGeometry(100, 100, 300, 200)

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

        layout.addWidget(self.clock_label)
        layout.addWidget(self.clock_checkbox)
        layout.addWidget(self.weather_label)
        layout.addWidget(self.weather_checkbox)
        layout.addWidget(self.timetable_label)
        layout.addWidget(self.timetable_checkbox)
        layout.addWidget(self.autocctv_label)
        layout.addWidget(self.autocctv_checkbox)
        layout.addWidget(self.timer_shutdown_label)
        layout.addWidget(self.timer_shutdown_checkbox)
        layout.addWidget(self.about_button)
        layout.addWidget(self.help_button)

        self.setLayout(layout)

    def load_initial_settings(self):
        if self.clock_checkbox.isChecked():
            self.toggle_clock(Qt.Checked)

        if self.weather_checkbox.isChecked():
            self.toggle_weather(Qt.Checked)

        if self.timetable_checkbox.isChecked():
            self.toggle_timetable(Qt.Checked)

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

    def toggle_autocctv(self, state):
        self.save_setting("autocctv_enabled", state == Qt.Checked)
        if state == Qt.Checked:
            if self.autocctv is None:
                self.autocctv = autocctv.AutoCCTVController()
        else:
            if self.autocctv is not None:
                self.autocctv.close_browser()

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
        QMessageBox.information(self, "关于", "Education-Clock\n版本：v0.6\n更新日期：2024/6/2\n许可证：GPLv3\nGitHub仓库：https://github.com/Return"
                                              "-Log/Education-Clock\nCopyright © 2024 Log All rights reserved.")

    def show_help(self):
        QMessageBox.about(self, "帮助", "使用说明：\n1. 选择模块是否启用。\n2. 设置信息存储在软件目录data文件夹中。\n3. "
                                        "设置如无法保存请用管理员权限运行。")

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
