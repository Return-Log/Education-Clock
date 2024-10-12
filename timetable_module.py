import json
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import pyqtSlot
from datetime import time


class TimetableModule:
    def __init__(self, main_window: QMainWindow):
        self.main_window = main_window
        self.layout = main_window.verticalLayout_2
        self.comboBox = main_window.comboBox
        self.labels = []
        self.load_timetable()
        self.comboBox.currentTextChanged.connect(self.on_combobox_changed)
        self.update_timetable(datetime.now().time())

    def load_timetable(self):
        with open('data/timetable.json', 'r', encoding='utf-8') as file:
            self.timetable = json.load(file)

    @pyqtSlot(str)
    def on_combobox_changed(self, text):
        self.update_timetable(datetime.now().time())

    def clear_layout(self):
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

    def add_label(self, subject, start, end, is_intime):
        label = QLabel(f"{subject} {start} - {end}")
        label.setProperty("timetable", "intime" if is_intime else "untimely")
        label.setStyleSheet(label.styleSheet())  # 应用样式
        self.layout.addWidget(label)
        self.labels.append(label)

    def update_timetable(self, current_time: time):
        self.clear_layout()
        selected_day = self.comboBox.currentText()
        if selected_day == "无调休":
            selected_day = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][
                datetime.now().weekday()]

        if selected_day in self.timetable:
            for entry in self.timetable[selected_day]:
                subject, start_str, end_str = entry
                start = time.fromisoformat(start_str)
                end = time.fromisoformat(end_str)
                is_intime = start <= current_time < end
                self.add_label(subject, start_str, end_str, is_intime)