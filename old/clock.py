import os
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QDateEdit, QPushButton, QDialog, \
    QMessageBox
from PyQt6.QtCore import Qt, QTimer, QDate, QSettings, QTime
from PyQt6.QtGui import QFont


# 确保data文件夹存在
data_folder = "data"
if not os.path.exists(data_folder):
    os.makedirs(data_folder)

# 保存倒计时信息的文件路径
time_file_path = os.path.join(data_folder, "[倒计时设置]time.txt")

# 保存窗口位置信息的文件路径
settings_file_path = os.path.join(data_folder, "[时钟窗口位置]settings.ini")


class SettingsDialog(QDialog):
    """用于倒计时设置的对话框类"""
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle('设置倒计时')
        self.setGeometry(200, 200, 300, 200)

        self.layout = QVBoxLayout()  # 垂直布局
        self.setLayout(self.layout)

        # 事件标签和输入框
        self.label_event = QLabel("事件:")
        self.layout.addWidget(self.label_event)
        self.input_event = QLineEdit()
        self.input_event.setMaxLength(2)  # 设置最大长度为2
        self.layout.addWidget(self.input_event)

        # 截止日期标签和日期输入框
        self.label_end_date = QLabel("截止日期:")
        self.layout.addWidget(self.label_end_date)
        self.input_end_date = QDateEdit()
        self.input_end_date.setCalendarPopup(True)  # 弹出日历
        self.layout.addWidget(self.input_end_date)

        # 保存按钮
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_and_close)  # 绑定保存事件
        self.layout.addWidget(self.save_button)

    def save_and_close(self):
        """保存输入的事件和截止日期到文件"""
        event = self.input_event.text()
        end_date = self.input_end_date.date().toString("yyyy-MM-dd")

        if event and end_date:
            try:
                with open(time_file_path, "w", encoding="utf-8") as file:
                    file.write(f"Event={event}\nEndDate={end_date}")
                QMessageBox.information(self, "保存成功", "设置已保存！")
                self.accept()  # 关闭对话框
            except Exception as e:
                QMessageBox.warning(self, "保存失败", f"发生错误: {str(e)}")
        else:
            QMessageBox.warning(self, "保存失败", "请填写完整的设置！")


class DigitalClock(QWidget):
    """数字时钟窗口类"""
    def __init__(self):
        super().__init__()

        # 设置窗口为无边框
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        # 初始化窗口
        self.setWindowTitle('数字时钟')
        self.setGeometry(100, 100, 300, 200)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnBottomHint)  # 设置无边框并置底
        self.setStyleSheet("background-color: black; color: red;")  # 设置背景色和字体颜色

        # 创建垂直布局
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # 创建字体对象
        bold_font = QFont("黑体", 26, QFont.Weight.Bold)

        # 星期标签
        self.weekday_label = QLabel("星期")
        self.weekday_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.weekday_label.setFont(bold_font)
        self.weekday_label.setStyleSheet("color: red;")
        self.layout.addWidget(self.weekday_label)

        # 时间标签
        self.time_label = QLabel("时间")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_font = QFont("黑体", 45, QFont.Weight.Bold)
        self.time_label.setFont(time_font)
        self.time_label.setStyleSheet("color: red;")
        self.layout.addWidget(self.time_label)

        # 日期标签
        self.date_label = QLabel("日期")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.date_label.setFont(bold_font)
        self.date_label.setStyleSheet("color: red;")
        self.layout.addWidget(self.date_label)

        # 倒计时标签
        self.countdown_label = QLabel("倒计时")
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.countdown_label.setFont(bold_font)
        self.countdown_label.setStyleSheet("color: red;")
        self.layout.addWidget(self.countdown_label)

        # 定时器，每秒更新一次时间
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

        # 更新时间显示
        self.update_time()

        # 双击事件绑定
        self.countdown_label.mouseDoubleClickEvent = self.edit_countdown

        # 鼠标拖动支持
        self.drag_start_position = None

        # 加载窗口位置信息
        self.load_window_position()

        # 将窗口放到最底层
        self.raise_()

    def update_time(self):
        """更新时间、日期、倒计时的显示"""
        current_date = QDate.currentDate()  # 当前日期
        current_time = QTime.currentTime()  # 当前时间

        # 星期的中文转换
        # 星期的中文转换
        weekday_dict = {
            1: "星期一",  # 周一
            2: "星期二",  # 周二
            3: "星期三",  # 周三
            4: "星期四",  # 周四
            5: "星期五",  # 周五
            6: "星期六",  # 周六
            7: "星期日"  # 周日
        }

        weekday_chinese = weekday_dict[current_date.dayOfWeek()]

        # 中文格式的日期
        date_chinese = f"{current_date.year()}年{current_date.month()}月{current_date.day()}日"

        # 更新标签的显示内容
        self.weekday_label.setText(weekday_chinese)
        self.time_label.setText(current_time.toString("hh:mm:ss"))
        self.date_label.setText(date_chinese)

        # 更新倒计时
        event, end_date = self.load_settings()
        days_left = current_date.daysTo(QDate.fromString(end_date, "yyyy-MM-dd"))
        days_left = max(0, days_left)  # 如果日期过期则显示为0天
        self.countdown_label.setText(f"距{event}还剩{min(9999, days_left)}天")  # 最多显示9999天

    def load_settings(self):
        """从文件加载事件和截止日期"""
        try:
            with open(time_file_path, "r", encoding="utf-8") as file:
                lines = file.readlines()
                event = lines[0].split("=")[1].strip()
                end_date = lines[1].split("=")[1].strip()
                return event, end_date
        except Exception as e:
            print(f"加载设置时出错: {e}")
            return "事件", QDate.currentDate().addDays(7).toString("yyyy-MM-dd")

    def edit_countdown(self, event):
        """双击倒计时标签时，弹出设置对话框"""
        dialog = SettingsDialog(self)
        dialog.exec()

    def mousePressEvent(self, event):
        """记录鼠标按下的位置，用于拖动窗口"""
        self.drag_start_position = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        """拖动窗口"""
        if self.drag_start_position:
            delta = event.globalPosition().toPoint() - self.drag_start_position
            self.move(self.pos() + delta)
            self.drag_start_position = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        """释放鼠标按键时清空位置记录"""
        self.drag_start_position = None

    def closeEvent(self, event):
        """窗口关闭时保存位置"""
        self.save_window_position()
        event.accept()

    def load_window_position(self):
        """从文件加载窗口位置信息"""
        try:
            settings = QSettings(settings_file_path, QSettings.Format.IniFormat)
            pos = settings.value("window/position", self.pos())
            self.move(pos)
        except Exception as e:
            print(f"加载窗口位置时出错: {e}")

    def save_window_position(self):
        """保存窗口位置信息到文件"""
        try:
            settings = QSettings(settings_file_path, QSettings.Format.IniFormat)
            settings.setValue("window/position", self.pos())
        except Exception as e:
            print(f"保存窗口位置时出错: {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    clock = DigitalClock()
    clock.show()
    sys.exit(app.exec())
