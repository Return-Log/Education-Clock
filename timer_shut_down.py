"""
https://github.com/Return-Log/Education-Clock
GPL-3.0 license
coding: UTF-8
"""

import sys
import json5
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox, QDialog
from PyQt6.QtCore import QTimer, QTime, QDate, Qt
from PyQt6.QtGui import QScreen
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
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)  # 设置窗口总是保持在顶部

        # 创建倒计时标签并设置样式
        self.countdown_label = QLabel(self)
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.countdown_label.setStyleSheet("font-size: 60px; font-weight: bold; font-family: 'SimHei'; color: #003399;")

        # 创建“取消关机”按钮并设置样式和点击事件
        self.cancel_shutdown_button = QPushButton('取消关机', self)
        self.cancel_shutdown_button.setStyleSheet("font-size: 70px; font-weight: bold; font-family: 'SimHei'; background-color: #CC0033; color: #000000;")
        self.cancel_shutdown_button.clicked.connect(self.cancel_shutdown)

        # 创建“立即关机”按钮并设置样式和点击事件
        self.shutdown_now_button = QPushButton('立即关机', self)
        self.shutdown_now_button.setStyleSheet("font-size: 70px; font-weight: bold; font-family: 'SimHei'; background-color: #99CC00; color: #000000;")
        self.shutdown_now_button.clicked.connect(self.shutdown_now)

        # 设置布局
        layout = QVBoxLayout(self)
        layout.addWidget(self.countdown_label)
        layout.addWidget(self.cancel_shutdown_button)
        layout.addWidget(self.shutdown_now_button)
        self.setLayout(layout)

        # 初始化倒计时时间
        self.countdown_seconds = 10

        # 设置定时器，每秒触发一次以更新倒计时
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
            self.shutdown_now()  # 倒计时结束，执行关机操作
        self.countdown_seconds -= 1

    def cancel_shutdown(self):
        """
        取消关机操作
        """
        self.timer.stop()  # 停止倒计时
        self.reject()  # 关闭对话框

    def shutdown_now(self):
        """
        立即关机
        """
        self.timer.stop()  # 停止倒计时
        self.accept()  # 关闭对话框并返回接受状态


class ShutdownTimerApp(QWidget):
    """
    关机计时器应用程序类
    """

    def __init__(self):
        """
        初始化关机计时器应用程序
        """
        super().__init__()
        self.shutdown_times = self.read_shutdown_times()  # 从配置文件读取关机时间
        self.initUI()  # 初始化界面
        self.timer = QTimer()  # 创建定时器
        self.timer.timeout.connect(self.check_shutdown_time)  # 每秒检查是否到了关机时间
        self.timer.start(1000)
        self.countdown_active = False  # 标记倒计时是否激活
        self.delay_timer = QTimer()  # 延迟计时器，用于取消倒计时后的延迟
        self.delay_timer.setSingleShot(True)
        self.delay_timer.timeout.connect(self.reset_countdown_active)

    def read_shutdown_times(self):
        """
        读取并返回关机时间配置
        """
        try:
            # 从JSON5文件中读取关机时间配置
            with open('data/[关机时间]closetime.json5', 'r', encoding='utf-8') as file:
                data = json5.load(file)
                return data.get('shutdown_times', {})
        except FileNotFoundError:
            return {}

    def initUI(self):
        """
        初始化用户界面
        """
        self.setWindowTitle('关机倒计时')  # 设置窗口标题
        self.resize(300, 150)  # 设置窗口大小
        self.center()  # 窗口居中显示
        self.setStyleSheet("background-color: #bbcdc5;")  # 设置背景色

    def center(self):
        """
        将窗口居中显示
        """
        screen = self.screen()  # 获取当前窗口所在的屏幕
        screen_geometry = screen.availableGeometry()  # 获取屏幕的可用几何信息
        window_geometry = self.frameGeometry()  # 获取窗口尺寸
        x = (screen_geometry.width() - window_geometry.width()) // 2
        y = (screen_geometry.height() - window_geometry.height()) // 2
        self.move(x, y)  # 移动窗口到中心位置

    def check_shutdown_time(self):
        """
        检查是否应该启动关机倒计时
        """
        if self.countdown_active:  # 如果倒计时已经激活，则直接返回
            return

        try:
            current_time = QTime.currentTime()  # 获取当前时间
            current_day = QDate.currentDate().dayOfWeek()  # 获取当前星期几

            # 将星期几映射为英文名称
            day_mapping = {
                1: 'Monday',
                2: 'Tuesday',
                3: 'Wednesday',
                4: 'Thursday',
                5: 'Friday',
                6: 'Saturday',
                7: 'Sunday'
            }

            day_name = day_mapping.get(current_day, '')  # 获取当前星期几对应的英文名称

            shutdown_times_today = self.shutdown_times.get(day_name, [])  # 获取今天的关机时间

            for shutdown_time in shutdown_times_today:
                shutdown_time = QTime.fromString(shutdown_time, 'hh:mm')  # 将字符串转换为 QTime 对象
                # 检查当前时间是否接近关机时间（前后1秒）
                if current_time.addSecs(-1) <= shutdown_time <= current_time.addSecs(1):
                    self.show_countdown_dialog()  # 显示关机倒计时对话框
                    return
        except Exception as e:
            pass  # 捕获并忽略异常

    def show_countdown_dialog(self):
        """
        显示关机倒计时对话框
        """
        self.countdown_active = True  # 标记倒计时为激活状态
        self.countdown_dialog = CountdownDialog(self)  # 创建倒计时对话框
        if self.countdown_dialog.exec() == QDialog.DialogCode.Accepted:
            self.shutdown()  # 如果倒计时对话框被接受，则执行关机
        else:
            self.start_delay_timer()  # 否则启动延迟计时器

    def shutdown(self):
        """
        执行关机操作
        """
        os.system('shutdown /s /t 1')  # 调用系统关机命令
        sys.exit()  # 退出程序

    def start_delay_timer(self):
        """
        启动延迟计时器，用于在倒计时对话框被取消后等待一段时间再允许新的倒计时启动
        """
        self.delay_timer.start(120000)  # 启动2分钟的延迟计时器

    def reset_countdown_active(self):
        """
        重置倒计时活动状态
        """
        self.countdown_active = False  # 重置倒计时标记

    def stop(self):
        """
        停止计时器
        """
        self.timer.stop()  # 停止主定时器
        self.delay_timer.stop()  # 停止延迟计时器


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ShutdownTimerApp()  # 创建关机计时器应用程序实例
    if ex.shutdown_times:
        sys.exit(app.exec())  # 启动应用程序事件循环
    else:
        QMessageBox.warning(None, '警告', '未找到关机时间，请先设置关机时间！')  # 如果没有读取到关机时间，则显示警告
