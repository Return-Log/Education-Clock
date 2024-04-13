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

import os
import sys
import json5
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtCore import Qt, QTimer, QDate, QTime, QPoint, QSettings


class ClassSchedule(QWidget):
    def __init__(self):
        super().__init__()

        # 初始化窗口设置
        self.setWindowTitle("电子课表")  # 设置窗口标题
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint)  # 设置窗口无边框并保持在底层
        self.setStyleSheet("background-color: black;")  # 设置背景颜色

        self.load_window_geometry()  # 加载窗口的位置和大小

        self.offset = QPoint()  # 用于窗口拖动的偏移量

        # 设置布局
        self.layout = QVBoxLayout(self)
        self.timer = QTimer(self)  # 初始化定时器
        self.timer.timeout.connect(self.update_course_schedule)  # 定时器超时连接到课程表更新函数

        self.show_schedule()  # 显示课程表

    def show_schedule(self):
        # 初始化课程信息的显示
        self.course_labels = []
        self.layout.setAlignment(Qt.AlignTop)  # 标签从顶部开始对齐
        self.layout.setSpacing(5)  # 设置标签间距
        self.update_course_schedule()  # 更新课程信息
        self.timer.start(10000)  # 定时器开始，间隔10秒

    def update_course_schedule(self):
        # 更新课程信息
        current_date = QDate.currentDate()
        current_time = QTime.currentTime()
        course_schedule = self.get_course_schedule(current_date)
        self.update_course_labels(current_time, course_schedule)

    def update_course_labels(self, current_time, course_schedule):
        # 更新显示的课程标签，并根据标签调整窗口大小
        max_width = 0
        total_height = 0

        for label in self.course_labels:
            label.deleteLater()  # 删除旧标签
        self.course_labels.clear()

        font = QFont("微软雅黑", 24, QFont.Bold)
        for course_name, start_time, end_time in course_schedule:
            label = QLabel(course_name[:2])  # 显示课程名的前两个字
            label.setAlignment(Qt.AlignCenter)  # 设置居中对齐
            label.setStyleSheet("color: red;")  # 设置字体颜色
            label.setFont(font)
            self.course_labels.append(label)
            self.layout.addWidget(label)

            # 计算标签宽度
            label_width = QFontMetrics(font).width(course_name[:2])
            max_width = max(max_width, label_width)
            total_height += label.sizeHint().height()

            # 设置当前课程高亮显示
            if self.is_between_times(current_time, start_time, end_time):
                label.setStyleSheet("color: white; background-color: green;")

        # 窗口宽度比最大标签宽度多二个字符
        extra_width = QFontMetrics(font).width("X")
        self.setFixedSize(max_width + extra_width, total_height)

    def is_between_times(self, current_time, start_time, end_time):
        # 判断当前时间是否在课程时间内
        return start_time <= current_time <= end_time

    def get_course_schedule(self, current_date):
        # 获取当前日期的课程安排
        current_day = current_date.dayOfWeek() - 1
        exe_dir = os.path.dirname(sys.argv[0])
        schedule_file = os.path.join(exe_dir, "schedule.json5")
        with open(schedule_file, "r", encoding="utf-8") as f:
            data = json5.load(f)

        course_schedule = data.get(str(current_day), [])
        for i, course_info in enumerate(course_schedule):
            # 将时间字符串转换为 QTime 对象
            start_time = QTime.fromString(course_info[1], "hh:mm")
            end_time = QTime.fromString(course_info[2], "hh:mm")
            course_schedule[i][1] = start_time
            course_schedule[i][2] = end_time

        return course_schedule

    def mousePressEvent(self, event):
        # 鼠标按下事件处理，用于窗口拖动
        if event.button() == Qt.LeftButton:
            self.offset = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event):
        # 鼠标移动事件处理，用于窗口拖动
        if event.buttons() & Qt.LeftButton:
            # 计算新位置并移动窗口
            newPos = event.globalPos() - self.offset
            self.move(newPos)

    def closeEvent(self, event):
        # 窗口关闭事件处理
        self.save_window_geometry()
        event.accept()

    def save_window_geometry(self):
        # 保存窗口位置和大小设置
        settings = QSettings("CloudReturn", "timetable")
        settings.setValue("window/geometry", self.saveGeometry())

    def load_window_geometry(self):
        # 加载窗口位置和大小设置
        settings = QSettings("CloudReturn", "timetable")
        if settings.contains("window/geometry"):
            self.restoreGeometry(settings.value("window/geometry"))



if __name__ == '__main__':
    app = QApplication(sys.argv)
    schedule_window = ClassSchedule()
    schedule_window.show()
    sys.exit(app.exec_())
