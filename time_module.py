# time_module.py
import json
from PyQt6.QtWidgets import QLabel, QVBoxLayout
from PyQt6.QtCore import QTimer, QPropertyAnimation, Qt, QRect
from datetime import datetime, timedelta

class TimeModule:
    def __init__(self, main_window):
        self.main_window = main_window
        self.time_label = main_window.findChild(QLabel, "label_4")
        self.date_label = main_window.findChild(QLabel, "label")
        self.week_label = main_window.findChild(QLabel, "label_5")
        self.enddate_label = main_window.findChild(QLabel, "label_3")

        # 设置属性
        self.time_label.setProperty("time", "time")
        self.week_label.setProperty("time", "week")
        self.date_label.setProperty("time", "date")
        self.enddate_label.setProperty("time", "enddate")

        # 星期名称的映射
        self.weekday_map = {
            "Monday": "星期一",
            "Tuesday": "星期二",
            "Wednesday": "星期三",
            "Thursday": "星期四",
            "Friday": "星期五",
            "Saturday": "星期六",
            "Sunday": "星期日"
        }

        # 定时器每秒更新时间
        self.time_update_timer = QTimer(self.main_window)
        self.time_update_timer.timeout.connect(self.update_time)
        self.time_update_timer.start(1000)

        # 定时器每分钟检测 JSON 文件是否更新
        self.json_update_timer = QTimer(self.main_window)
        self.json_update_timer.timeout.connect(self.load_enddate)
        self.json_update_timer.start(60000)

        # 初始加载倒计时信息
        self.load_enddate()

    def update_time(self):
        """更新时间和日期显示"""
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        current_date = now.strftime("%Y-%m-%d")
        current_weekday = now.strftime("%A")  # 获取英文星期名称

        # 将英文星期名称转换为中文
        current_weekday_chinese = self.weekday_map.get(current_weekday, "未知")

        self.time_label.setText(current_time)
        self.date_label.setText(current_date)
        self.week_label.setText(current_weekday_chinese)

    def load_enddate(self):
        """加载倒计时信息并更新 label_3"""
        try:
            with open('data/time.json', 'r', encoding='utf-8') as file:
                data = json.load(file)
                event = data.get('event', '')
                enddate_str = data.get('enddate', '')

                if enddate_str:
                    enddate = datetime.strptime(enddate_str, "%Y-%m-%d")
                    now = datetime.now()
                    remaining_days = (enddate - now).days

                    if remaining_days > 0:
                        message = f"距{event}还剩{remaining_days}天"
                    else:
                        message = f"{event}已经过去"

                    self.enddate_label.setText(message)

                else:
                    self.enddate_label.setText("无倒计时信息")
        except (FileNotFoundError, json.JSONDecodeError):
            self.enddate_label.setText("无法加载倒计时信息")

    def animate_text(self, label, text):
        """动画滚动显示文本"""
        if len(text) * 10 > label.width():  # 如果文本长度超过标签宽度
            self.animation = QPropertyAnimation(label, b"geometry")
            self.animation.setDuration(5000)
            self.animation.setStartValue(QRect(label.geometry().x(), label.geometry().y(), label.width(), label.height()))
            self.animation.setEndValue(QRect(-label.width(), label.geometry().y(), label.width(), label.height()))
            self.animation.setLoopCount(-1)  # 无限循环
            self.animation.start()
        else:
            self.animation = None