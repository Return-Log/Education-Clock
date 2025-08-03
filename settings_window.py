
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
    QVBoxLayout, QScrollArea, QHBoxLayout, QGridLayout, QLineEdit, QSizePolicy, QTextEdit
)
from PyQt6.uic import loadUi
from PyQt6.QtCore import QTimer, QDateTime, QDate, QThread, pyqtSignal


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

        # 连接信号
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



