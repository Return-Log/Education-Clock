
import logging
import re
import sys
import json
import base64
import os
from PyQt6.QtWidgets import (
    QDialog, QPushButton, QLabel, QFileDialog, QTextBrowser, QTabWidget,
    QTableWidgetItem, QMessageBox, QApplication, QDialogButtonBox, QPlainTextEdit
)
from PyQt6.uic import loadUi
from PyQt6.QtCore import QTimer, QDateTime, QDate

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.timetable_file = './data/timetable.json'
        self.db_config_file = './data/db_config.json'
        self.countdown_file = './data/time.json'
        self.launch_file = './data/launch.json'
        self.closetime_file = './data/closetime.json'
        self.weather_file = './data/weather.txt'
        self.location_file = './data/location.txt'
        self.names_file = './data/name.txt'
        self.encryption_key = 0x5A  # 选择一个简单的密钥
        self.timetable_data = {}  # 初始化一个空字典以保存时间表数据
        self.load_timetable()  # 加载时刻表数据
        self.load_db_config()  # 加载数据库配置
        self.load_countdown()  # 加载倒计时数据
        self.load_countdown()  # 加载倒计时数据
        self.load_shutdown_settings()  # 加载自动关机设置
        self.load_news_settings()  # 加载新闻设置
        self.load_weather_settings()  # 加载天气设置
        self.load_location_settings()  # 加载位置设置
        self.load_names()  # 加载名字列表

    def setup_ui(self):
        loadUi('./ui/setting.ui', self)
        self.textBrowser.setStyleSheet(
            "background-color: black; color: green; font-family: 'Courier New', Courier, monospace;")
        self.tabWidget.currentChanged.connect(self.on_tab_changed)
        # 连接 tabWidget_2 的 currentChanged 信号
        self.tabWidget_2.currentChanged.connect(self.on_tab_changed_2)
        self.pushButton.clicked.connect(self.insert_row)
        self.pushButton_2.clicked.connect(self.delete_row)
        self.connect_line_edit_signals()  # 连接通知栏设置文本框的信号
        self.connect_count_line_edit_signals()  # 连接倒计时设置文本框的信号
        self.connect_shutdown_signals()  # 连接自动关机设置文本框的信号
        self.connect_news_signals()  # 连接新闻设置信号
        self.connect_weather_signals()  # 连接天气设置信号
        self.connect_location_signals()  # 连接位置设置信号
        self.plainTextEdit_names = self.findChild(QPlainTextEdit, "plainTextEdit")  # 获取名字编辑器
        self.plainTextEdit_names.textChanged.connect(self.save_names)  # 连接 textChanged 信号

    def on_tab_changed(self, index):
        if index == 3:
            self.load_db_config()
        elif index == 7:
            self.init_streaming_text()
        elif index == 1:
            self.load_countdown()
        elif index == 4:
            self.load_shutdown_settings()
        elif index == 5:
            self.load_news_settings()
        elif index == 2:
            self.load_weather_settings()
            self.load_location_settings()
        elif index == 6:
            self.load_names()

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
            "版本: 3.4",
            "",
            "更新日志: ",
            " - 设置项全部更新完毕",
            " - 启动时自动检查更新",
            " - 调节公告板更新频率减轻服务端压力",
            "",
            "日期: 2024/11/24",
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

