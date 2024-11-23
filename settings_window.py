
import logging
import re
import sys
import json
import base64
import os
from PyQt6.QtWidgets import (
    QDialog, QPushButton, QLabel, QFileDialog, QTextBrowser, QTabWidget,
    QTableWidgetItem, QMessageBox, QApplication
)
from PyQt6.uic import loadUi
from PyQt6.QtCore import QTimer, QDateTime

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.timetable_file = './data/timetable.json'
        self.db_config_file = './data/db_config.json'
        self.encryption_key = 0x5A  # 选择一个简单的密钥
        self.timetable_data = {}  # 初始化一个空字典以保存时间表数据
        self.load_timetable()  # 加载时刻表数据
        self.load_db_config()  # 加载数据库配置

    def setup_ui(self):
        loadUi('./ui/setting.ui', self)
        self.textBrowser.setStyleSheet(
            "background-color: black; color: green; font-family: 'Courier New', Courier, monospace;")
        self.tabWidget.currentChanged.connect(self.on_tab_changed)
        # 连接 tabWidget_2 的 currentChanged 信号
        self.tabWidget_2.currentChanged.connect(self.on_tab_changed_2)
        self.pushButton.clicked.connect(self.insert_row)
        self.pushButton_2.clicked.connect(self.delete_row)
        self.connect_line_edit_signals()

    def on_tab_changed(self, index):
        if index == 3:  # 假设 tab_4 的索引是 3
            self.load_db_config()
        elif index == 6:
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
            "本软件遵循GPL-3.0协议发布",
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

#####################################通知栏设置################################################################
    def xor_encrypt_decrypt(self, data, key):
        """XOR 加密/解密函数"""
        return bytes([b ^ key for b in data])

    def encrypt_data(self, data, key):
        """加密数据"""
        json_data = json.dumps(data, ensure_ascii=False, indent=4).encode('utf-8')
        encrypted_data = self.xor_encrypt_decrypt(json_data, key)
        return base64.b64encode(encrypted_data).decode('utf-8')

    def decrypt_data(self, encrypted_data, key):
        """解密数据"""
        decoded_data = base64.b64decode(encrypted_data.encode('utf-8'))
        decrypted_data = self.xor_encrypt_decrypt(decoded_data, key)
        return json.loads(decrypted_data.decode('utf-8'))

    def load_db_config(self):
        try:
            with open(self.db_config_file, 'r', encoding='utf-8') as f:
                encrypted_data = f.read()
                config = self.decrypt_data(encrypted_data, self.encryption_key)
                db_config = config['db_config']
                filter_conditions = config['filter_conditions']

                self.lineEdit_3.setText(db_config['host'])
                self.lineEdit_4.setText(str(db_config['port']))
                self.lineEdit_5.setText(db_config['user'])
                self.lineEdit_6.setText(db_config['password'])
                self.lineEdit_7.setText(db_config['database'])

                self.lineEdit_8.setText(','.join(filter_conditions['robot_names']))
                self.lineEdit_9.setText(','.join(filter_conditions['sender_names']))
                self.lineEdit_10.setText(','.join(filter_conditions['conversation_titles']))

                logging.debug("Database configuration loaded.")
        except Exception as e:
            logging.error(f"Failed to load database configuration: {e}")

    def connect_line_edit_signals(self):
        line_edits = [self.lineEdit_3, self.lineEdit_4, self.lineEdit_5, self.lineEdit_6, self.lineEdit_7,
                      self.lineEdit_8, self.lineEdit_9, self.lineEdit_10]
        for line_edit in line_edits:
            line_edit.textChanged.connect(self.on_line_edit_text_changed)

    def on_line_edit_text_changed(self):
        # 替换中文逗号为英文逗号
        for line_edit in [self.lineEdit_8, self.lineEdit_9, self.lineEdit_10]:
            line_edit.setText(line_edit.text().replace('，', ','))

        self.save_db_config()

    def save_db_config(self):
        config = {
            "db_config": {
                "host": self.lineEdit_3.text(),
                "port": self.lineEdit_4.text(),  # 不再强制转换为整数
                "user": self.lineEdit_5.text(),
                "password": self.lineEdit_6.text(),
                "database": self.lineEdit_7.text()
            },
            "filter_conditions": {
                "robot_names": self.lineEdit_8.text().split(','),
                "sender_names": self.lineEdit_9.text().split(','),
                "conversation_titles": self.lineEdit_10.text().split(',')
            }
        }

        try:
            # 生成 JSON 字符串
            json_data = json.dumps(config, ensure_ascii=False, indent=4)
            logging.debug(f"Generated JSON data: {json_data}")

            # 加密数据
            encrypted_data = self.encrypt_data(config, self.encryption_key)

            # 保存到文件
            with open(self.db_config_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
                logging.info("Database configuration saved.")
        except Exception as e:
            logging.error(f"Failed to save database configuration: {e}")
    # def closeEvent(self, event):
    #     QMessageBox.information(self, "重启", "设置已更改，重启应用程序以应用更改。")
    #     python = sys.executable
    #     os.execl(python, python, *sys.argv)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    with open('data/qss.qss', 'r', encoding="utf-8") as f:
        app.setStyleSheet(f.read())
    window = SettingsWindow()
    window.show()
    sys.exit(app.exec())