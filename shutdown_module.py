# shutdown_module.py
import json
from PyQt6.QtCore import QTimer, QTime, QDate, Qt, QRect, QPoint
import os
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.uic import loadUi
from PyQt6.QtWidgets import QDialog

class CountdownDialog(QDialog):
    def __init__(self, parent=None):
        """
        初始化倒计时对话框。
        """
        super().__init__(parent)
        loadUi('./ui/shutdown.ui', self)  # 加载UI文件
        self.setWindowTitle('关机倒计时')
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)

        # 获取主屏幕的尺寸
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        # 计算窗口在屏幕中心的位置
        window_geometry = self.geometry()
        x = (screen_geometry.width() - window_geometry.width()) // 2
        y = (screen_geometry.height() - window_geometry.height()) // 2
        self.move(x, y)

        self.countdown_seconds = 10
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)
        self.update_countdown()

        self.cancel_shutdown_button.clicked.connect(self.cancel_shutdown)
        self.shutdown_now_button.clicked.connect(self.shutdown_now)

    def update_countdown(self):
        """
        更新倒计时显示，并在倒计时结束时触发关机操作。
        """
        self.countdown_label.setText(f"关机倒计时：{self.countdown_seconds}秒")
        if self.countdown_seconds == 0:
            self.shutdown_now()
        else:
            self.countdown_seconds -= 1
            self.raise_()  # 确保窗口在最上层
            self.activateWindow()  # 激活窗口

    def cancel_shutdown(self):
        """
        取消关机操作并关闭对话框。
        """
        self.timer.stop()
        self.reject()

    def shutdown_now(self):
        """
        立即执行关机操作并关闭对话框。
        """
        self.timer.stop()
        self.accept()

class ShutdownModule:
    def __init__(self, parent=None):
        """
        初始化关机模块。
        """
        self.parent = parent  # 保存父窗口引用
        self.shutdown_times = self.read_shutdown_times()
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_shutdown_time)
        self.timer.start(1000)
        self.countdown_active = False
        self.delay_timer = QTimer()
        self.delay_timer.setSingleShot(True)
        self.delay_timer.timeout.connect(self.reset_countdown_active)

    def read_shutdown_times(self):
        """
        从JSON文件中读取关机时间设置。
        """
        try:
            with open('data/closetime.json', 'r', encoding='utf-8') as file:
                data = json.load(file)
                return data.get('shutdown_times', {})
        except FileNotFoundError:
            return {}

    def check_shutdown_time(self):
        """
        检查当前时间是否与设定的关机时间匹配，并在匹配时弹出倒计时对话框。
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
                if current_time.addSecs(-1) <= shutdown_time <= current_time.addSecs(1):
                    self.show_countdown_dialog()
                    return
        except Exception as e:
            pass

    def show_countdown_dialog(self):
        """
        显示倒计时对话框，并根据用户选择执行关机或延迟操作。
        """
        self.countdown_active = True
        self.countdown_dialog = CountdownDialog(self.parent)
        if self.countdown_dialog.exec() == QDialog.DialogCode.Accepted:
            self.shutdown()
        else:
            self.start_delay_timer()

    def shutdown(self):
        """
        执行系统关机命令。
        """
        os.system('shutdown /s /t 1')
        QApplication.quit()

    def start_delay_timer(self):
        """
        启动延迟定时器，延迟一段时间后重置倒计时状态。
        """
        self.delay_timer.start(120000)

    def reset_countdown_active(self):
        """
        重置倒计时活动状态。
        """
        self.countdown_active = False

    def stop(self):
        """
        停止所有定时器。
        """
        self.timer.stop()
        self.delay_timer.stop()