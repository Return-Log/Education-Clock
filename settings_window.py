
import logging
import re
import sys
import json
import base64
import os
import numpy as np
import pyaudio
import cv2      # 需要导入以扫描相机设备
import comtypes.stream
from pygrabber.dshow_graph import FilterGraph
from PyQt6.QtWidgets import (
    QDialog, QPushButton, QLabel, QFileDialog, QTextBrowser, QTabWidget,
    QTableWidgetItem, QMessageBox, QApplication, QDialogButtonBox, QPlainTextEdit, QComboBox
)
from PyQt6.uic import loadUi
from PyQt6.QtCore import QTimer, QDateTime, QDate, QThread, pyqtSignal


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
        self.maintain_order_info = './data/maintain_order_info.json'
        self.score_db = './data/score_db_config.json'
        self.encryption_key = 0x5A  # 选择一个简单的密钥
        self.is_calibrating = False  # 初始化校准状态
        self.timetable_data = {}  # 初始化一个空字典以保存时间表数据
        self.load_timetable()  # 加载时刻表数据
        self.load_db_config()  # 加载数据库配置
        self.load_countdown()  # 加载倒计时数据
        self.load_countdown()  # 加载倒计时数据
        self.load_shutdown_settings()  # 加载自动关机设置
        self.load_news_settings()  # 加载新闻设置
        self.load_weather_settings()  # 加载天气设置
        self.load_location_settings()  # 加载位置设置
        self.load_score_settings()  # 加载积分设置
        self.load_names()  # 加载名字列表
        self.load_maintain_order_info() # 加载维护秩序信息
        self.load_order_settings()

    def setup_ui(self):
        loadUi('./ui/setting.ui', self)
        self.tabWidget.currentChanged.connect(self.on_tab_changed)
        self.init_theme_settings()
        self.tabWidget_2.currentChanged.connect(self.on_tab_changed_2)
        self.pushButton.clicked.connect(self.insert_row)
        self.pushButton_2.clicked.connect(self.delete_row)
        self.connect_line_edit_signals()  # 连接通知栏设置文本框的信号
        self.connect_count_line_edit_signals()  # 连接倒计时设置文本框的信号
        self.connect_shutdown_signals()  # 连接自动关机设置文本框的信号
        self.connect_maintain_order_signals() # 链接维护秩序信息信号
        self.connect_order_signals() # 链接维护秩序信息开启关闭信号
        self.pushButton_3.clicked.connect(self.calibrate_microphone)  # 连接校准按钮
        self.connect_news_signals()  # 连接新闻设置信号
        self.connect_weather_signals()  # 连接天气设置信号
        self.connect_score_signals()
        self.connect_location_signals()  # 连接位置设置信号
        self.plainTextEdit_names = self.findChild(QPlainTextEdit, "plainTextEdit")  # 获取名字编辑器
        self.plainTextEdit_names.textChanged.connect(self.save_names)  # 连接 textChanged 信号

    def on_tab_changed(self, index):
        if index == 3:
            self.load_db_config()
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
        elif index == 7:
            self.init_theme_settings()
        elif index == 8:
            self.load_maintain_order_info()
            self.load_order_settings()
        elif index == 9:
            self.load_score_settings()

    def on_tab_changed_2(self, index):
        if 0 <= index <= 6:

            self.load_timetable_day(index)
        else:
            logging.warning(f"Unexpected tab index: {index}")

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
    """此部分加密解密下方排行榜复用"""
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
        try:
            decoded_data = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = self.xor_encrypt_decrypt(decoded_data, key)
            return json.loads(decrypted_data.decode('utf-8'))
        except Exception as e:
            logging.error(f"解密失败: {str(e)}")
            return None

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
            "news": "开启",
            "order": "关闭"
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

