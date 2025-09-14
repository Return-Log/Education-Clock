
import logging
import re
import sys
import json
import base64
import requests
import os
from PyQt6.QtWidgets import (
    QDialog, QPushButton, QLabel, QFileDialog, QTextBrowser, QTabWidget,
    QTableWidgetItem, QMessageBox, QApplication, QDialogButtonBox, QPlainTextEdit, QComboBox, QGroupBox, QWidget,
    QVBoxLayout, QScrollArea, QHBoxLayout, QGridLayout, QLineEdit, QSizePolicy, QTextEdit, QTimeEdit, QDateEdit
)
from PyQt6.uic import loadUi
from PyQt6.QtCore import QTimer, QDateTime, QDate, QThread, pyqtSignal, QTime, Qt


class GroupBoxWidget(QGroupBox):
    def __init__(self, config=None, parent=None, settings_window=None):
        super().__init__(parent)
        self.setTitle("API Configuration")
        self.config = config or {"name": "", "url": "", "template": "", "refresh_time": ""}
        self.settings_window = settings_window
        self.last_data = None
        logging.debug(f"Initializing GroupBoxWidget with config: {self.config}")
        self.setup_ui()

        # Initialize with config
        self.name_input.setText(self.config.get("name", ""))
        self.url_input.setText(self.config.get("url", ""))
        self.template_input.setPlainText(self.config.get("template", ""))
        self.refresh_time_input.setText(str(self.config.get("refresh_time", "")))
        logging.debug(f"Loaded refresh_time: {self.config.get('refresh_time', '')}")

        # Connect signals
        logging.debug("Connecting GroupBoxWidget signals")
        self.request_button.clicked.connect(self.fetch_and_display)
        self.parse_button.clicked.connect(self.parse_and_display)
        self.name_input.textChanged.connect(self.on_config_changed)
        self.url_input.textChanged.connect(self.on_config_changed)
        self.template_input.textChanged.connect(self.on_config_changed)
        self.refresh_time_input.textChanged.connect(self.on_config_changed)
        logging.debug("GroupBoxWidget initialization complete")



    def setup_ui(self):
        layout = QGridLayout(self)

        # Row 0: Name
        name_label = QLabel("标签名：")
        self.name_input = QLineEdit()
        layout.addWidget(name_label, 0, 0)
        layout.addWidget(self.name_input, 0, 1, 1, 2)

        # Row 1: URL
        url_label = QLabel("Get URL：")
        self.url_input = QLineEdit()
        layout.addWidget(url_label, 1, 0)
        layout.addWidget(self.url_input, 1, 1, 1, 2)

        # Row 2: Refresh Time
        refresh_time_label = QLabel("刷新时间（秒）：")
        self.refresh_time_input = QLineEdit()
        self.refresh_time_input.setPlaceholderText("请输入正整数（秒）")
        layout.addWidget(refresh_time_label, 2, 0)
        layout.addWidget(self.refresh_time_input, 2, 1, 1, 2)

        # Row 3: Request and Parse Buttons
        self.request_button = QPushButton("请求")
        self.parse_button = QPushButton("解析")
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.request_button)
        button_layout.addWidget(self.parse_button)
        layout.addLayout(button_layout, 3, 0, 1, 1)

        # Row 4: Raw Output and Template
        self.raw_output = QTextBrowser()
        self.raw_output.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.template_input = QTextEdit()
        self.template_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.template_input.setPlaceholderText(
            "Enter Markdown template, e.g:\n# {title}\n![Poster]({poster})\n[Read More]({url})"
        )
        layout.addWidget(self.raw_output, 4, 0, 1, 2)
        layout.addWidget(self.template_input, 4, 2)

        # Row 5: Formatted Output
        self.formatted_output = QTextBrowser()
        self.formatted_output.setOpenExternalLinks(True)
        layout.addWidget(self.formatted_output, 5, 0, 1, 3)

        layout.setColumnStretch(1, 1)
        layout.setColumnMinimumWidth(1, 200)

    def fetch_and_display(self):
        url = self.url_input.text().strip()
        template = self.template_input.toPlainText()
        logging.debug(f"Fetching data from URL: {url}")

        if not url:
            logging.warning("Empty URL provided")
            QMessageBox.warning(self, "Error", "Please enter a valid URL")
            return

        try:
            logging.debug("Sending GET request")
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            self.last_data = response.json()
            logging.debug("Received API response")

            # Display raw JSON
            self.raw_output.setPlainText(json.dumps(self.last_data, indent=2, ensure_ascii=False))
            logging.debug("Displayed raw JSON")

            # Process and display formatted output
            if isinstance(self.last_data.get("data"), list):
                logging.debug("Processing data list for Markdown")
                markdown_output = ""
                for item in self.last_data["data"]:
                    item_output = template
                    for key, value in item.items():
                        placeholder = "{" + key + "}"
                        value = str(value).replace("\n", " ")
                        item_output = item_output.replace(placeholder, value)
                    markdown_output += item_output + "\n"
                self.formatted_output.setMarkdown(markdown_output)
                logging.debug("Displayed formatted Markdown")
            else:
                logging.warning("No valid 'data' list in response")
                self.formatted_output.setPlainText("No valid 'data' list found in response")

        except requests.RequestException as e:
            logging.error(f"Failed to fetch data: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to fetch data: {str(e)}")
            self.raw_output.clear()
            self.formatted_output.clear()
            self.last_data = None

    def parse_and_display(self):
        logging.debug("Parse button clicked")
        template = self.template_input.toPlainText()

        if not self.last_data:
            logging.warning("No data available for parsing")
            QMessageBox.warning(self, "警告", "请先请求数据以进行解析")
            return

        try:
            logging.debug("Processing last data with current template")
            if isinstance(self.last_data.get("data"), list):
                markdown_output = ""
                for item in self.last_data["data"]:
                    item_output = template
                    for key, value in item.items():
                        placeholder = "{" + key + "}"
                        value = str(value).replace("\n", " ")
                        item_output = item_output.replace(placeholder, value)
                    markdown_output += item_output + "\n"
                self.formatted_output.setMarkdown(markdown_output)
                logging.debug("Displayed parsed Markdown")
            else:
                logging.warning("No valid 'data' list in last data")
                self.formatted_output.setPlainText("No valid 'data' list found in last response")
        except Exception as e:
            logging.error(f"Failed to parse data: {str(e)}")
            QMessageBox.critical(self, "错误", f"解析数据失败: {str(e)}")

    def get_config(self):
        refresh_time = self.refresh_time_input.text().strip()
        # Validate refresh_time as a positive integer or empty
        if refresh_time and not refresh_time.isdigit():
            logging.warning(f"Invalid refresh_time: {refresh_time}, must be a positive integer")
            QMessageBox.warning(self, "警告", "刷新时间必须为正整数")
            self.refresh_time_input.clear()
            refresh_time = ""
        elif refresh_time and int(refresh_time) <= 0:
            logging.warning(f"Invalid refresh_time: {refresh_time}, must be positive")
            QMessageBox.warning(self, "警告", "刷新时间必须为正整数")
            self.refresh_time_input.clear()
            refresh_time = ""

        return {
            "name": self.name_input.text().strip(),
            "url": self.url_input.text().strip(),
            "template": self.template_input.toPlainText(),
            "refresh_time": refresh_time
        }

    def on_config_changed(self):
        config = self.get_config()
        logging.debug(f"Text changed in GroupBox: {config}")
        if self.settings_window:
            logging.debug("Calling save_api_configs from GroupBoxWidget")
            self.settings_window.save_api_configs()
        else:
            logging.warning("SettingsWindow reference not available")