#############################倒计时设置########################################################################
    def load_countdown(self):
        try:
            logging.debug("Loading countdown from file.")
            if not os.path.exists(self.countdown_file):
                logging.warning("Countdown file not found. Creating a default one.")
                self.create_default_countdown_file()

            with open(self.countdown_file, 'r', encoding='utf-8') as f:
                countdown_data = f.read()
                countdown_json = json.loads(countdown_data)
                event = countdown_json.get('event', '')
                enddate = countdown_json.get('enddate', '')

                self.lineEdit.setText(event)
                self.dateEdit.setDate(QDate.fromString(enddate, "yyyy-MM-dd"))
                logging.debug("Countdown loaded successfully.")
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON: {e}")
            self.create_default_countdown_file()
        except Exception as e:
            logging.error(f"Failed to load countdown: {e}")

    def create_default_countdown_file(self):
        default_countdown = {
            "event": "New Event",
            "enddate": QDate.currentDate().addDays(7).toString("yyyy-MM-dd")
        }
        try:
            json_data = json.dumps(default_countdown, ensure_ascii=False, indent=4)
            with open(self.countdown_file, 'w', encoding='utf-8') as f:
                f.write(json_data)
                logging.info("Default countdown file created.")
        except Exception as e:
            logging.error(f"Failed to create default countdown file: {e}")

    def connect_count_line_edit_signals(self):
        self.lineEdit.textChanged.connect(self.on_count_line_edit_text_changed)
        self.dateEdit.dateChanged.connect(self.on_count_line_edit_text_changed)

    def on_count_line_edit_text_changed(self):
        self.save_countdown()

    def save_countdown(self):
        try:
            event = self.lineEdit.text()
            enddate = self.dateEdit.date().toString("yyyy-MM-dd")

            countdown = {
                "event": event,
                "enddate": enddate
            }

            json_data = json.dumps(countdown, ensure_ascii=False, indent=4)
            logging.debug(f"Generated JSON data: {json_data}")

            with open(self.countdown_file, 'w', encoding='utf-8') as f:
                f.write(json_data)
                logging.info("Countdown saved successfully.")
        except Exception as e:
            logging.error(f"Failed to save countdown: {e}")

