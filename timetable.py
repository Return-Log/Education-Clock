"""
https://github.com/Return-Log/Education-Clock
GPL-3.0 license
coding: UTF-8
"""

import os
import sys
import json5
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtGui import QFont, QFontMetrics
from PyQt6.QtCore import Qt, QTimer, QDate, QTime, QPoint, QSettings


class ClassSchedule(QWidget):
    def __init__(self):
        super().__init__()

        # 初始化窗口设置
        self.setWindowTitle("课程表")  # 设置窗口标题
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnBottomHint)  # 设置窗口无边框并保持在底层
        self.setStyleSheet("background-color: black;")  # 设置背景颜色

        self.load_window_geometry()  # 加载窗口的位置和大小

        self.offset = QPoint()  # 用于窗口拖动的偏移量

        # 设置布局
        self.layout = QVBoxLayout(self)
        self.timer = QTimer(self)  # 初始化定时器
        self.timer.timeout.connect(self.update_course_schedule)  # 定时器超时连接到课程表更新函数

        self.show_schedule()  # 显示课程表

    def show_schedule(self):
        """初始化并显示课程表信息"""
        self.course_labels = []  # 保存显示的课程标签
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # 标签从顶部开始对齐
        self.layout.setSpacing(5)  # 设置标签间距
        self.update_course_schedule()  # 更新课程信息
        self.timer.start(10000)  # 每10秒更新一次课程表

    def update_course_schedule(self):
        """定时器触发时，更新当前日期和时间的课程表"""
        current_date = QDate.currentDate()  # 获取当前日期
        current_time = QTime.currentTime()  # 获取当前时间
        course_schedule = self.get_course_schedule(current_date)  # 获取当前日期的课程表
        self.update_course_labels(current_time, course_schedule)  # 更新课程标签

    def update_course_labels(self, current_time, course_schedule):
        """根据当前时间和课程表更新课程标签，并调整窗口大小"""
        max_width = 0  # 记录标签的最大宽度
        total_height = 0  # 记录所有标签的总高度

        for label in self.course_labels:
            label.deleteLater()  # 删除旧标签
        self.course_labels.clear()  # 清空旧标签列表

        font = QFont("微软雅黑", 24, QFont.Weight.Bold)  # 设置字体
        for course_name, start_time, end_time in course_schedule:
            label = QLabel(course_name[:2])  # 仅显示课程名称的前两个字
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 设置居中对齐
            label.setStyleSheet("color: red;")  # 设置字体颜色为红色
            label.setFont(font)  # 应用字体
            self.course_labels.append(label)  # 将标签添加到列表
            self.layout.addWidget(label)  # 将标签添加到布局中

            # 计算标签宽度，确保窗口宽度足够容纳最大标签
            label_width = QFontMetrics(font).horizontalAdvance(course_name[:2])
            max_width = max(max_width, label_width)
            total_height += label.sizeHint().height()

            # 设置当前时间的课程高亮显示
            if self.is_between_times(current_time, start_time, end_time):
                label.setStyleSheet("color: black; background-color: red;")  # 当前课程以红色背景显示

        # 调整窗口大小以适应标签内容
        extra_width = QFontMetrics(font).horizontalAdvance("X")  # 额外宽度，用于防止内容溢出
        self.setFixedSize(max_width + extra_width, total_height)  # 根据标签最大宽度和总高度设置窗口大小

    def is_between_times(self, current_time, start_time, end_time):
        """判断当前时间是否在课程时间范围内"""
        return start_time <= current_time <= end_time  # 返回布尔值，判断当前时间是否在课程时间范围内

    def get_course_schedule(self, current_date):
        """从文件中获取当前日期的课程表"""
        current_day = current_date.dayOfWeek() - 1  # 获取当前日期对应的星期几
        exe_dir = os.path.dirname(sys.argv[0])  # 获取程序的执行路径
        data_dir = os.path.join(exe_dir, "data")  # 课程表文件所在目录
        schedule_file = os.path.join(data_dir, "[课程表]schedule.json5")  # 课程表文件路径
        with open(schedule_file, "r", encoding="utf-8") as f:
            data = json5.load(f)  # 使用json5解析课程表文件

        course_schedule = data.get(str(current_day), [])  # 根据当前星期几获取对应的课程表
        for i, course_info in enumerate(course_schedule):
            # 将时间字符串转换为 QTime 对象
            start_time = QTime.fromString(course_info[1], "hh:mm")
            end_time = QTime.fromString(course_info[2], "hh:mm")
            course_schedule[i][1] = start_time  # 更新课程表中的开始时间
            course_schedule[i][2] = end_time  # 更新课程表中的结束时间

        return course_schedule  # 返回当前日期的课程表

    def mousePressEvent(self, event):
        """鼠标按下事件，用于实现窗口拖动"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.offset = event.globalPosition().toPoint() - self.pos()  # 记录鼠标按下时窗口与鼠标的位置偏移量

    def mouseMoveEvent(self, event):
        """鼠标移动事件，用于实现窗口拖动"""
        if event.buttons() & Qt.MouseButton.LeftButton:
            # 计算新位置并移动窗口
            new_pos = event.globalPosition().toPoint() - self.offset
            self.move(new_pos)

    def closeEvent(self, event):
        """窗口关闭事件，保存窗口位置和大小设置"""
        self.save_window_geometry()  # 保存当前窗口的几何信息
        event.accept()

    def save_window_geometry(self):
        """保存窗口位置和大小到配置文件"""
        settings = QSettings("CloudReturn", "timetable")
        settings.setValue("window/geometry", self.saveGeometry())  # 将当前窗口几何信息保存到配置文件

    def load_window_geometry(self):
        """从配置文件中加载窗口位置和大小"""
        settings = QSettings("CloudReturn", "timetable")
        if settings.contains("window/geometry"):
            self.restoreGeometry(settings.value("window/geometry"))  # 恢复之前保存的窗口几何信息


if __name__ == '__main__':
    app = QApplication(sys.argv)
    schedule_window = ClassSchedule()  # 实例化课程表窗口
    schedule_window.show()  # 显示窗口
    sys.exit(app.exec())  # 启动应用程序事件循环