class SettingsWindow(QDialog):
    refresh_signal = pyqtSignal(str)  # 发送给主窗口的刷新信号
    def __init__(self, parent=None):
        super().__init__(parent)
        self.modules_to_refresh = set()  # 使用 set 避免重复添加模块
        self.setup_ui()
        self.timetable_file = './data/timetable.json'
        self.db_config_file = './data/db_config.json'
        self.countdown_file = './data/time.json'
        self.launch_file = './data/launch.json'
        self.closetime_file = './data/closetime.json'
        self.weather_file = './data/weather.txt'
        self.location_file = './data/location.txt'
        self.names_file = './data/name.txt'
        self.api_config_file = './data/api_config.json'
        self.encryption_key = 0x5A  # 选择一个简单的密钥
        self.is_calibrating = False  # 初始化校准状态
        self.timetable_data = {}  # 初始化一个空字典以保存时间表数据
        self.settings_changed = False
        self.groupboxes = []
        self.load_timetable()  # 加载时刻表数据
        self.load_db_config()  # 加载数据库配置
        self.load_countdown()  # 加载倒计时数据
        self.load_shutdown_settings()  # 加载自动关机设置
        self.load_news_settings()  # 加载新闻设置
        self.load_weather_settings()  # 加载天气设置
        self.load_location_settings()  # 加载位置设置
        self.load_names()  # 加载名字列表
        self.setup_api_tab()

    def closeEvent(self, event):
        """无论点击 OK、Cancel 还是关闭按钮，都会进入这里"""
        logging.debug(f"刷新模块: {self.modules_to_refresh}")
        for module in self.modules_to_refresh:
            self.refresh_signal.emit(module)
        self.modules_to_refresh.clear()
        super().accept()

    def setup_ui(self):
        loadUi('./ui/setting.ui', self)
        self.tabWidget.currentChanged.connect(self.on_tab_changed)
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
        self.setup_api_tab()

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
            self.load_api_configs()
        elif index == 9:  # 计划任务设置标签页
            self.setup_plan_tasks_tab()


    def on_tab_changed_2(self, index):
        if 0 <= index <= 6:

            self.load_timetable_day(index)
        else:
            logging.warning(f"Unexpected tab index: {index}")

    def setup_api_tab(self):
        try:
            self.add_api_button = self.findChild(QPushButton, "pushButton_3")
            self.remove_api_button = self.findChild(QPushButton, "pushButton_4")
            self.scroll_area = self.findChild(QScrollArea, "scrollArea")

            if not all([self.add_api_button, self.remove_api_button, self.scroll_area]):
                logging.error("Missing UI elements in tab 8")
                QMessageBox.critical(self, "Error", "Missing UI elements in API Settings tab")
                return

            # Prevent duplicate connections
            try:
                self.add_api_button.clicked.disconnect()
            except TypeError:
                pass
            try:
                self.remove_api_button.clicked.disconnect()
            except TypeError:
                pass

            self.add_api_button.clicked.connect(self.add_groupbox)
            self.remove_api_button.clicked.connect(self.remove_groupbox)

            # Setup scroll area
            self.scroll_content = QWidget()
            self.scroll_layout = QVBoxLayout(self.scroll_content)
            self.scroll_layout.addStretch()
            self.scroll_area.setWidgetResizable(True)
            self.scroll_area.setWidget(self.scroll_content)


        except Exception as e:
            logging.error(f"Failed to setup API tab: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to setup API tab: {str(e)}")

    def add_groupbox(self, config=None):
        logging.debug(f"Adding GroupBox with config: {config}")
        groupbox = GroupBoxWidget(config, self.scroll_content, self)  # Pass self as settings_window
        delete_button = QPushButton("删除")
        delete_button.clicked.connect(lambda: self.delete_specific_groupbox(groupbox, delete_button))
        checkbox_layout = QHBoxLayout()
        checkbox_layout.addWidget(delete_button)
        checkbox_layout.addWidget(groupbox)

        logging.debug("Inserting GroupBox layout into scroll area")
        self.scroll_layout.insertLayout(self.scroll_layout.count() - 1, checkbox_layout)
        self.groupboxes.append((groupbox, delete_button))
        self.settings_changed = True
        logging.debug(f"GroupBox added, total: {len(self.groupboxes)}")
        self.save_api_configs()

    def delete_specific_groupbox(self, groupbox, delete_button):
        self.scroll_layout.removeWidget(groupbox)
        self.scroll_layout.removeWidget(delete_button)
        groupbox.deleteLater()
        delete_button.deleteLater()
        self.groupboxes.remove((groupbox, delete_button))
        self.settings_changed = True
        self.save_api_configs()

    def remove_groupbox(self):
        removed = False
        for groupbox, delete_button in self.groupboxes[:]:
            if delete_button.isDown():  # Optional: keep for pushButton_4 compatibility
                self.scroll_layout.removeWidget(groupbox)
                self.scroll_layout.removeWidget(delete_button)
                groupbox.deleteLater()
                delete_button.deleteLater()
                self.groupboxes.remove((groupbox, delete_button))
                removed = True

        if removed:
            self.settings_changed = True
            self.save_api_configs()
        else:
            QMessageBox.warning(self, "警告", "请先选择一个API配置进行删除")

    def load_api_configs(self):
        logging.debug("Loading API configurations")
        try:
            with open(self.api_config_file, "r", encoding="utf-8") as f:
                configs = json.load(f)
                logging.debug(f"Loaded {len(configs)} API configurations")
                # Clear existing GroupBoxes
                for groupbox, delete_button in self.groupboxes[:]:
                    logging.debug(f"Removing GroupBox: {groupbox.get_config()['name']}")
                    self.scroll_layout.removeWidget(groupbox)
                    self.scroll_layout.removeWidget(delete_button)
                    groupbox.deleteLater()
                    delete_button.deleteLater()
                self.groupboxes.clear()
                logging.debug("GroupBoxes cleared")
                # Add GroupBoxes for each config
                for config in configs:
                    logging.debug(f"Adding GroupBox for config: {config}")
                    self.add_groupbox(config)
                logging.debug("API configurations loaded successfully")
        except (FileNotFoundError, json.JSONDecodeError):
            logging.debug("No API configs found or invalid JSON, skipping")

    def save_api_configs(self):
        logging.debug("Saving API configurations")
        configs = [groupbox.get_config() for groupbox, _ in self.groupboxes]
        try:
            with open(self.api_config_file, "w", encoding="utf-8") as f:
                json.dump(configs, f, indent=2, ensure_ascii=False)
            logging.debug(f"Saved {len(configs)} API configurations")
            self.settings_changed = True
            self.modules_to_refresh.add("api_display")
        except OSError as e:
            logging.error(f"Failed to save API configs: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save API configs: {str(e)}")


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
        self.modules_to_refresh.add("timetable")

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

    def load_db_config(self):
        try:
            with open(self.db_config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # 安全地获取配置值
            filter_conditions = config_data.get('filter_conditions', {})
            agent_id = config_data.get('agent_id', '')
            server_url = config_data.get('server_url', '')

            # 设置控件文本
            self.lineEdit_4.setText(agent_id)
            self.lineEdit_3.setText(server_url)

            # 处理过滤条件
            sender_names = filter_conditions.get('sender_names', [])
            conversation_titles = filter_conditions.get('conversation_titles', [])

            self.lineEdit_9.setText(','.join(sender_names) if sender_names else '')
            self.lineEdit_10.setText(','.join(conversation_titles) if conversation_titles else '')

            logging.debug("Database configuration loaded.")
        except FileNotFoundError:
            logging.warning(f"Database config file not found: {self.db_config_file}")
            # 可以选择创建默认配置
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in database config file: {e}")
        except Exception as e:
            logging.error(f"Failed to load database configuration: {e}")

    def connect_line_edit_signals(self):
        line_edits = [self.lineEdit_3, self.lineEdit_4, self.lineEdit_9, self.lineEdit_10]
        for line_edit in line_edits:
            line_edit.textChanged.connect(self.on_line_edit_text_changed)

    def on_line_edit_text_changed(self):
        # 替换中文逗号为英文逗号
        for line_edit in [self.lineEdit_9, self.lineEdit_10]:
            line_edit.setText(line_edit.text().replace('，', ','))

        self.save_db_config()

    def save_db_config(self):
        config = {
            "agent_id": self.lineEdit_4.text().strip(),  # 自动去除首尾空格
            "server_url": self.lineEdit_3.text().strip(),  # 自动去除首尾空格
            "filter_conditions": {
                "sender_names": [name.strip() for name in self.lineEdit_9.text().split(',') if name.strip()],
                "conversation_titles": [title.strip() for title in self.lineEdit_10.text().split(',') if title.strip()]
            }
        }

        try:
            # 保存到文件
            with open(self.db_config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
                logging.info("Database configuration saved.")

            self.modules_to_refresh.add("bulletin")

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

            self.modules_to_refresh.add("time")


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

            self.modules_to_refresh.add("shutdown")

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

                self.modules_to_refresh.add("news")

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
            self.modules_to_refresh.add("weather")
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

        # 只有在下拉框为空时才加载QSS文件列表
        if self.comboBox_themes.count() == 0:
            # 动态加载 QSS 文件
            qss_dir = './ui/qss'
            if os.path.exists(qss_dir):
                qss_files = [f for f in os.listdir(qss_dir) if f.endswith('.qss')]
                self.comboBox_themes.clear()
                self.comboBox_themes.addItems(qss_files)
            else:
                logging.warning(f"QSS 目录不存在: {qss_dir}")
                self.comboBox_themes.clear()

        self.load_current_theme()

        # 只有在没有连接信号时才连接信号
        if not self.comboBox_themes.signalsBlocked():
            try:
                self.comboBox_themes.currentIndexChanged.disconnect()
            except TypeError:
                pass
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
                        # 如果在comboBox中找不到该主题，则设置为默认主题
                        default_index = self.comboBox_themes.findText(default_qss)
                        if default_index >= 0:
                            self.comboBox_themes.setCurrentIndex(default_index)
                        else:
                            self.comboBox_themes.setCurrentText(default_qss)
                else:
                    # 文件不存在或主题文件不存在
                    QMessageBox.warning(self, "警告", f"QSS文件 {current_theme} 不存在，使用默认主题。")
                    default_index = self.comboBox_themes.findText(default_qss)
                    if default_index >= 0:
                        self.comboBox_themes.setCurrentIndex(default_index)
                    else:
                        self.comboBox_themes.setCurrentText(default_qss)
        except Exception as e:
            # 读取文件出错时的处理
            QMessageBox.warning(self, "警告", f"读取qss.txt出错: {e}，使用默认主题。")
            default_index = self.comboBox_themes.findText(default_qss)
            if default_index >= 0:
                self.comboBox_themes.setCurrentIndex(default_index)
            else:
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

################################计划消息###############################################################################

    def setup_plan_tasks_tab(self):
        """
        设置计划任务配置标签页
        """
        # 获取scrollArea_2用于预约消息，scrollArea_3用于循环消息
        self.scrollArea_2 = self.findChild(QScrollArea, "scrollArea_2")
        self.scrollArea_3 = self.findChild(QScrollArea, "scrollArea_3")

        if not self.scrollArea_2 or not self.scrollArea_3:
            logging.error("找不到 scrollArea_2 或 scrollArea_3")
            return

        # 初始化预约消息界面
        self.setup_appointment_messages_ui()

        # 初始化循环消息界面
        self.setup_loop_messages_ui()

        # 加载现有配置
        self.load_plan_tasks_config()

    def setup_appointment_messages_ui(self):
        """
        设置预约消息UI
        """
        # 创建预约消息的容器widget
        self.appointment_widget = QWidget()
        self.appointment_layout = QVBoxLayout(self.appointment_widget)

        # 添加标题
        title_label = QLabel("预约消息设置")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px 0;")
        self.appointment_layout.addWidget(title_label)

        # 添加按钮布局
        button_layout = QHBoxLayout()
        self.add_appointment_btn = QPushButton("添加预约消息")
        self.add_appointment_btn.clicked.connect(self.add_appointment_message)
        button_layout.addWidget(self.add_appointment_btn)
        button_layout.addStretch()
        self.appointment_layout.addLayout(button_layout)

        # 创建预约消息列表容器
        self.appointment_list_widget = QWidget()
        self.appointment_list_layout = QVBoxLayout(self.appointment_list_widget)
        self.appointment_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.appointment_layout.addWidget(self.appointment_list_widget)

        # 设置滚动区域
        self.scrollArea_2.setWidgetResizable(True)
        self.scrollArea_2.setWidget(self.appointment_widget)

    def setup_loop_messages_ui(self):
        """
        设置循环消息UI
        """
        # 创建循环消息的容器widget
        self.loop_widget = QWidget()
        self.loop_layout = QVBoxLayout(self.loop_widget)

        # 添加标题
        title_label = QLabel("循环消息设置")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px 0;")
        self.loop_layout.addWidget(title_label)

        # 添加按钮布局
        button_layout = QHBoxLayout()
        self.add_loop_btn = QPushButton("添加循环消息列表")
        self.add_loop_btn.clicked.connect(self.add_loop_message_list)
        button_layout.addWidget(self.add_loop_btn)
        button_layout.addStretch()
        self.loop_layout.addLayout(button_layout)

        # 创建循环消息列表容器
        self.loop_list_widget = QWidget()
        self.loop_list_layout = QVBoxLayout(self.loop_list_widget)
        self.loop_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.loop_layout.addWidget(self.loop_list_widget)

        # 设置滚动区域
        self.scrollArea_3.setWidgetResizable(True)
        self.scrollArea_3.setWidget(self.loop_widget)

    def load_plan_tasks_config(self):
        """
        加载计划任务配置
        """
        config_file = 'data/message_config.json'
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.plan_tasks_config = json.load(f)
            else:
                self.plan_tasks_config = {"appointment_message": {}, "loop_message": {}}
                logging.warning(f"配置文件 {config_file} 不存在")
        except Exception as e:
            logging.error(f"加载计划任务配置文件出错: {e}")
            self.plan_tasks_config = {"appointment_message": {}, "loop_message": {}}

        # 清除现有UI组件
        self.clear_appointment_messages_ui()
        self.clear_loop_messages_ui()

        # 加载预约消息
        appointment_messages = self.plan_tasks_config.get("appointment_message", {})
        # 按照消息键的顺序加载，确保界面显示顺序一致
        for message_key, message_data in appointment_messages.items():
            self.add_appointment_message(message_key, message_data)

        # 加载循环消息
        loop_messages = self.plan_tasks_config.get("loop_message", {})
        for list_name, list_data in loop_messages.items():
            self.add_loop_message_list(list_name, list_data)

    def clear_appointment_messages_ui(self):
        """
        清除预约消息UI组件
        """
        # 删除所有预约消息项（除了标题和按钮）
        while self.appointment_list_layout.count() > 0:
            item = self.appointment_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def clear_loop_messages_ui(self):
        """
        清除循环消息UI组件
        """
        # 删除所有循环消息项（除了标题和按钮）
        while self.loop_list_layout.count() > 0:
            item = self.loop_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def add_appointment_message(self, message_key="", message_data=None):
        """
        添加预约消息UI项
        """
        # 如果没有提供消息键，则生成一个新的唯一键
        if not message_key:
            message_key = self._generate_unique_appointment_key()

        if message_data is None:
            message_data = {"time": "", "text": "", "message": "", "remind_time": ""}

        # 创建预约消息组框
        group_box = QGroupBox()
        group_box.setProperty("message_key", message_key)  # 存储消息键
        group_layout = QVBoxLayout(group_box)

        # 时间输入（可以是日期或星期）
        time_layout = QHBoxLayout()
        time_label = QLabel("时间:")
        time_edit = QLineEdit()
        time_edit.setPlaceholderText("输入日期(yyyy-MM-dd)或星期(Monday-Sunday)")
        time_value = message_data.get("time", "")
        time_edit.setText(time_value)

        # 连接时间变化信号，使用 QTimer.singleShot 延迟执行保存
        time_edit.textChanged.connect(self._delayed_save_plan_tasks_config)

        time_layout.addWidget(time_label)
        time_layout.addWidget(time_edit)
        time_layout.addStretch()

        # 删除按钮
        delete_btn = QPushButton("删除")
        # 使用自定义属性存储引用
        delete_btn.setProperty("group_box", group_box)
        delete_btn.clicked.connect(self._on_delete_appointment_clicked)
        time_layout.addWidget(delete_btn)
        group_layout.addLayout(time_layout)

        # 文本内容
        text_label = QLabel("显示文本:")
        text_edit = QTextEdit()
        text_edit.setMaximumHeight(60)
        text_edit.setPlaceholderText("在此输入要显示的文本内容")
        text_edit.setText(message_data.get("text", ""))
        # 连接文本变化信号，使用 QTimer.singleShot 延迟执行保存
        text_edit.textChanged.connect(self._delayed_save_plan_tasks_config)
        group_layout.addWidget(text_label)
        group_layout.addWidget(text_edit)

        # 提醒消息
        message_label = QLabel("提醒消息:")
        message_edit = QTextEdit()
        message_edit.setMaximumHeight(60)
        message_edit.setPlaceholderText("在此输入提醒时弹出的消息（可选）")
        message_edit.setText(message_data.get("message", ""))
        # 连接文本变化信号，使用 QTimer.singleShot 延迟执行保存
        message_edit.textChanged.connect(self._delayed_save_plan_tasks_config)
        group_layout.addWidget(message_label)
        group_layout.addWidget(message_edit)

        # 提醒时间
        remind_layout = QHBoxLayout()
        remind_label = QLabel("提醒时间:")
        remind_time_edit = QTimeEdit()
        remind_time_edit.setDisplayFormat("HH:mm")
        if message_data.get("remind_time"):
            try:
                time = QTime.fromString(message_data["remind_time"], "HH:mm")
                remind_time_edit.setTime(time)
            except:
                remind_time_edit.setTime(QTime.currentTime())
        else:
            remind_time_edit.setTime(QTime.currentTime())

        # 连接时间变化信号，使用 QTimer.singleShot 延迟执行保存
        remind_time_edit.timeChanged.connect(self._delayed_save_plan_tasks_config)

        remind_layout.addWidget(remind_label)
        remind_layout.addWidget(remind_time_edit)
        remind_layout.addStretch()
        group_layout.addLayout(remind_layout)

        # 添加到列表布局的最前面
        self.appointment_list_layout.insertWidget(0, group_box)

    def _generate_unique_text_item_id(self, group_box):
        """
        为指定的循环消息列表生成唯一的文本项ID
        """
        # 获取当前组框中的所有文本项ID
        existing_ids = set()

        # 查找文本项容器
        texts_widgets = group_box.findChildren(QWidget)
        texts_widget = None
        for widget in texts_widgets:
            if widget.layout() and widget.layout().count() > 0:
                texts_widget = widget
                break

        if texts_widget:
            texts_layout = texts_widget.layout()
            if texts_layout:
                for j in range(texts_layout.count()):
                    item_widget = texts_layout.itemAt(j)
                    if not item_widget:
                        continue

                    item_group_box = item_widget.widget()
                    if isinstance(item_group_box, QGroupBox):
                        # 获取标识符
                        id_edits = item_group_box.findChildren(QLineEdit)
                        if id_edits:
                            item_id = id_edits[0].text().strip()
                            if item_id:
                                existing_ids.add(item_id)

        # 从配置文件中获取当前列表的文本项ID
        list_name = group_box.property("list_name")
        if list_name:
            config_file = 'data/message_config.json'
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        loop_messages = config.get("loop_message", {})
                        if list_name in loop_messages:
                            text_data = loop_messages[list_name].get("text", {})
                            # 过滤掉特殊字段
                            text_items = {k: v for k, v in text_data.items()
                                          if isinstance(v, dict) and k not in ["id_now", "date_now"]}
                            existing_ids.update(text_items.keys())
                except Exception:
                    pass

        # 生成新的唯一ID
        counter = 1
        while f"text_{counter}" in existing_ids:
            counter += 1
        return f"text_{counter}"

    def _generate_unique_loop_list_name(self):
        """
        生成唯一的循环消息列表名称
        """
        # 获取当前已有的所有列表名称
        existing_names = set()
        for i in range(self.loop_list_layout.count()):
            widget_item = self.loop_list_layout.itemAt(i)
            if widget_item and widget_item.widget():
                group_box = widget_item.widget()
                if isinstance(group_box, QGroupBox):
                    name = group_box.property("list_name")
                    if name:
                        existing_names.add(name)

        # 从配置文件中获取已有的列表名称
        config_file = 'data/message_config.json'
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    existing_names.update(config.get("loop_message", {}).keys())
            except Exception:
                pass

        # 生成新的唯一名称
        counter = 1
        while f"新列表_{counter}" in existing_names:
            counter += 1
        return f"新列表_{counter}"

    def _on_delete_appointment_clicked(self):
        """
        删除预约消息项的槽函数
        """
        sender = self.sender()
        group_box = sender.property("group_box")
        if group_box:
            self.delete_appointment_message(group_box)

    def _delayed_save_plan_tasks_config(self):
        """
        延迟保存计划任务配置，避免频繁保存导致卡顿
        """
        # 使用 QTimer.singleShot 延迟执行保存操作
        if not hasattr(self, '_save_timer'):
            self._save_timer = QTimer()
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self.save_plan_tasks_config)

        # 重启计时器，延迟1秒执行保存
        self._save_timer.start(1000)

    def delete_appointment_message(self, group_box):
        """
        删除预约消息项
        """
        self.appointment_list_layout.removeWidget(group_box)
        group_box.deleteLater()
        self.save_plan_tasks_config()

    def add_loop_message_list(self, list_name="", list_data=None):
        """
        添加循环消息列表UI项
        """
        # 如果没有提供列表名称，则生成一个新的唯一名称
        if not list_name:
            list_name = self._generate_unique_loop_list_name()

        if list_data is None:
            list_data = {
                "text": {
                    "text_1": {"text": "", "message": "", "remain_time": ""},
                    "id_now": "text_1",
                    "date_now": ""
                },
                "suspension_date": []
            }

        # 创建循环消息组框
        group_box = QGroupBox()
        group_box.setProperty("list_name", list_name)  # 存储列表名称
        group_layout = QVBoxLayout(group_box)

        # 列表名称
        name_layout = QHBoxLayout()
        name_label = QLabel("列表名称:")
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("输入列表名称")
        name_edit.setText(list_name)

        # 连接名称变化信号，使用 QTimer.singleShot 延迟执行保存
        name_edit.textChanged.connect(self._delayed_save_plan_tasks_config)

        name_layout.addWidget(name_label)
        name_layout.addWidget(name_edit)

        # 删除按钮
        delete_btn = QPushButton("删除")
        # 使用自定义属性存储引用
        delete_btn.setProperty("group_box", group_box)
        delete_btn.clicked.connect(self._on_delete_loop_list_clicked)
        name_layout.addWidget(delete_btn)
        group_layout.addLayout(name_layout)

        # 暂停日期
        suspension_layout = QHBoxLayout()
        suspension_label = QLabel("暂停日期:")
        suspension_edit = QLineEdit()
        suspension_edit.setPlaceholderText("输入暂停日期，用逗号分隔（如: 2025-9-13, Sunday）")
        suspension_dates = list_data.get("suspension_date", [])
        suspension_edit.setText(", ".join(suspension_dates))

        # 连接暂停日期变化信号，使用 QTimer.singleShot 延迟执行保存
        suspension_edit.textChanged.connect(self._delayed_save_plan_tasks_config)

        suspension_layout.addWidget(suspension_label)
        suspension_layout.addWidget(suspension_edit)
        group_layout.addLayout(suspension_layout)

        # 文本项标题
        texts_label = QLabel("文本项:")
        texts_label.setStyleSheet("font-weight: bold;")
        group_layout.addWidget(texts_label)

        # 文本项容器
        texts_widget = QWidget()
        texts_layout = QVBoxLayout(texts_widget)

        # 添加现有文本项
        text_data = list_data.get("text", {})
        for key, item_data in text_data.items():
            if isinstance(item_data, dict) and key not in ["id_now", "date_now"]:
                self.add_loop_text_item(texts_layout, key, item_data)

        group_layout.addWidget(texts_widget)

        # 添加文本项按钮
        add_text_layout = QHBoxLayout()
        add_text_btn = QPushButton("添加文本项")
        # 使用自定义属性存储引用
        add_text_btn.setProperty("texts_layout", texts_layout)
        add_text_btn.setProperty("group_box", group_box)  # 存储组框引用
        add_text_btn.clicked.connect(self._on_add_text_item_clicked)
        add_text_layout.addStretch()
        add_text_layout.addWidget(add_text_btn)
        group_layout.addLayout(add_text_layout)

        # 添加到列表布局
        self.loop_list_layout.addWidget(group_box)

    def _on_add_text_item_clicked(self):
        """
        添加文本项按钮点击处理
        """
        sender = self.sender()
        texts_layout = sender.property("texts_layout")
        group_box = sender.property("group_box")  # 获取组框引用
        if texts_layout and group_box:
            # 生成唯一的文本项ID
            unique_id = self._generate_unique_text_item_id(group_box)
            self.add_loop_text_item(texts_layout, unique_id)

    def add_loop_text_item(self, parent_layout, key="", item_data=None):
        """
        添加循环消息文本项
        """
        if item_data is None:
            item_data = {"text": "", "message": "", "remain_time": ""}

        # 创建文本项组框
        item_group_box = QGroupBox()
        item_group_box.setProperty("item_id", key)  # 存储项ID
        item_layout = QVBoxLayout(item_group_box)

        # 标识符
        id_layout = QHBoxLayout()
        id_label = QLabel("标识符:")
        id_edit = QLineEdit()
        id_edit.setPlaceholderText("文本项标识符（如: text_1）")
        id_edit.setText(key)

        # 连接标识符变化信号，使用 QTimer.singleShot 延迟执行保存
        id_edit.textChanged.connect(self._delayed_save_plan_tasks_config)

        delete_btn = QPushButton("删除")
        # 使用自定义属性存储引用
        delete_btn.setProperty("item_group_box", item_group_box)
        delete_btn.clicked.connect(self._on_delete_text_item_clicked)
        id_layout.addWidget(id_label)
        id_layout.addWidget(id_edit)
        id_layout.addWidget(delete_btn)
        item_layout.addLayout(id_layout)

        # 文本内容
        text_label = QLabel("显示文本:")
        text_edit = QTextEdit()
        text_edit.setMaximumHeight(60)
        text_edit.setPlaceholderText("在此输入要显示的文本内容")
        text_edit.setText(item_data.get("text", ""))

        # 连接文本变化信号，使用 QTimer.singleShot 延迟执行保存
        text_edit.textChanged.connect(self._delayed_save_plan_tasks_config)

        item_layout.addWidget(text_label)
        item_layout.addWidget(text_edit)

        # 提醒消息
        message_label = QLabel("提醒消息:")
        message_edit = QTextEdit()
        message_edit.setMaximumHeight(60)
        message_edit.setPlaceholderText("在此输入提醒时弹出的消息（可选）")
        message_edit.setText(item_data.get("message", ""))

        # 连接消息变化信号，使用 QTimer.singleShot 延迟执行保存
        message_edit.textChanged.connect(self._delayed_save_plan_tasks_config)

        item_layout.addWidget(message_label)
        item_layout.addWidget(message_edit)

        # 提醒时间
        remain_layout = QHBoxLayout()
        remain_label = QLabel("提醒时间:")
        remain_time_edit = QTimeEdit()
        remain_time_edit.setDisplayFormat("HH:mm")
        if item_data.get("remain_time"):
            try:
                time = QTime.fromString(item_data["remain_time"], "HH:mm")
                remain_time_edit.setTime(time)
            except:
                remain_time_edit.setTime(QTime.currentTime())
        else:
            remain_time_edit.setTime(QTime.currentTime())

        # 连接时间变化信号，使用 QTimer.singleShot 延迟执行保存
        remain_time_edit.timeChanged.connect(self._delayed_save_plan_tasks_config)

        remain_layout.addWidget(remain_label)
        remain_layout.addWidget(remain_time_edit)
        remain_layout.addStretch()
        item_layout.addLayout(remain_layout)

        parent_layout.addWidget(item_group_box)

    def _on_delete_text_item_clicked(self):
        """
        删除循环消息文本项的槽函数
        """
        sender = self.sender()
        item_group_box = sender.property("item_group_box")
        if item_group_box:
            self.delete_loop_text_item(item_group_box)

    def _on_delete_loop_list_clicked(self):
        """
        删除循环消息列表的槽函数
        """
        sender = self.sender()
        group_box = sender.property("group_box")
        if group_box:
            self.delete_loop_message_list(group_box)

    def delete_loop_text_item(self, item_group_box):
        """
        删除循环消息文本项
        """
        item_group_box.setParent(None)
        item_group_box.deleteLater()
        self.save_plan_tasks_config()

    def delete_loop_message_list(self, group_box):
        """
        删除循环消息列表
        """
        self.loop_list_layout.removeWidget(group_box)
        group_box.deleteLater()
        self.save_plan_tasks_config()

    def _generate_unique_appointment_key(self):
        """
        生成唯一的预约消息键
        """
        # 获取当前已有的所有消息键
        existing_keys = set()
        for i in range(self.appointment_list_layout.count()):
            widget_item = self.appointment_list_layout.itemAt(i)
            if widget_item and widget_item.widget():
                group_box = widget_item.widget()
                if isinstance(group_box, QGroupBox):
                    key = group_box.property("message_key")
                    if key:
                        existing_keys.add(key)

        # 从配置文件中获取已有的键
        config_file = 'data/message_config.json'
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    existing_keys.update(config.get("appointment_message", {}).keys())
            except Exception:
                pass

        # 生成新的唯一键
        counter = 1
        while f"message_{counter}" in existing_keys:
            counter += 1
        return f"message_{counter}"

    def save_plan_tasks_config(self):
        """
        保存计划任务配置
        """
        config = {"appointment_message": {}, "loop_message": {}}

        # 保存预约消息
        appointment_messages = {}
        for i in range(self.appointment_list_layout.count()):
            widget_item = self.appointment_list_layout.itemAt(i)
            if not widget_item:
                continue

            group_box = widget_item.widget()
            if isinstance(group_box, QGroupBox):
                try:
                    # 获取消息键
                    message_key = group_box.property("message_key")
                    if not message_key:
                        # 如果没有消息键，跳过保存
                        continue

                    # 获取时间
                    time_edits = group_box.findChildren(QLineEdit)
                    time_value = time_edits[0].text().strip() if len(time_edits) > 0 else ""

                    # 获取文本内容
                    text_edits = group_box.findChildren(QTextEdit)
                    text_content = text_edits[0].toPlainText() if len(text_edits) > 0 else ""

                    # 获取提醒消息
                    message_content = text_edits[1].toPlainText() if len(text_edits) > 1 else ""

                    # 获取提醒时间
                    time_widgets = group_box.findChildren(QTimeEdit)
                    remind_time = time_widgets[0].time().toString("HH:mm") if len(time_widgets) > 0 else ""

                    appointment_messages[message_key] = {
                        "time": time_value,
                        "text": text_content,
                        "message": message_content,
                        "remind_time": remind_time
                    }
                except Exception as e:
                    logging.error(f"保存预约消息时出错: {e}")
                    continue

        config["appointment_message"] = appointment_messages

        # 保存循环消息
        for i in range(self.loop_list_layout.count()):
            widget_item = self.loop_list_layout.itemAt(i)
            if not widget_item:
                continue

            group_box = widget_item.widget()
            if isinstance(group_box, QGroupBox):
                try:
                    # 获取列表名称
                    name_edit = group_box.findChild(QLineEdit)
                    if not name_edit:
                        continue
                    list_name = name_edit.text()

                    if list_name:
                        # 获取暂停日期
                        suspension_edits = group_box.findChildren(QLineEdit)
                        suspension_text = suspension_edits[1].text() if len(suspension_edits) > 1 else ""
                        suspension_dates = [d.strip() for d in suspension_text.split(",") if d.strip()]

                        # 获取文本项
                        text_items = {}

                        # 查找文本项容器
                        texts_widgets = group_box.findChildren(QWidget)
                        texts_widget = None
                        for widget in texts_widgets:
                            if widget.layout() and widget.layout().count() > 0:
                                texts_widget = widget
                                break

                        if texts_widget:
                            texts_layout = texts_widget.layout()
                            if texts_layout:
                                used_ids = set()  # 跟踪已使用的ID

                                for j in range(texts_layout.count()):
                                    item_widget = texts_layout.itemAt(j)
                                    if not item_widget:
                                        continue

                                    item_group_box = item_widget.widget()
                                    if isinstance(item_group_box, QGroupBox):
                                        # 获取标识符
                                        id_edits = item_group_box.findChildren(QLineEdit)
                                        if not id_edits:
                                            continue

                                        item_id = id_edits[0].text().strip()

                                        # 处理重复ID
                                        original_id = item_id
                                        counter = 1
                                        while item_id in used_ids:
                                            item_id = f"{original_id}_{counter}"
                                            counter += 1
                                        used_ids.add(item_id)

                                        # 获取文本内容
                                        text_edits = item_group_box.findChildren(QTextEdit)
                                        text_content = text_edits[0].toPlainText() if len(text_edits) > 0 else ""

                                        # 获取提醒消息
                                        message_content = text_edits[1].toPlainText() if len(text_edits) > 1 else ""

                                        # 获取提醒时间
                                        time_edits = item_group_box.findChildren(QTimeEdit)
                                        remain_time = time_edits[0].time().toString("HH:mm") if len(
                                            time_edits) > 0 else ""

                                        text_items[item_id] = {
                                            "text": text_content,
                                            "message": message_content,
                                            "remain_time": remain_time
                                        }

                        # 添加默认字段
                        if text_items:  # 只有当有文本项时才设置id_now
                            text_items["id_now"] = list(text_items.keys())[0] if text_items.keys() else "text_1"
                        else:
                            text_items["id_now"] = ""
                        text_items["date_now"] = ""

                        config["loop_message"][list_name] = {
                            "text": text_items,
                            "suspension_date": suspension_dates
                        }
                except Exception as e:
                    logging.error(f"保存循环消息时出错: {e}")
                    continue

        # 保存到文件
        config_file = 'data/message_config.json'
        try:
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.modules_to_refresh.add("plan_tasks")
            logging.info("计划任务配置已保存")
        except Exception as e:
            logging.error(f"保存计划任务配置文件出错: {e}")




