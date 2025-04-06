import sys
import os
import json
import base64
import logging
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6 import uic
import pymysql
import re

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler()])

class DatabaseWorker(QThread):
    """数据库操作线程"""
    data_fetched = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    message_sent = pyqtSignal()
    message_deleted = pyqtSignal()

    def __init__(self, db_config, table_name, robot_name=None):
        super().__init__()
        self.db_config = db_config
        self.table_name = table_name
        self.robot_name = robot_name
        self.task = None
        self.message = None

    def run(self):
        try:
            with pymysql.connect(**self.db_config, cursorclass=pymysql.cursors.DictCursor) as conn:
                with conn.cursor() as cursor:
                    if self.task == "fetch":
                        query = f"SELECT * FROM `{self.table_name}` WHERE `robot_name` = %s ORDER BY `timestamp` DESC"
                        cursor.execute(query, (self.robot_name,))
                        data = cursor.fetchall()
                        self.data_fetched.emit(data)
                    elif self.task == "delete":
                        query = f"DELETE FROM `{self.table_name}` WHERE `timestamp` = %s AND `robot_name` = %s"
                        cursor.execute(query, (self.message["timestamp"], self.robot_name))
                        conn.commit()
                        self.message_deleted.emit()
                    elif self.task == "insert":
                        query = f"INSERT INTO `{self.table_name}` (`robot_name`, `sender_name`, `message_content`, `timestamp`, `conversationTitle`) VALUES (%s, %s, %s, %s, %s)"
                        cursor.execute(query, (
                            self.message["robot_name"],
                            self.message["sender_name"],
                            self.message["message_content"],
                            self.message["timestamp"],
                            self.message["conversationTitle"]
                        ))
                        conn.commit()
                        self.message_sent.emit()
        except pymysql.MySQLError as e:
            self.error_occurred.emit(f"数据库错误: {str(e)}")
        except Exception as e:
            self.error_occurred.emit(f"线程错误: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.encryption_key = 0x5A
        self.device_name = os.environ.get("COMPUTERNAME", "Unknown")
        self.db_config = None
        self.table_name = "messages"
        self.config_path = "./data/db_config.json"

        try:
            # 加载 UI 文件
            if not os.path.exists("./ui/db_manager.ui"):
                logging.error("db_manager.ui 文件不存在")
                raise FileNotFoundError("db_manager.ui 文件不存在")
            uic.loadUi("./ui/db_manager.ui", self)
            logging.info("成功加载 db_manager.ui")

            # 检查关键控件
            required_widgets = ["label_4", "pushButton_3", "pushButton_4", "pushButton_5",
                               "tableWidget", "plainTextEdit", "lineEdit_2", "plainTextEdit_2"]
            for widget in required_widgets:
                if not hasattr(self, widget):
                    logging.error(f"UI 中缺少控件: {widget}")
                    raise AttributeError(f"UI 中缺少控件: {widget}")

            # 设置初始 UI
            self.label_4.setText(f"设备名称: {self.device_name}")
            self.setup_ui_connections()

            # 使用 QTimer 延迟加载数据库，避免初始化冲突
            QTimer.singleShot(100, self.update_db_config_and_fetch)

        except Exception as e:
            logging.error(f"初始化失败: {str(e)}")
            self.log(f"程序初始化失败: {str(e)}", True)
            raise

    def setup_ui_connections(self):
        """设置 UI 信号连接"""
        try:
            self.pushButton_3.clicked.connect(self.delete_selected_message)
            self.pushButton_4.clicked.connect(self.send_message)
            self.pushButton_5.clicked.connect(self.add_device_to_filter)
            self.tableWidget.setColumnCount(5)
            self.tableWidget.setHorizontalHeaderLabels(["Robot Name", "Sender Name", "Message Content", "Timestamp", "Conversation Title"])
            self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            logging.info("UI 信号连接成功")
        except Exception as e:
            self.log(f"设置 UI 连接失败: {str(e)}", True)
            raise

    def log(self, message, is_error=False):
        prefix = "ERROR: " if is_error else "INFO: "
        if hasattr(self, "plainTextEdit_2"):
            self.plainTextEdit_2.appendPlainText(f"{prefix}{message}")
        logging.info(f"{prefix}{message}")

    def xor_encrypt_decrypt(self, data, key):
        return bytes([b ^ key for b in data])

    def decrypt_data(self, encrypted_data, key):
        try:
            decoded_data = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = self.xor_encrypt_decrypt(decoded_data, key)
            return json.loads(decrypted_data.decode('utf-8'))
        except Exception as e:
            self.log(f"解密失败: {str(e)}", True)
            return None

    def encrypt_data(self, data, key):
        json_data = json.dumps(data, ensure_ascii=False, indent=4).encode('utf-8')
        encrypted_data = self.xor_encrypt_decrypt(json_data, key)
        return base64.b64encode(encrypted_data).decode('utf-8')

    def update_db_config_and_fetch(self):
        """更新数据库配置并获取数据"""
        if not os.path.exists(self.config_path):
            self.log(f"数据库配置文件不存在: {self.config_path}", True)
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                encrypted_data = f.read().strip()
            if not encrypted_data:
                self.log(f"配置文件 {self.config_path} 为空", True)
                return

            config_data = self.decrypt_data(encrypted_data, self.encryption_key)
            if not config_data:
                self.log("解密配置文件失败", True)
                return

            db_config = config_data.get("db_config", {})
            required_fields = ["host", "port", "user", "password", "database"]
            missing = [field for field in required_fields if not db_config.get(field)]
            if missing:
                self.log(f"配置文件缺少字段: {', '.join(missing)}", True)
                return

            db_config["port"] = int(db_config["port"])
            self.db_config = db_config
            self.log("数据库配置加载成功")
            self.fetch_messages()
        except Exception as e:
            self.log(f"读取数据库配置失败: {str(e)}", True)

    def fetch_messages(self):
        """从数据库获取消息"""
        if not self.db_config:
            self.log("数据库配置未加载", True)
            return
        try:
            self.worker = DatabaseWorker(self.db_config, self.table_name, self.device_name)
            self.worker.task = "fetch"
            self.worker.data_fetched.connect(self.update_table)
            self.worker.error_occurred.connect(self.log_error)
            self.worker.start()
            self.log("开始获取消息")
        except Exception as e:
            self.log(f"启动消息获取线程失败: {str(e)}", True)

    def update_table(self, data):
        """更新 tableWidget"""
        try:
            if not data:
                self.log("没有消息数据可加载")
                self.tableWidget.setRowCount(0)
                return

            self.log(f"准备加载 {len(data)} 条消息到 tableWidget")
            self.tableWidget.setRowCount(len(data))
            for row, item in enumerate(data):
                fields = [
                    str(item.get("robot_name", "") or ""),
                    str(item.get("sender_name", "") or ""),
                    str(item.get("message_content", "") or ""),
                    str(item.get("timestamp", "") or ""),
                    str(item.get("conversationTitle", "") or "")
                ]
                for col, value in enumerate(fields):
                    table_item = QTableWidgetItem(value)
                    self.tableWidget.setItem(row, col, table_item)
            self.log(f"成功加载 {len(data)} 条消息")
        except Exception as e:
            self.log(f"更新 tableWidget 失败: {str(e)}", True)
            self.tableWidget.setRowCount(0)

    def add_device_to_filter(self):
        """将设备名称追加到 filter_conditions 的 robot_names 列表"""
        if not os.path.exists(self.config_path):
            self.log(f"配置文件不存在: {self.config_path}", True)
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                encrypted_data = f.read().strip()
            config_data = self.decrypt_data(encrypted_data, self.encryption_key)
            if not config_data:
                self.log("无法解密配置文件", True)
                return

            if "filter_conditions" not in config_data:
                config_data["filter_conditions"] = {}
            if "robot_names" not in config_data["filter_conditions"] or not isinstance(
                    config_data["filter_conditions"]["robot_names"], list):
                config_data["filter_conditions"]["robot_names"] = []

            robot_names = config_data["filter_conditions"]["robot_names"]
            if self.device_name not in robot_names:
                robot_names.append(self.device_name)
                self.log(f"已将设备名称 {self.device_name} 添加到 robot_names")

                encrypted_content = self.encrypt_data(config_data, self.encryption_key)
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    f.write(encrypted_content)
                self.log(f"配置文件已更新: {self.config_path}")
            else:
                self.log(f"设备名称 {self.device_name} 已存在于 robot_names，无需重复添加")

        except Exception as e:
            self.log(f"更新 filter_conditions 失败: {str(e)}", True)

    def delete_selected_message(self):
        """删除选中的消息"""
        selected = self.tableWidget.currentRow()
        if selected == -1:
            self.log("请先选择一条消息", True)
            return

        message = {
            "timestamp": self.tableWidget.item(selected, 3).text(),
            "robot_name": self.device_name
        }
        self.worker = DatabaseWorker(self.db_config, self.table_name, self.device_name)
        self.worker.task = "delete"
        self.worker.message = message
        self.worker.message_deleted.connect(self.on_message_deleted)
        self.worker.error_occurred.connect(self.log_error)
        self.worker.start()

    def on_message_deleted(self):
        self.log("消息已删除")
        self.fetch_messages()

    def send_message(self):
        """发送消息"""
        content = self.plainTextEdit.toPlainText().strip()
        sender = self.lineEdit_2.text().strip()

        if sender:
            if re.match(r'^https?://[^\s]+$', sender):
                content = f"&[{sender}]& {content}"
                self.log(f"检测到 URL，已拼接: {content}")

        if not content:
            self.log("消息内容不能为空", True)
            return

        message = {
            "robot_name": self.device_name,
            "sender_name": self.device_name,
            "message_content": content,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "conversationTitle": ""
        }

        self.worker = DatabaseWorker(self.db_config, self.table_name, self.device_name)
        self.worker.task = "insert"
        self.worker.message = message
        self.worker.message_sent.connect(self.on_message_sent)
        self.worker.error_occurred.connect(self.log_error)
        self.worker.start()

    def on_message_sent(self):
        self.log("消息发送成功")
        self.plainTextEdit.clear()
        self.lineEdit_2.clear()
        self.fetch_messages()

    def log_error(self, message):
        self.log(message, True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())