#################################主题设置#########################################################
    def init_theme_settings(self):
        """初始化主题设置页面"""
        self.comboBox_themes = self.findChild(QComboBox, "comboBox")
        if self.comboBox_themes is None:
            raise ValueError("找不到 comboBox，请检查 UI 文件")

        # 动态加载 QSS 文件
        qss_dir = './ui/qss'
        if os.path.exists(qss_dir):
            qss_files = [f for f in os.listdir(qss_dir) if f.endswith('.qss')]
            self.comboBox_themes.clear()
            self.comboBox_themes.addItems(qss_files)

        # 设置默认选择
        self.load_current_theme()

        # 连接 comboBox 的 currentIndexChanged 信号
        self.comboBox_themes.currentIndexChanged.connect(self.save_selected_theme)

    def load_current_theme(self):
        """根据 qss.txt 文件设置当前主题"""
        qss_txt_path = './data/qss.txt'
        default_qss = 'Vista Blue.qss'

        try:
            with open(qss_txt_path, 'r', encoding='utf-8') as f:
                current_theme = f.read().strip()
                if current_theme and os.path.exists(os.path.join('./ui/qss', current_theme)):
                    index = self.comboBox_themes.findText(current_theme)
                    if index >= 0:
                        self.comboBox_themes.setCurrentIndex(index)
                else:
                    QMessageBox.warning(f"QSS file {current_theme} does not exist, using default.")
                    self.comboBox_themes.setCurrentText(default_qss)
        except Exception as e:
            QMessageBox.warning(f"Error reading qss.txt: {e}, using default.")
            self.comboBox_themes.setCurrentText(default_qss)

    def save_selected_theme(self, index):
        """保存选中的主题到 qss.txt 文件"""
        selected_theme = self.comboBox_themes.itemText(index)
        qss_txt_path = './data/qss.txt'

        try:
            with open(qss_txt_path, 'w', encoding='utf-8') as f:
                f.write(selected_theme)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法保存主题设置: {e}")

    def closeEvent(self, event):
        QMessageBox.information(self, "重启", "设置已更改，重启应用程序以应用更改。")
        python = sys.executable
        os.execl(python, python, *sys.argv)