######################自动关机设置###########################################################################
    def connect_shutdown_signals(self):
        self.buttonBox.clicked.connect(self.toggle_shutdown)
        self.lineEdit_11.textChanged.connect(self.save_shutdown_settings)
        self.lineEdit_12.textChanged.connect(self.save_shutdown_settings)
        self.lineEdit_13.textChanged.connect(self.save_shutdown_settings)
        self.lineEdit_14.textChanged.connect(self.save_shutdown_settings)
        self.lineEdit_15.textChanged.connect(self.save_shutdown_settings)
        self.lineEdit_16.textChanged.connect(self.save_shutdown_settings)
        self.lineEdit_17.textChanged.connect(self.save_shutdown_settings)

    def load_shutdown_settings(self):
        try:
            logging.debug("Loading shutdown settings from files.")
            if not os.path.exists(self.launch_file):
                logging.warning("Launch file not found. Creating a default one.")
                self.create_default_launch_file()

            if not os.path.exists(self.closetime_file):
                logging.warning("Closetime file not found. Creating a default one.")
                self.create_default_closetime_file()

            with open(self.launch_file, 'r', encoding='utf-8') as f:
                launch_data = json.load(f)
                shutdown_status = launch_data.get('shutdown', '关闭')
                self.label_4.setText(f"{shutdown_status}")

            with open(self.closetime_file, 'r', encoding='utf-8') as f:
                closetime_data = json.load(f)
                shutdown_times = closetime_data.get('shutdown_times', {})
                self.lineEdit_11.setText(",".join(shutdown_times.get('Monday', [])))
                self.lineEdit_12.setText(",".join(shutdown_times.get('Tuesday', [])))
                self.lineEdit_13.setText(",".join(shutdown_times.get('Wednesday', [])))
                self.lineEdit_14.setText(",".join(shutdown_times.get('Thursday', [])))
                self.lineEdit_15.setText(",".join(shutdown_times.get('Friday', [])))
                self.lineEdit_16.setText(",".join(shutdown_times.get('Saturday', [])))
                self.lineEdit_17.setText(",".join(shutdown_times.get('Sunday', [])))


            logging.debug("Shutdown settings loaded successfully.")
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON: {e}")
        except Exception as e:
            logging.error(f"Failed to load shutdown settings: {e}")

    def create_default_launch_file(self):
        default_launch = {
            "shutdown": "关闭",
            "news": "开启"
        }
        try:
            json_data = json.dumps(default_launch, ensure_ascii=False, indent=4)
            with open(self.launch_file, 'w', encoding='utf-8') as f:
                f.write(json_data)
                logging.info("Default launch file created.")
        except Exception as e:
            logging.error(f"Failed to create default launch file: {e}")

    def create_default_closetime_file(self):
        default_closetime = {
            "shutdown_times": {
                "Monday": ["12:01", "22:29"],
                "Tuesday": ["12:01", "22:29"],
                "Wednesday": ["12:01", "22:29"],
                "Thursday": ["12:01", "22:29"],
                "Friday": ["12:01", "22:29"],
                "Saturday": ["12:01", "15:45"],
                "Sunday": ["12:01", "21:59"]
            }
        }
        try:
            json_data = json.dumps(default_closetime, ensure_ascii=False, indent=4)
            with open(self.closetime_file, 'w', encoding='utf-8') as f:
                f.write(json_data)
                logging.info("Default closetime file created.")
        except Exception as e:
            logging.error(f"Failed to create default closetime file: {e}")

    def toggle_shutdown(self, button):
        try:
            with open(self.launch_file, 'r', encoding='utf-8') as f:
                launch_data = json.load(f)

            current_status = launch_data.get('shutdown', '关闭')
            if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Open):
                new_status = "开启"
            elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
                new_status = "关闭"
            else:
                return

            if current_status != new_status:
                launch_data['shutdown'] = new_status
                with open(self.launch_file, 'w', encoding='utf-8') as f:
                    json.dump(launch_data, f, ensure_ascii=False, indent=4)

                self.label_4.setText(f"{new_status}")
                logging.info(f"Shutdown status toggled to: {new_status}")
        except Exception as e:
            logging.error(f"Failed to toggle shutdown status: {e}")

    def save_shutdown_settings(self):
        try:
            with open(self.launch_file, 'r', encoding='utf-8') as f:
                launch_data = json.load(f)

            with open(self.closetime_file, 'r', encoding='utf-8') as f:
                closetime_data = json.load(f)

            # 自动合法化时间输入
            def legalize_time(time_str):
                # 将中文逗号替换为英文逗号
                time_str = time_str.replace('，', ',')
                # 分割时间字符串
                times = time_str.split(',')
                legalized_times = []

                for time in times:
                    # 去除前后空格
                    time = time.strip()
                    # 检查是否为空
                    if not time:
                        continue

                    # 检查是否已经有冒号
                    if ':' in time:
                        parts = time.split(':')
                        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                            hour = int(parts[0])
                            minute = int(parts[1])
                            if 0 <= hour < 24 and 0 <= minute < 60:
                                legalized_times.append(f"{hour:02}:{minute:02}")
                            else:
                                logging.warning(f"Illegal time format: {time}. Ignoring.")
                        else:
                            logging.warning(f"Illegal time format: {time}. Ignoring.")
                    else:
                        # 如果没有冒号，尝试将其解释为 HHMM 格式
                        if len(time) == 4 and time.isdigit():
                            hour = int(time[:2])
                            minute = int(time[2:])
                            if 0 <= hour < 24 and 0 <= minute < 60:
                                legalized_times.append(f"{hour:02}:{minute:02}")
                            else:
                                logging.warning(f"Illegal time format: {time}. Ignoring.")
                        else:
                            logging.warning(f"Illegal time format: {time}. Ignoring.")

                return legalized_times

            shutdown_times = {
                "Monday": legalize_time(self.lineEdit_11.text()),
                "Tuesday": legalize_time(self.lineEdit_12.text()),
                "Wednesday": legalize_time(self.lineEdit_13.text()),
                "Thursday": legalize_time(self.lineEdit_14.text()),
                "Friday": legalize_time(self.lineEdit_15.text()),
                "Saturday": legalize_time(self.lineEdit_16.text()),
                "Sunday": legalize_time(self.lineEdit_17.text())
            }

            closetime_data['shutdown_times'] = shutdown_times

            with open(self.closetime_file, 'w', encoding='utf-8') as f:
                json.dump(closetime_data, f, ensure_ascii=False, indent=4)

            logging.info("Shutdown times saved successfully.")
        except Exception as e:
            logging.error(f"Failed to save shutdown settings: {e}")

###############自动新闻联播设置#########################################################################################
    def connect_news_signals(self):
        self.buttonBox_3.clicked.connect(self.toggle_news)

    def load_news_settings(self):
        try:
            logging.debug("Loading news settings from files.")
            if not os.path.exists(self.launch_file):
                logging.warning("Launch file not found. Creating a default one.")
                self.create_default_launch_file()

            with open(self.launch_file, 'r', encoding='utf-8') as f:
                launch_data = json.load(f)
                news_status = launch_data.get('news', '开启')
                self.label_2.setText(f"{news_status}")

            logging.debug("News settings loaded successfully.")
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON: {e}")
        except Exception as e:
            logging.error(f"Failed to load news settings: {e}")

    def toggle_news(self, button):
        try:
            with open(self.launch_file, 'r', encoding='utf-8') as f:
                launch_data = json.load(f)

            current_status = launch_data.get('news', '关闭')
            if button == self.buttonBox_3.button(QDialogButtonBox.StandardButton.Open):
                new_status = "开启"
            elif button == self.buttonBox_3.button(QDialogButtonBox.StandardButton.Close):
                new_status = "关闭"
            else:
                return

            if current_status != new_status:
                launch_data['news'] = new_status
                with open(self.launch_file, 'w', encoding='utf-8') as f:
                    json.dump(launch_data, f, ensure_ascii=False, indent=4)

                self.label_2.setText(f"{new_status}")
                logging.info(f"News status toggled to: {new_status}")
        except Exception as e:
            logging.error(f"Failed to toggle news status: {e}")

