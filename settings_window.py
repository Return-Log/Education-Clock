
import logging
import re
import sys
import json
import os
from PyQt6.QtWidgets import (
    QDialog, QPushButton, QLabel, QFileDialog, QTextBrowser, QTabWidget,
    QTableWidgetItem, QMessageBox, QApplication
)
from PyQt6.uic import loadUi
from PyQt6.QtCore import QTimer, QDateTime

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.timetable_file = './data/timetable.json'
        self.timetable_data = {}  # Initialize an empty dictionary to hold timetable data
        self.load_timetable()  # Load the timetable data

    def setup_ui(self):
        loadUi('./ui/setting.ui', self)
        self.textBrowser.setStyleSheet(
            "background-color: black; color: green; font-family: 'Courier New', Courier, monospace;")
        self.tabWidget.currentChanged.connect(self.on_tab_changed)
        # 连接 tabWidget_2 的 currentChanged 信号
        self.tabWidget_2.currentChanged.connect(self.on_tab_changed_2)

        self.pushButton.clicked.connect(self.insert_row)
        self.pushButton_2.clicked.connect(self.delete_row)

    def on_tab_changed(self, index):
        if index == 6:
            self.init_streaming_text()

    def on_tab_changed_2(self, index):
        if 0 <= index <= 6:

            self.load_timetable_day(index)
        else:
            logging.warning(f"Unexpected tab index: {index}")

    def init_streaming_text(self):
        self.textBrowser.clear()
        software_info = [
            """                               
  ______    _                 _   _             
 |  ____|  | |               | | (_)            
 | |__   __| |_   _  ___ __ _| |_ _  ___  _ __  
 |  __| / _` | | | |/ __/ _` | __| |/ _ \\| '_ \\ 
 | |___| (_| | |_| | (_| (_| | |_| | (_) | | | |
 |______\\__,_|\\__,_|\\___\\__,_|\\__|_|\\___/|_| |_|
           / ____| |          | |               
          | |    | | ___   ___| | __            
          | |    | |/ _ \\ / __| |/ /            
          | |____| | (_) | (__|   <             
           \\_____|_|\\___/ \\___|_|\\_\\                      
            """,
            "欢迎使用本软件！",
            "版本: 3.3",
            "",
            "更新日志: ",
            " - 设置项可修改课程表",
            " - 修复公告板无网络时闪退问题",
            " - 增加运行稳定性",
            "",
            "日期: 2024/11/10",
            "项目仓库: https://github.com/Return-Log/Education-Clock",
            "本软件遵循CPL-3.0协议发布",
            "============================================",
            "Copyright © 2024  Log  All rights reserved.",
        ]
        software_info_str = "\n".join(software_info) + "\n"
        self.add_text_line(software_info_str, delay=1)

    def add_text_line(self, text, delay=1):
        self.target_text = text
        self.character_delay = delay
        self.current_index = 0
        self.print_next_character()

    def print_next_character(self):
        if self.current_index < len(self.target_text):
            current_char = self.target_text[self.current_index]
            cursor = self.textBrowser.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(current_char)
            self.textBrowser.setTextCursor(cursor)
            self.current_index += 1
            QTimer.singleShot(self.character_delay, self.print_next_character)
        else:
            cursor = self.textBrowser.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertHtml(
                "<br><a href='https://github.com/Return-Log/Education-Clock' style='color:green;'>GitHub仓库</a>")
            self.textBrowser.setTextCursor(cursor)

