import json
from PyQt6.QtWidgets import QLabel, QMainWindow
from datetime import time, datetime
from PyQt6.QtCore import Qt

class TimetableModule:
    def __init__(self, main_window: QMainWindow):
        self.timetable = None
        self.main_window = main_window
        self.layout = main_window.verticalLayout_2  # 获取垂直布局
        self.comboBox = main_window.comboBox  # 获取 comboBox 对象
        self.labels = []
        self.load_timetable()

        # 使用 currentIndexChanged 信号，连接到槽函数
        self.comboBox.currentIndexChanged.connect(self.on_combobox_changed)
        self.update_timetable(datetime.now().time())  # 初始化时调用一次课程表更新

    def load_timetable(self):
        with open('data/timetable.json', 'r', encoding='utf-8') as file:
            self.timetable = json.load(file)

    # 定义槽函数，获取当前索引并更新课程表
    def on_combobox_changed(self):
        index = self.comboBox.currentIndex()  # 获取当前选中序号
        self.update_timetable(datetime.now().time(), index)  # 传递序号更新课程表

    def clear_layout(self):
        # 只清理课程表的 QLabel，保留 ComboBox 和弹簧
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget is not None and widget != self.comboBox:  # 确保不删除 comboBox
                if isinstance(widget, QLabel):  # 只删除 QLabel（课程表标签）
                    widget.deleteLater()

    def add_label(self, subject, start, end, is_intime):
        label = QLabel(f"{subject}")
        label.setProperty("timetable", "intime" if is_intime else "untimely")
        label.setStyleSheet(label.styleSheet())  # 应用样式
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 设置文本居中
        # 在弹簧之前插入课程表标签（顶部）
        self.layout.insertWidget(self.layout.count() - 2, label)
        self.labels.append(label)

    # 修改 update_timetable 函数，接收序号并更新课程表
    def update_timetable(self, current_time: time, selected_day_index: int = None):
        self.clear_layout()
        if selected_day_index is None:
            selected_day_index = self.comboBox.currentIndex()  # 如果没有传递索引，则获取当前选中序号

        days = ["无调休", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        # 根据索引获取对应的天数
        if selected_day_index >= 0 and selected_day_index < len(days):
            selected_day_name = days[selected_day_index]
        else:
            selected_day_name = days[0]  # 默认 "无调休"

        if selected_day_name == "无调休":
            selected_day_name = days[datetime.now().weekday() + 1]  # 如果选中 "无调休"，根据当前日期设置

        # 更新课程表显示
        if selected_day_name in self.timetable:
            for entry in self.timetable[selected_day_name]:
                subject, start_str, end_str = entry
                start = time.fromisoformat(start_str)
                end = time.fromisoformat(end_str)
                is_intime = start <= current_time < end
                self.add_label(subject, start_str, end_str, is_intime)