#####################天气模块设置########################################################################################
    def connect_weather_signals(self):
        self.lineEdit_2.textChanged.connect(self.save_weather_settings)

    def load_weather_settings(self):
        try:
            logging.debug("Loading weather settings from file.")
            if not os.path.exists(self.weather_file):
                logging.warning("Weather file not found. Creating a default one.")
                self.create_default_weather_file()

            with open(self.weather_file, 'r', encoding='utf-8') as f:
                api_key = f.read().strip()
                self.lineEdit_2.setText(api_key)

            logging.debug("Weather settings loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load weather settings: {e}")

    def create_default_weather_file(self):
        default_api_key = "your_api_key_here"
        try:
            with open(self.weather_file, 'w', encoding='utf-8') as f:
                f.write(default_api_key)
                logging.info("Default weather file created.")
        except Exception as e:
            logging.error(f"Failed to create default weather file: {e}")

    def save_weather_settings(self):
        try:
            api_key = self.lineEdit_2.text().strip()
            with open(self.weather_file, 'w', encoding='utf-8') as f:
                f.write(api_key)
            logging.info("Weather settings saved successfully.")
        except Exception as e:
            logging.error(f"Failed to save weather settings: {e}")

    def connect_location_signals(self):
        self.doubleSpinBox.valueChanged.connect(self.save_location_settings)
        self.doubleSpinBox_2.valueChanged.connect(self.save_location_settings)

    def load_location_settings(self):
        try:
            logging.debug("Loading location settings from file.")
            if not os.path.exists(self.location_file):
                logging.warning("Location file not found. Creating a default one.")
                self.create_default_location_file()

            with open(self.location_file, 'r', encoding='utf-8') as f:
                location_data = f.read().strip()
                latitude, longitude = map(float, location_data.split(','))
                self.doubleSpinBox.setValue(latitude)
                self.doubleSpinBox_2.setValue(longitude)

            logging.debug("Location settings loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load location settings: {e}")

    def create_default_location_file(self):
        default_location = "40.605403,111.843386"
        try:
            with open(self.location_file, 'w', encoding='utf-8') as f:
                f.write(default_location)
                logging.info("Default location file created.")
        except Exception as e:
            logging.error(f"Failed to create default location file: {e}")

    def save_location_settings(self):
        try:
            latitude = self.doubleSpinBox.value()
            longitude = self.doubleSpinBox_2.value()

            if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                QMessageBox.critical(self, "错误", "经纬度超出有效范围。")
                return

            location_data = f"{latitude},{longitude}"
            with open(self.location_file, 'w', encoding='utf-8') as f:
                f.write(location_data)
            logging.info("Location settings saved successfully.")
        except Exception as e:
            logging.error(f"Failed to save location settings: {e}")

#########################################随机点名设置################################################
    def load_names(self):
        """从文件中加载名字列表"""
        try:
            with open(self.names_file, 'r', encoding='utf-8') as file:
                names = file.read()
            self.plainTextEdit_names.setPlainText(names)
        except FileNotFoundError:
            self.plainTextEdit_names.setPlainText("")  # 如果文件不存在，清空编辑器

    def save_names(self):
        """保存名字列表到文件，并去除空的换行符"""
        # 获取纯文本编辑器中的所有文本
        names = self.plainTextEdit_names.toPlainText()

        # 将文本按行分割
        lines = names.splitlines()

        # 过滤掉空行
        non_empty_lines = [line for line in lines if line.strip()]

        # 重新组合成一个字符串，每行之间保留一个换行符
        cleaned_names = '\n'.join(non_empty_lines)

        # 写入文件
        with open(self.names_file, 'w', encoding='utf-8') as file:
            file.write(cleaned_names)

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