######################课程表设置##########################################################################################

    def load_timetable(self):
        """加载课表 JSON 文件内容到 timetable_data"""
        try:
            with open(self.timetable_file, 'r', encoding='utf-8') as f:
                self.timetable_data = json.load(f)
                logging.debug(f"Loaded timetable data: {self.timetable_data}")
            self.load_timetable_day(0)  # 默认加载星期一的课表
        except Exception as e:
            logging.error(f"加载课表失败: {e}")

    def load_timetable_day(self, day_index):
        """加载特定一天的课表到相应的 TableWidget"""
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_name = day_names[day_index]

        table_widget = getattr(self, f'tableWidget_{day_index + 1}', None)

        if not table_widget:
            logging.error(f"找不到 tableWidget_{day_index + 1}")
            return

        # 断开之前的连接
        try:
            table_widget.cellChanged.disconnect()
        except TypeError:
            pass

        # 设置列数
        table_widget.setColumnCount(3)  # 3 列：课程名称、开始时间、结束时间
        table_widget.setHorizontalHeaderLabels(['课程名称', '开始时间', '结束时间'])

        table_widget.setRowCount(0)

        # 确保 timetable_data 存在并包含当天数据
        if self.timetable_data and day_name in self.timetable_data:
            for row_idx, (subject, start, end) in enumerate(self.timetable_data[day_name]):
                table_widget.insertRow(row_idx)

                table_widget.setItem(row_idx, 0, QTableWidgetItem(subject))  # 课程名称
                table_widget.setItem(row_idx, 1, QTableWidgetItem(start))  # 开始时间
                table_widget.setItem(row_idx, 2, QTableWidgetItem(end))  # 结束时间
                logging.debug(f"Inserted row for {day_name}: {subject}, {start}, {end}")
            logging.info(f"{day_name}的课程表已加载。")
        else:
            logging.warning(f"{day_name} 的课程表不存在。")

        table_widget.cellChanged.connect(lambda: self.save_timetable(day_name))  # 恢复信号连接

    def insert_row(self):
        current_table = self.get_current_table()
        if not current_table:
            return

        # 如果当前表格没有行，则直接添加一行
        if current_table.rowCount() == 0:
            current_table.insertRow(0)
            self.populate_new_row(current_table, 0)
        else:
            # 否则，在当前选中的行之后插入一行
            row = current_table.currentRow()
            if row == -1:
                QMessageBox.warning(self, "警告", "请先选择一行")
                return
            current_table.insertRow(row + 1)
            self.populate_new_row(current_table, row + 1)

        self.save_timetable(self.get_current_day_name())  # 保存课表

    def populate_new_row(self, table, row):
        table.setItem(row, 0, QTableWidgetItem("课程"))  # 课程名称
        table.setItem(row, 1, QTableWidgetItem("10:24"))  # 开始时间
        table.setItem(row, 2, QTableWidgetItem("10:24"))  # 结束时间

    def delete_row(self):
        current_table = self.get_current_table()
        if not current_table:
            return

        row = current_table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "警告", "请先选择一行")
            return
        current_table.removeRow(row)
        self.save_timetable(self.get_current_day_name())  # 保存课表

    def save_timetable(self, day_name):
        current_table = self.get_current_table()
        if not current_table:
            return
        updated_day_data = []
        for row in range(current_table.rowCount()):
            subject_item = current_table.item(row, 0)
            start_item = current_table.item(row, 1)
            end_item = current_table.item(row, 2)

            if subject_item and start_item and end_item:
                subject = subject_item.text()
                start = start_item.text()
                end = end_item.text()

                # 验证时间格式
                if not self.validate_time_format(start) or not self.validate_time_format(end):
                    QMessageBox.warning(self, "警告", "时间格式不正确，请使用 hh:mm 格式。")
                    return

                updated_day_data.append([subject, start, end])
        self.timetable_data[day_name] = updated_day_data
        with open(self.timetable_file, 'w', encoding='utf-8') as f:
            json.dump(self.timetable_data, f, ensure_ascii=False, indent=4)
        logging.info(f"{day_name}的课表已保存。")

    def validate_time_format(self, time_str):
        """验证时间格式是否为 hh:mm"""
        return bool(re.match(r'^\d{2}:\d{2}$', time_str))

    def get_current_table(self):
        day_index = self.tabWidget_2.currentIndex()
        if 0 <= day_index < 7:
            return getattr(self, f'tableWidget_{day_index + 1}', None)
        return None

    def get_current_day_name(self):
        day_index = self.tabWidget_2.currentIndex()
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        if 0 <= day_index < 7:
            return day_names[day_index]
        return None

    def closeEvent(self, event):
        QMessageBox.information(self, "重启", "设置已更改，重启应用程序以应用更改。")
        python = sys.executable
        os.execl(python, python, *sys.argv)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    with open('data/qss.qss', 'r', encoding="utf-8") as f:
        app.setStyleSheet(f.read())
    window = SettingsWindow()
    window.show()
    sys.exit(app.exec())