#####################################排行榜####################################################
    def load_score_settings(self):
        """加载排行榜数据库配置"""
        try:
            if not os.path.exists(self.score_db):
                logging.error(f"配置文件 {self.score_db} 不存在")
                return

            with open(self.score_db, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            # 尝试解密
            config = self.decrypt_data(content, self.encryption_key)
            if config is not None:
                # 解密成功，加载到 UI
                self.lineEdit_29.setText(config.get("host", ""))
                self.lineEdit_30.setText(str(config.get("port", "")))
                self.lineEdit_31.setText(config.get("user", ""))
                self.lineEdit_32.setText(config.get("password", ""))
                self.lineEdit_33.setText(config.get("database", ""))
                self.lineEdit_34.setText(config.get("table_name", ""))
                logging.debug("已加载加密的数据库配置.")
                return

            # 如果解密失败，尝试直接加载未加密的 JSON
            logging.info("尝试加载未加密的 JSON 文件")
            config = json.loads(content)
            self.lineEdit_29.setText(config.get("host", ""))
            self.lineEdit_30.setText(str(config.get("port", "")))
            self.lineEdit_31.setText(config.get("user", ""))
            self.lineEdit_32.setText(config.get("password", ""))
            self.lineEdit_33.setText(config.get("database", ""))
            self.lineEdit_34.setText(config.get("table_name", ""))
            logging.debug("已加载未加密的数据库配置.")

            # 自动加密并保存
            encrypted_content = self.encrypt_data(config, self.encryption_key)
            with open(self.score_db, 'w', encoding='utf-8') as f:
                f.write(encrypted_content)
            logging.info(f"配置文件未加密，已自动加密并保存到 {self.score_db}")

        except json.JSONDecodeError:
            logging.error("配置文件格式错误或解密失败")
        except Exception as e:
            logging.error(f"无法加载数据库配置: {e}")

    def connect_score_signals(self):
        line_edits = [self.lineEdit_29, self.lineEdit_30, self.lineEdit_31, self.lineEdit_32, self.lineEdit_33,
                      self.lineEdit_34]
        for line_edit in line_edits:
            line_edit.textChanged.connect(self.save_score_db_config)

    def save_score_db_config(self):
        """保存排行榜数据库配置（加密）"""
        config = {
            "host": self.lineEdit_29.text(),
            "port": self.lineEdit_30.text(),  # 保持字符串形式
            "user": self.lineEdit_31.text(),
            "password": self.lineEdit_32.text(),
            "database": self.lineEdit_33.text(),
            "table_name": self.lineEdit_34.text()
        }

        try:
            # 加密数据
            encrypted_data = self.encrypt_data(config, self.encryption_key)
            logging.debug(f"Encrypted data: {encrypted_data}")

            # 保存到文件
            with open(self.score_db, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
            logging.info("Encrypted database configuration saved.")
        except Exception as e:
            logging.error(f"Failed to save encrypted database configuration: {e}")


###################################秩序维护模块设置#################################################
    def connect_maintain_order_signals(self):
        """连接维护秩序设置的控件信号到保存函数"""
        # 文本输入框信号
        self.lineEdit_18.textChanged.connect(self.save_maintain_order_info)  # webhook_url
        self.lineEdit_19.textChanged.connect(self.save_maintain_order_info)  # smms_username
        self.lineEdit_20.textChanged.connect(self.save_maintain_order_info)  # smms_password
        self.lineEdit_21.textChanged.connect(self.save_maintain_order_info)  # text_at
        self.lineEdit_22.textChanged.connect(self.save_maintain_order_info)  # Monday
        self.lineEdit_23.textChanged.connect(self.save_maintain_order_info)  # Tuesday
        self.lineEdit_24.textChanged.connect(self.save_maintain_order_info)  # Wednesday
        self.lineEdit_25.textChanged.connect(self.save_maintain_order_info)  # Thursday
        self.lineEdit_26.textChanged.connect(self.save_maintain_order_info)  # Friday
        self.lineEdit_27.textChanged.connect(self.save_maintain_order_info)  # Saturday
        self.lineEdit_28.textChanged.connect(self.save_maintain_order_info)  # Sunday

        # 下拉框信号（替换原来的 spinBox）
        self.comboBox_2.currentIndexChanged.connect(self.save_maintain_order_info)  # mic_device_index
        self.comboBox_3.currentIndexChanged.connect(self.save_maintain_order_info)  # camera_device_index
        self.spinBox_3.valueChanged.connect(self.save_maintain_order_info)  # threshold_db（保持不变）

    def load_maintain_order_info(self):
        """加载维护秩序信息到控件，并扫描设备填充 ComboBox"""
        try:
            with open(self.maintain_order_info, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logging.debug(f"Loaded maintain_order_info: {data}")

                # 加载基本设置
                self.lineEdit_18.setText(data.get("webhook_url", ""))
                self.lineEdit_19.setText(data.get("smms_username", ""))
                self.lineEdit_20.setText(data.get("smms_password", ""))
                self.lineEdit_21.setText(",".join(data.get("text_at", [])))
                self.spinBox_3.setValue(data.get("threshold_db", -30))

                # 扫描话筒设备并填充 comboBox_2
                p = pyaudio.PyAudio()
                mic_devices = []
                for i in range(p.get_device_count()):
                    device_info = p.get_device_info_by_index(i)
                    # 条件1：必须是输入设备
                    if device_info['maxInputChannels'] <= 0:
                        continue
                    # 条件2：排除常见虚拟设备（可选，根据实际情况调整）
                    device_name = device_info['name'].lower()
                    if "virtual" in device_name or "default" in device_name or "output" in device_name:
                        logging.debug(f"跳过可能不可用的设备: {device_info['name']}")
                        continue
                    # 条件3：尝试打开设备以验证可用性
                    try:
                        stream = p.open(
                            format=pyaudio.paInt16,
                            channels=1,
                            rate=int(device_info['defaultSampleRate']),
                            input=True,
                            input_device_index=i,
                            frames_per_buffer=1024
                        )
                        stream.close()
                        mic_devices.append((device_info['name'], i))
                        logging.debug(f"可用麦克风设备: {device_info['name']} (index: {i})")
                    except Exception as e:
                        logging.debug(f"设备 {device_info['name']} (index: {i}) 不可用: {e}")
                        continue
                p.terminate()

                self.comboBox_2.clear()
                if mic_devices:
                    for name, _ in mic_devices:
                        self.comboBox_2.addItem(name)
                else:
                    self.comboBox_2.addItem("未检测到可用麦克风")
                    logging.warning("未找到任何可用的麦克风设备")

                # 设置当前话筒索引
                mic_index = data.get("mic_device_index", 0)
                if mic_devices and 0 <= mic_index < len(mic_devices):
                    self.comboBox_2.setCurrentIndex(mic_index)
                else:
                    self.comboBox_2.setCurrentIndex(0)  # 默认选择第一个设备或提示
                    logging.warning(f"话筒索引 {mic_index} 超出范围或无可用设备，使用默认值 0")

                # 扫描相机设备并填充 comboBox_3
                if sys.platform == "win32":
                    graph = FilterGraph()
                    camera_names = graph.get_input_devices()
                    camera_devices = [(name, i) for i, name in enumerate(camera_names)]
                else:
                    camera_devices = []
                    index = 0
                    while True:
                        cap = cv2.VideoCapture(index)
                        if not cap.isOpened():
                            break
                        camera_devices.append((f"Camera {index}", index))
                        cap.release()
                        index += 1

                self.comboBox_3.clear()
                for name, _ in camera_devices:
                    self.comboBox_3.addItem(name)

                # 设置当前相机索引
                camera_index = data.get("camera_device_index", 0)
                if 0 <= camera_index < len(camera_devices):
                    self.comboBox_3.setCurrentIndex(camera_index)
                else:
                    self.comboBox_3.setCurrentIndex(0)  # 默认选择第一个设备
                    logging.warning(f"相机索引 {camera_index} 超出范围，使用默认值 0")

                # 加载日程表
                schedule = data.get("schedule", {})
                self.lineEdit_22.setText(",".join(schedule.get("Monday", [])))
                self.lineEdit_23.setText(",".join(schedule.get("Tuesday", [])))
                self.lineEdit_24.setText(",".join(schedule.get("Wednesday", [])))
                self.lineEdit_25.setText(",".join(schedule.get("Thursday", [])))
                self.lineEdit_26.setText(",".join(schedule.get("Friday", [])))
                self.lineEdit_27.setText(",".join(schedule.get("Saturday", [])))
                self.lineEdit_28.setText(",".join(schedule.get("Sunday", [])))

                logging.info("维护秩序信息加载成功")
        except FileNotFoundError:
            logging.warning(f"{self.maintain_order_info} 文件未找到，使用默认值")
            self.create_default_maintain_order_file()
            self.load_maintain_order_info()  # 再次加载默认值
        except json.JSONDecodeError:
            logging.error(f"{self.maintain_order_info} 文件格式错误")
        except Exception as e:
            logging.error(f"加载维护秩序信息失败: {e}")

    def create_default_maintain_order_file(self):
        """创建默认的维护秩序配置文件"""
        default_data = {
            "webhook_url": "",
            "smms_username": "",
            "smms_password": "",
            "threshold_db": -30,
            "mic_device_index": 0,
            "camera_device_index": 0,
            "text_at": [],
            "schedule": {
                "Monday": [],
                "Tuesday": [],
                "Wednesday": [],
                "Thursday": [],
                "Friday": [],
                "Saturday": [],
                "Sunday": []
            }
        }
        try:
            with open(self.maintain_order_info, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=4)
            logging.info("默认维护秩序文件已创建")
        except Exception as e:
            logging.error(f"创建默认维护秩序文件失败: {e}")

    def save_maintain_order_info(self):
        """保存维护秩序信息到文件，包含防呆措施"""
        try:
            # 处理时间格式，确保符合 HH:MM-HH:MM
            def legalize_time(time_str):
                """将时间段字符串合法化为 HH:MM-HH:MM 格式，并处理中文标点"""
                if not time_str:
                    return []
                # 替换中文标点为英文标点
                time_str = time_str.replace('，', ',').replace('：', ':')
                time_ranges = time_str.split(',')
                legalized_ranges = []

                for time_range in time_ranges:
                    time_range = time_range.strip()
                    if not time_range:
                        continue

                    # 检查是否为 HH:MM-HH:MM 格式
                    if '-' in time_range:
                        start, end = time_range.split('-', 1)
                        start = start.strip()
                        end = end.strip()

                        # 处理开始时间
                        if re.match(r'^\d{2}:\d{2}$', start):
                            s_hour, s_minute = map(int, start.split(':'))
                            if not (0 <= s_hour < 24 and 0 <= s_minute < 60):
                                logging.warning(f"开始时间超出范围: {start}")
                                continue
                            start = f"{s_hour:02d}:{s_minute:02d}"
                        elif re.match(r'^\d{4}$', start):
                            s_hour, s_minute = int(start[:2]), int(start[2:])
                            if not (0 <= s_hour < 24 and 0 <= s_minute < 60):
                                logging.warning(f"开始时间超出范围: {start}")
                                continue
                            start = f"{s_hour:02d}:{s_minute:02d}"
                        else:
                            logging.warning(f"开始时间格式错误: {start}")
                            continue

                        # 处理结束时间
                        if re.match(r'^\d{2}:\d{2}$', end):
                            e_hour, e_minute = map(int, end.split(':'))
                            if not (0 <= e_hour < 24 and 0 <= e_minute < 60):
                                logging.warning(f"结束时间超出范围: {end}")
                                continue
                            end = f"{e_hour:02d}:{e_minute:02d}"
                        elif re.match(r'^\d{4}$', end):
                            e_hour, e_minute = int(end[:2]), int(end[2:])
                            if not (0 <= e_hour < 24 and 0 <= e_minute < 60):
                                logging.warning(f"结束时间超出范围: {end}")
                                continue
                            end = f"{e_hour:02d}:{e_minute:02d}"
                        else:
                            logging.warning(f"结束时间格式错误: {end}")
                            continue

                        # 验证开始时间早于结束时间
                        if start >= end:
                            logging.warning(f"时间段无效（开始时间晚于结束时间）: {start}-{end}")
                            continue

                        legalized_ranges.append(f"{start}-{end}")
                    else:
                        logging.warning(f"时间段格式错误（缺少'-'）: {time_range}")

                return legalized_ranges

            # 构造 JSON 数据
            data = {
                "webhook_url": self.lineEdit_18.text().strip(),
                "smms_username": self.lineEdit_19.text().strip(),
                "smms_password": self.lineEdit_20.text().strip(),
                "threshold_db": self.spinBox_3.value(),
                "mic_device_index": self.comboBox_2.currentIndex(),  # 从 comboBox_2 获取索引
                "camera_device_index": self.comboBox_3.currentIndex(),  # 从 comboBox_3 获取索引
                "text_at": [x.strip() for x in self.lineEdit_21.text().replace('，', ',').split(',') if x.strip()],
                "schedule": {
                    "Monday": legalize_time(self.lineEdit_22.text()),
                    "Tuesday": legalize_time(self.lineEdit_23.text()),
                    "Wednesday": legalize_time(self.lineEdit_24.text()),
                    "Thursday": legalize_time(self.lineEdit_25.text()),
                    "Friday": legalize_time(self.lineEdit_26.text()),
                    "Saturday": legalize_time(self.lineEdit_27.text()),
                    "Sunday": legalize_time(self.lineEdit_28.text())
                }
            }

            # 保存到文件
            with open(self.maintain_order_info, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            logging.info("维护秩序信息保存成功")
        except Exception as e:
            logging.error(f"保存维护秩序信息失败: {e}")

    def connect_order_signals(self):
        self.buttonBox_2.clicked.connect(self.toggle_order)

    def load_order_settings(self):
        try:
            logging.debug("Loading order settings from files.")
            if not os.path.exists(self.launch_file):
                logging.warning("Launch file not found. Creating a default one.")
                self.create_default_launch_file()

            with open(self.launch_file, 'r', encoding='utf-8') as f:
                launch_data = json.load(f)
                order_status = launch_data.get('order', '开启')
                self.label_43.setText(f"{order_status}")

            logging.debug("News settings loaded successfully.")
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON: {e}")
        except Exception as e:
            logging.error(f"Failed to load order settings: {e}")

    def toggle_order(self, button):
        try:
            with open(self.launch_file, 'r', encoding='utf-8') as f:
                launch_data = json.load(f)

            current_status = launch_data.get('order', '关闭')
            if button == self.buttonBox_2.button(QDialogButtonBox.StandardButton.Open):
                new_status = "开启"
            elif button == self.buttonBox_2.button(QDialogButtonBox.StandardButton.Close):
                new_status = "关闭"
            else:
                logging.warning(f"Unknown button clicked: {button}")
                return

            if current_status != new_status:
                launch_data['order'] = new_status
                with open(self.launch_file, 'w', encoding='utf-8') as f:
                    json.dump(launch_data, f, ensure_ascii=False, indent=4)

                self.label_43.setText(f"{new_status}")
                logging.info(f"order status toggled to: {new_status}")
        except Exception as e:
            logging.error(f"Failed to toggle order status: {e}")

    def calibrate_microphone(self):
        """校准话筒，检测5秒内平均去极值分贝值"""
        if self.is_calibrating:
            logging.info("正在校准中，忽略重复点击")
            return

        logging.debug("开始校准话筒")
        self.is_calibrating = True
        self.pushButton_3.setEnabled(False)
        self.label_66.setText("校准中...")

        # 从 maintain_order_info.json 获取 mic_device_index
        try:
            with open(self.maintain_order_info, 'r', encoding='utf-8') as f:
                data = json.load(f)
                mic_device_index = data.get("mic_device_index", 0)
            logging.debug(f"使用 mic_device_index: {mic_device_index}")
        except Exception as e:
            logging.error(f"读取 mic_device_index 失败: {e}")
            mic_device_index = 0

        # 启动校准线程
        self.calibration_thread = CalibrationThread(mic_device_index)
        try:
            self.calibration_thread.calibration_complete.connect(self.on_calibration_complete)
            logging.debug("校准线程信号已连接")
        except Exception as e:
            logging.error(f"连接校准线程信号失败: {e}")
            self.is_calibrating = False
            self.pushButton_3.setEnabled(True)
            return

        self.calibration_thread.start()
        logging.info("校准线程已启动")

    def on_calibration_complete(self, db_value):
        """处理校准完成事件"""
        logging.debug(f"收到校准完成信号，db_value: {db_value}")
        if db_value is not None:
            self.label_66.setText(f"校准完成: {db_value:.1f} dB")
            logging.info(f"话筒校准完成，结果: {db_value:.1f} dB")
        else:
            self.label_66.setText("校准失败")
            logging.error("话筒校准失败")

        self.is_calibrating = False
        self.pushButton_3.setEnabled(True)
        logging.debug("校准状态已重置")



class CalibrationThread(QThread):
    calibration_complete = pyqtSignal(float)

    def __init__(self, mic_device_index):
        super().__init__()
        self.mic_device_index = mic_device_index
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100

    def run(self):
        """运行校准线程，检测5秒内平均去极值分贝值"""
        p = None
        stream = None
        try:
            p = pyaudio.PyAudio()
            device_count = p.get_device_count()
            logging.debug(f"可用音频设备数: {device_count}")
            if self.mic_device_index >= device_count or self.mic_device_index < 0:
                logging.error(f"无效的 mic_device_index: {self.mic_device_index}")
                self.calibration_complete.emit(None)
                return

            stream = p.open(format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE, input=True,
                            frames_per_buffer=self.CHUNK, input_device_index=self.mic_device_index)
            logging.info("校准线程：音频流初始化成功，开始检测5秒噪音")

            db_values = []
            for _ in range(int(self.RATE / self.CHUNK * 5)):
                data = np.frombuffer(stream.read(self.CHUNK, exception_on_overflow=False), dtype=np.int16)
                rms = np.sqrt(np.mean(data ** 2)) if np.any(data) else 0
                db = 20 * np.log10(rms) if rms > 0 else -float("inf")
                db_values.append(db)

            logging.info(f"5秒原始分贝值 - 最小: {min(db_values):.1f}, 最大: {max(db_values):.1f}, 平均: {np.mean(db_values):.1f}")
            db_array = np.array(db_values)
            trimmed_db = np.percentile(db_array, [5, 95])
            trimmed_mean_db = np.mean(db_array[(db_array > trimmed_db[0]) & (db_array < trimmed_db[1])])
            logging.info(f"去极值后 - 范围: {trimmed_db[0]:.1f} 到 {trimmed_db[1]:.1f}, 平均: {trimmed_mean_db:.1f}")

            self.calibration_complete.emit(trimmed_mean_db)
        except Exception as e:
            logging.error(f"校准线程异常: {str(e)}")
            self.calibration_complete.emit(None)
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            if p:
                p.terminate()
            logging.info("校准线程：音频流已关闭")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    with open('data/qss.qss', 'r', encoding="utf-8") as f:
        app.setStyleSheet(f.read())
    window = SettingsWindow()
    window.show()
    sys.exit(app.exec())