import os
import sys
import json5
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QSlider, QDialog
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer, QDate, QTime, QPoint, QSettings

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(200, 100)

        # 添加窗口大小标签
        self.label_window_size = QLabel("窗口大小:")
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label_window_size)

        # 添加拖动条
        self.resize_slider = QSlider(Qt.Horizontal)
        self.resize_slider.setRange(100, 1200)  # 设置最小值和最大值
        self.resize_slider.setValue(300)  # 设置默认值
        self.resize_slider.setTickPosition(QSlider.TicksBelow)
        self.resize_slider.setTickInterval(50)
        self.resize_slider.valueChanged.connect(self.resize_main_window)
        self.layout.addWidget(self.resize_slider)

        self.setLayout(self.layout)

    def resize_main_window(self, value):
        # 调整主窗口大小
        self.parent().resize(value, value // 2)  # 假设主窗口宽高比为2:1，你可以根据实际情况调整


class ClassSchedule(QWidget):
    def __init__(self):
        super().__init__()

        # 设置窗口属性
        self.setWindowTitle("电子课表")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint)  # 将窗口置于桌面最下层
        self.setStyleSheet("background-color: black;")

        # 加载窗口位置和大小信息
        self.load_window_geometry()

        # 记录鼠标按下时的位置和窗口位置的差值
        self.offset = QPoint()

        # 设置布局
        layout = QVBoxLayout()
        self.setLayout(layout)

        # 添加课程信息标签
        self.course_labels = []
        for i in range(12):  # 假设一天最多有12节课
            label = QLabel(" " * 4)  # 初始化为空标签，窄两个字符
            label.setAlignment(Qt.AlignCenter)  # 设置居中对齐
            label.setStyleSheet("color: red;")
            label.setFont(QFont("微软雅黑", 14, QFont.Bold))  # 设置字体为微软雅黑
            self.course_labels.append(label)
            layout.addWidget(label)

        # 更新课程信息
        self.update_course_schedule()

        # 设置定时器，每秒更新一次课程信息
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_course_schedule)
        self.timer.start(1000)

    def update_course_schedule(self):
        # 获取当前日期和时间
        current_date = QDate.currentDate()
        current_time = QTime.currentTime()

        # 获取当天的课程信息
        course_schedule = self.get_course_schedule(current_date)

        # 更新课程信息标签
        for i, (course_name, start_time, end_time) in enumerate(course_schedule):
            if i >= len(self.course_labels):  # 超出课程信息标签数量的课程信息不显示
                break
            label = self.course_labels[i]

            # 设置标签文本为课程名称，截断名称以确保不超过2个字符
            label.setText(course_name[:2])

            # 检查当前时间是否在课程时间范围内，并根据结果设置标签的样式
            if self.is_between_times(current_time, start_time, end_time):
                label.setStyleSheet("color: white; background-color: green;")  # 设置高亮显示
            else:
                label.setStyleSheet("color: red;")  # 恢复原始样式

    # 辅助函数，检查当前时间是否在指定的时间范围内
    def is_between_times(self, current_time, start_time, end_time):
        return start_time <= current_time <= end_time

    # 辅助函数，获取当天的课程信息
    def get_course_schedule(self, current_date):
        # 获取星期几，假设星期一为0，星期日为6
        current_day = current_date.dayOfWeek() - 1

        # 读取课程表文件，假设文件名为 schedule.json5
        schedule_file = os.path.join(os.path.dirname(__file__), "schedule.json5")
        with open(schedule_file, "r", encoding="utf-8") as f:  # 使用 UTF-8 编码打开文件
            data = json5.load(f)

        # 解析课程信息
        course_schedule = data.get(str(current_day), [])

        # 转换时间字符串为 QTime 对象
        for course_info in course_schedule:
            course_info[1] = QTime.fromString(course_info[1], "hh:mm")  # 起始时间
            course_info[2] = QTime.fromString(course_info[2], "hh:mm")  # 结束时间

        return course_schedule

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 计算鼠标按下时的位置和窗口位置的差值
            self.offset = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            # 更新窗口位置
            self.move(event.globalPos() - self.offset)

    def mouseDoubleClickEvent(self, event):
        # 双击事件，弹出设置窗口
        dialog = SettingsDialog(self)
        dialog.exec_()

    def resizeEvent(self, event):
        # 根据窗口大小调整标签字体大小，并保持比例
        font_size = max(8, min(self.width() // 6, self.height() // 6))  # 字体大小与窗口大小保持一定比例
        font = QFont("微软雅黑", font_size)
        for label in self.course_labels:
            label.setFont(font)

    def closeEvent(self, event):
        self.save_window_geometry()
        event.accept()

    def save_window_geometry(self):
        # 保存窗口位置和大小信息到配置文件
        settings = QSettings("CloudReturn", "timetable")
        settings.setValue("window/geometry", self.saveGeometry())

    def load_window_geometry(self):
        # 从配置文件加载窗口位置和大小信息
        settings = QSettings("CloudReturn", "timetable")
        if settings.contains("window/geometry"):
            self.restoreGeometry(settings.value("window/geometry"))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    schedule_window = ClassSchedule()
    schedule_window.show()
    sys.exit(app.exec_())
