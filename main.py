import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QDateEdit, QPushButton, QDialog, \
    QMessageBox, QSlider
from PyQt5.QtCore import Qt, QTimer, QDate, QTime, QPoint, QSettings
from PyQt5.QtGui import QFont
# 导入timetable.py中的ClassSchedule类
from timetable import ClassSchedule


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle('设置倒计时')
        self.setGeometry(200, 200, 300, 150)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # 添加窗口大小标签
        self.label_window_size = QLabel("窗口大小:")
        self.layout.addWidget(self.label_window_size)

        # 添加拖动条
        self.resize_slider = QSlider(Qt.Horizontal)
        self.resize_slider.setRange(100, 2400)  # 设置最小值和最大值
        self.resize_slider.setValue(300)  # 设置默认值
        self.resize_slider.setTickPosition(QSlider.TicksBelow)
        self.resize_slider.setTickInterval(50)
        self.resize_slider.valueChanged.connect(self.resize_main_window)
        self.layout.addWidget(self.resize_slider)

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

    def resize_main_window(self, value):
        # 调整主窗口大小
        self.parent().resize(value, value // 2)  # 假设主窗口宽高比为2:1，你可以根据实际情况调整


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
        self.weekday_label.setStyleSheet("color: red;")
        self.layout.addWidget(self.weekday_label)

        # 时间标签
        self.time_label = QLabel()
        self.time_label.setAlignment(Qt.AlignCenter)  # 居中对齐
        self.time_label.setStyleSheet("color: red;")
        self.layout.addWidget(self.time_label)

        # 日期标签
        self.date_label = QLabel()
        self.date_label.setAlignment(Qt.AlignCenter)  # 居中对齐
        self.date_label.setStyleSheet("color: red;")
        self.layout.addWidget(self.date_label)

        # 倒计时标签
        self.countdown_label = QLabel()
        self.countdown_label.setAlignment(Qt.AlignCenter)  # 居中对齐
        self.countdown_label.setStyleSheet("color: red;")
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

        # 加载窗口位置和大小信息
        self.load_window_position()
        self.load_window_size()

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
        self.save_window_size()
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

    def load_window_size(self):
        # 从配置文件加载窗口大小信息
        settings = QSettings("CloudReturn", "clock")
        if settings.contains("window/size"):
            self.resize(settings.value("window/size"))

    def save_window_size(self):
        # 保存窗口大小信息到配置文件
        settings = QSettings("CloudReturn", "clock")
        settings.setValue("window/size", self.size())

    def resizeEvent(self, event):
        # 根据窗口大小调整标签字体大小，并保持比例
        font_size = max(12, self.width() // 18)  # 根据窗口宽度动态调整字体大小
        font = QFont("Arial", font_size)

        # 设置各个标签的字体大小
        self.weekday_label.setFont(font)
        self.time_label.setFont(QFont("Arial", font_size + 16))  # 时间标签字体大小增加12
        self.date_label.setFont(font)
        self.countdown_label.setFont(font)

        super().resizeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    clock = DigitalClock()
    clock.show()
    sys.exit(app.exec_())
