import os
import sys
import json5
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtCore import Qt, QTimer, QDate, QTime, QPoint, QSettings


class DutyRoster(QWidget):
    def __init__(self):
        super().__init__()

        # 初始化窗口设置
        self.setWindowTitle("值班表")  # 设置窗口标题
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint)  # 设置窗口无边框并保持在底层
        self.setStyleSheet("background-color: black;")  # 设置背景颜色

        self.load_window_geometry()  # 加载窗口的位置和大小

        self.offset = QPoint()  # 用于窗口拖动的偏移量

        # 设置布局
        self.layout = QVBoxLayout(self)
        self.timer = QTimer(self)  # 初始化定时器
        self.timer.timeout.connect(self.update_duty_schedule)  # 定时器超时连接到值班表更新函数

        self.show_schedule()  # 显示值班表

    def show_schedule(self):
        # 初始化值班信息的显示
        self.duty_labels = []
        self.layout.setAlignment(Qt.AlignTop)  # 标签从顶部开始对齐
        self.layout.setSpacing(5)  # 设置标签间距
        self.update_duty_schedule()  # 更新值班信息
        self.timer.start(10000)  # 定时器开始，间隔10秒

    def update_duty_schedule(self):
        # 更新值班信息
        current_date = QDate.currentDate()
        current_time = QTime.currentTime()
        duty_schedule = self.get_duty_schedule(current_date)
        self.update_duty_labels(current_time, duty_schedule)

    def update_duty_labels(self, current_time, duty_schedule):
        # 更新显示的值班标签，并根据标签调整窗口大小
        max_width = 0
        total_height = 0

        for label in self.duty_labels:
            label.deleteLater()  # 删除旧标签
        self.duty_labels.clear()

        font = QFont("bold", 18, QFont.Bold)
        for person, start_time, end_time in duty_schedule:
            label = QLabel(person)
            label.setAlignment(Qt.AlignCenter)  # 设置居中对齐
            label.setStyleSheet("color: red;")  # 设置字体颜色
            label.setFont(font)
            self.duty_labels.append(label)
            self.layout.addWidget(label)

            # 计算标签宽度
            label_width = QFontMetrics(font).width(person)
            max_width = max(max_width, label_width)
            total_height += label.sizeHint().height()

            # 设置当前值班人员高亮显示
            if self.is_between_times(current_time, start_time, end_time):
                label.setStyleSheet("color: white; background-color: green;")

        # 窗口宽度比最大标签宽度多二个字符
        extra_width = QFontMetrics(font).width("X")
        self.setFixedSize(max_width + extra_width, total_height)

    def is_between_times(self, current_time, start_time, end_time):
        # 判断当前时间是否在值班时间内
        return start_time <= current_time <= end_time

    def get_duty_schedule(self, current_date):
        # 获取当前日期的值班安排
        current_day = current_date.dayOfWeek() - 1
        exe_dir = os.path.dirname(sys.argv[0])
        schedule_file = os.path.join(exe_dir, "duty_schedule.json5")
        with open(schedule_file, "r", encoding="utf-8") as f:
            data = json5.load(f)

        duty_schedule = data.get(str(current_day), [])
        for i, duty_info in enumerate(duty_schedule):
            # 将时间字符串转换为 QTime 对象
            start_time = QTime.fromString(duty_info[1], "hh:mm")
            end_time = QTime.fromString(duty_info[2], "hh:mm")
            duty_schedule[i][1] = start_time
            duty_schedule[i][2] = end_time

        return duty_schedule

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
        settings = QSettings("CloudReturn", "dutyroster")
        settings.setValue("window/geometry", self.saveGeometry())

    def load_window_geometry(self):
        # 加载窗口位置和大小设置
        settings = QSettings("CloudReturn", "dutyroster")
        if settings.contains("window/geometry"):
            self.restoreGeometry(settings.value("window/geometry"))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    duty_roster_window = DutyRoster()
    duty_roster_window.show()
    sys.exit(app.exec_())
