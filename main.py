"""
https://github.com/Return-Log/Education-Clock
GPL-3.0 license
"""

import os
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QCheckBox, QSystemTrayIcon, QMenu, QAction, \
    QMessageBox, QPushButton
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QIcon

# 导入模块
from timetable import ClassSchedule
from weather import WeatherApp
from clock import DigitalClock
import autocctv
import timer_shut_down


class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        # 设置配置文件路径
        self.settings_file = os.path.join('data', 'launch.ini')
        self.init_ui()

        # 根据设置状态决定是否启动各个模块
        self.clock = None
        self.weather = None
        self.timetable = None
        self.autocctv = None
        self.timer_shutdown = None

        if self.clock_checkbox.isChecked():
            self.clock = DigitalClock()
            self.clock.show()

        if self.weather_checkbox.isChecked():
            self.weather = WeatherApp()
            self.weather.show()

        if self.timetable_checkbox.isChecked():
            self.timetable = ClassSchedule()
            self.timetable.show()

        if self.autocctv_checkbox.isChecked():
            self.autocctv = autocctv.AutoCCTVController()

        if self.timer_shutdown_checkbox.isChecked():
            self.timer_shutdown = timer_shut_down.ShutdownTimerApp()

        # 创建系统托盘图标和菜单
        self.create_tray_icon()
        self.tray_icon.show()

    def init_ui(self):
        self.setWindowTitle("Education Clock模块管理")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()

        # 添加时钟模块的复选框和标签
        self.clock_label = QLabel("时钟")
        self.clock_checkbox = QCheckBox()
        # 根据之前保存的设置，设置复选框的初始状态
        self.clock_checkbox.setChecked(self.load_setting("clock_enabled", True))
        self.clock_checkbox.stateChanged.connect(self.toggle_clock)

        # 添加天气模块的复选框和标签
        self.weather_label = QLabel("天气")
        self.weather_checkbox = QCheckBox()
        self.weather_checkbox.setChecked(self.load_setting("weather_enabled", True))
        self.weather_checkbox.stateChanged.connect(self.toggle_weather)

        # 添加课程表模块的复选框和标签
        self.timetable_label = QLabel("课程表")
        self.timetable_checkbox = QCheckBox()
        self.timetable_checkbox.setChecked(self.load_setting("timetable_enabled", True))
        self.timetable_checkbox.stateChanged.connect(self.toggle_timetable)

        # 添加自动监控模块的复选框和标签
        self.autocctv_label = QLabel("自动新闻联播")
        self.autocctv_checkbox = QCheckBox()
        self.autocctv_checkbox.setChecked(self.load_setting("autocctv_enabled", True))
        self.autocctv_checkbox.stateChanged.connect(self.toggle_autocctv)

        # 添加定时关机模块的复选框和标签
        self.timer_shutdown_label = QLabel("定时关机")
        self.timer_shutdown_checkbox = QCheckBox()
        self.timer_shutdown_checkbox.setChecked(self.load_setting("timer_shutdown_enabled", True))
        self.timer_shutdown_checkbox.stateChanged.connect(self.toggle_timer_shutdown)

        # 添加关于和帮助按钮
        self.about_button = QPushButton("关于")
        self.about_button.clicked.connect(self.show_about)
        self.help_button = QPushButton("帮助")
        self.help_button.clicked.connect(self.show_help)

        # 将标签、复选框和按钮添加到布局中
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

    def load_setting(self, key, default_value):
        """加载设置，如果文件不存在则返回默认值"""
        if os.path.exists(self.settings_file):
            settings = QSettings(self.settings_file, QSettings.IniFormat)
            return settings.value(key, default_value, type=bool)
        else:
            return default_value

    def save_setting(self, key, value):
        """保存设置到文件"""
        settings = QSettings(self.settings_file, QSettings.IniFormat)
        settings.setValue(key, value)

    # 切换时钟模块的显示状态
    def toggle_clock(self, state):
        self.save_setting("clock_enabled", state == Qt.Checked)
        if state == Qt.Checked:
            if self.clock is None:
                self.clock = DigitalClock()
            self.clock.show()
        else:
            if self.clock is not None:
                self.clock.hide()

    # 切换天气模块的显示状态
    def toggle_weather(self, state):
        self.save_setting("weather_enabled", state == Qt.Checked)
        if state == Qt.Checked:
            if self.weather is None:
                self.weather = WeatherApp()
            self.weather.show()
        else:
            if self.weather is not None:
                self.weather.hide()

    # 切换课程表模块的显示状态
    def toggle_timetable(self, state):
        self.save_setting("timetable_enabled", state == Qt.Checked)
        if state == Qt.Checked:
            if self.timetable is None:
                self.timetable = ClassSchedule()
            self.timetable.show()
        else:
            if self.timetable is not None:
                self.timetable.hide()

    # 切换自动新闻联播模块的显示状态
    def toggle_autocctv(self, state):
        self.save_setting("autocctv_enabled", state == Qt.Checked)
        if state == Qt.Checked:
            if self.autocctv is None:
                self.autocctv = autocctv.AutoCCTVController()
        else:
            if self.autocctv is not None:
                self.autocctv.close_browser()

    # 切换定时关机模块的显示状态
    def toggle_timer_shutdown(self, state):
        self.save_setting("timer_shutdown_enabled", state == Qt.Checked)
        if state == Qt.Checked:
            if self.timer_shutdown is None:
                self.timer_shutdown = timer_shut_down.ShutdownTimerApp()  # 实例化 ShutdownTimerApp
        else:
            if self.timer_shutdown is not None:
                self.save_setting("timer_shutdown_enabled", False)

    # 显示关于信息
    def show_about(self):
        QMessageBox.information(self, "关于", "Education-Clock\n版本：0.5\n许可证：GPLv3\nGitHub仓库：https://github.com/Return"
                                              "-Log/Education-Clock\nCopyright © 2024 Log All rights reserved.")

    # 显示帮助信息
    def show_help(self):
        QMessageBox.about(self, "帮助", "使用说明：\n1. 选择模块是否启用。\n2. 模块将在单独的窗口中显示。\n3. 设置信息存储在软件目录data文件夹中。\n4. "
                                        "设置如无法保存请用管理员权限运行。")

    # 创建系统托盘图标和菜单
    def create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icon.ico"))  # 设置托盘图标

        tray_menu = QMenu(self)
        show_action = QAction("显示", self)
        quit_action = QAction("退出", self)

        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(QApplication.instance().quit)

        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    # 托盘图标被点击时显示窗口
    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show()

    # 重写关闭事件，点击关闭按钮时隐藏窗口
    def closeEvent(self, event):
        self.hide()
        event.ignore()


if __name__ == '__main__':
    if not os.path.exists('data'):
        os.makedirs('data')

    app = QApplication(sys.argv)
    main_app = MainApp()
    main_app.hide()  # 启动时隐藏窗口
    sys.exit(app.exec_())
