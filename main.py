"""
    Education-Clock
    Copyright (C) 2024  Log

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QDateEdit, QPushButton, QDialog, \
    QMessageBox, QSlider
from PyQt5.QtCore import Qt, QTimer, QDate, QPoint, QSettings, QTime
from PyQt5.QtGui import QFont
import json5

# 导入timetable.py中的ClassSchedule类
from timetable import ClassSchedule


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle('设置倒计时')
        self.setGeometry(200, 200, 300, 200)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # 添加关于按钮
        self.about_button = QPushButton("关于")
        self.about_button.clicked.connect(self.show_about_dialog)
        self.layout.addWidget(self.about_button)

        self.label_event = QLabel("事件:")
        self.layout.addWidget(self.label_event)

        self.input_event = QLineEdit()
        self.input_event.setMaxLength(2)  # 设置最大长度为2
        self.layout.addWidget(self.input_event)

        self.label_end_date = QLabel("截止日期:")
        self.layout.addWidget(self.label_end_date)

        self.input_end_date = QDateEdit()
        self.input_end_date.setCalendarPopup(True)
        self.layout.addWidget(self.input_end_date)

        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_and_close)
        self.layout.addWidget(self.save_button)

    def show_about_dialog(self):
        about_text = """
        Education-Clock

        版本：0.2

        作者：Log

        许可证：GPLv3

        仓库地址：https://github.com/Return-Log/Education-Clock

        联系我：returnlog@outlook.com

        Copyright (C) 2024  Log
        """

        QMessageBox.about(self, "关于", about_text)

    def save_and_close(self):
        event = self.input_event.text()
        end_date = self.input_end_date.date().toString("yyyy-MM-dd")

        if event and end_date:
            try:
                with open("settings.txt", "w") as file:
                    file.write(f"{event}\n{end_date}")
                QMessageBox.information(self, "保存成功", "设置已保存！")
                self.accept()  # 关闭对话框
            except Exception as e:
                QMessageBox.warning(self, "保存失败", f"发生错误: {str(e)}")
        else:
            QMessageBox.warning(self, "保存失败", "请填写完整的设置！")


class DigitalClock(QWidget):
    def __init__(self):
        super().__init__()

        # 设置窗口为无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint)

        # 初始化窗口
        self.setWindowTitle('数字时钟')
        self.setGeometry(100, 100, 300, 200)  # 设置窗口位置和大小
        self.setStyleSheet("background-color: black; color: red;")  # 设置背景色和字体颜色

        # 创建垂直布局
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # 星期标签
        self.weekday_label = QLabel()
        self.weekday_label.setAlignment(Qt.AlignCenter)  # 居中对齐
        self.weekday_label.setStyleSheet("color: red; font: bold 35pt;")  # 设置黑体，字号35
        self.layout.addWidget(self.weekday_label)

        # 时间标签
        self.time_label = QLabel()
        self.time_label.setAlignment(Qt.AlignCenter)  # 居中对齐
        self.time_label.setStyleSheet("color: red; font: bold 60pt;")  # 设置黑体，字号50
        self.layout.addWidget(self.time_label)

        # 日期标签
        self.date_label = QLabel()
        self.date_label.setAlignment(Qt.AlignCenter)  # 居中对齐
        self.date_label.setStyleSheet("color: red; font: bold 35pt;")  # 设置黑体，字号35
        self.layout.addWidget(self.date_label)

        # 倒计时标签
        self.countdown_label = QLabel()
        self.countdown_label.setAlignment(Qt.AlignCenter)  # 居中对齐
        self.countdown_label.setStyleSheet("color: red; font: bold 35pt;")  # 设置黑体，字号35
        self.layout.addWidget(self.countdown_label)

        # 定时器，每秒更新一次时间
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

        # 更新时间显示
        self.update_time()

        # 连接双击事件到处理函数
        self.countdown_label.mouseDoubleClickEvent = self.edit_countdown

        # 用于记录鼠标按下时的位置
        self.drag_start_position = None

        # 加载窗口位置信息
        self.load_window_position()

        # 将窗口放到最底层
        self.raise_()

        # 创建并显示课程表窗口
        self.schedule_window = ClassSchedule()
        self.schedule_window.show()

    def update_time(self):
        # 获取当前日期和时间
        current_date = QDate.currentDate()
        current_time = QTime.currentTime()

        # 星期中文转换
        weekday_dict = {Qt.Monday: "星期一", Qt.Tuesday: "星期二", Qt.Wednesday: "星期三",
                        Qt.Thursday: "星期四", Qt.Friday: "星期五", Qt.Saturday: "星期六",
                        Qt.Sunday: "星期日"}
        weekday_chinese = weekday_dict[current_date.dayOfWeek()]

        # 日期中文格式
        date_chinese = "{0}年{1}月{2}日".format(current_date.year(),
                                                current_date.month(), current_date.day())

        # 更新显示
        self.weekday_label.setText(weekday_chinese)
        self.time_label.setText(current_time.toString("hh:mm:ss"))
        self.date_label.setText(date_chinese)

        # 计算并更新倒计时
        event, end_date = self.load_settings()
        days_left = current_date.daysTo(QDate.fromString(end_date, "yyyy-MM-dd"))
        days_left = max(0, days_left)  # 如果小于0，则显示为0
        self.countdown_label.setText(f"据{event}还剩{min(9999, days_left)}天")  # 最多显示9999天

    def load_settings(self):
        try:
            with open("settings.txt", "r") as file:
                event = file.readline().strip()
                end_date = file.readline().strip()
                return event, end_date
        except FileNotFoundError:
            return "事件", QDate.currentDate().addDays(7).toString("yyyy-MM-dd")

    def edit_countdown(self, event):
        # 双击事件，弹出设置窗口
        dialog = SettingsDialog(self)
        dialog.exec_()

    def mousePressEvent(self, event):
        # 记录鼠标按下时的位置
        self.drag_start_position = event.globalPos()

    def mouseMoveEvent(self, event):
        # 计算鼠标移动的距离
        if self.drag_start_position:
            delta = event.globalPos() - self.drag_start_position
            self.move(self.pos() + delta)
            self.drag_start_position = event.globalPos()

    def mouseReleaseEvent(self, event):
        # 清空记录的鼠标按下位置
        self.drag_start_position = None

    def closeEvent(self, event):
        self.save_window_position()
        event.accept()

    def load_window_position(self):
        # 从配置文件加载窗口位置信息
        settings = QSettings("CloudReturn", "clock")
        if settings.contains("window/position"):
            self.move(settings.value("window/position"))

    def save_window_position(self):
        # 保存窗口位置信息到配置文件
        settings = QSettings("CloudReturn", "clock")
        settings.setValue("window/position", self.pos())


if __name__ == '__main__':
    app = QApplication(sys.argv)
    clock = DigitalClock()
    clock.show()
    sys.exit(app.exec_())
