import json
import os
import base64
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QUrl
from PyQt6.QtMultimedia import QSoundEffect
from datetime import datetime, timedelta
from markdown import markdown
import pymysql

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        return super(DateTimeEncoder, self).default(obj)

class BulletinBoardWorker(QThread):
    update_signal = pyqtSignal(str, bool)  # 新增一个布尔参数，表示是否播放提示音

    def __init__(self, db_config, filter_conditions, text_edit):
        super().__init__()
        self.db_config = db_config
        self.filter_conditions = filter_conditions
        self.text_edit = text_edit

    def run(self):
        # 读取最后的消息 ID
        last_id = self.read_last_db_id()

        # 获取新消息并判断是否有新消息
        new_messages, has_new_message = self.fetch_and_filter_messages(last_id)

        # 更新 textEdit 并发送信号
        formatted_text = self.format_text(new_messages)
        self.update_signal.emit(formatted_text, has_new_message)

    def read_last_db_id(self):
        """ 读取 dbid.txt 文件中的最后一条消息 ID """
        last_id = 0
        if os.path.exists('data/dbid.txt'):
            try:
                with open('data/dbid.txt', 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        last_id = int(content)
            except ValueError as e:
                self.update_signal.emit(f"值错误: {str(e)}", False)
            except Exception as e:
                self.update_signal.emit(f"意外错误: {str(e)}", False)
        return last_id

    def fetch_and_filter_messages(self, last_id):
        """ 从数据库中获取并过滤消息，同时检查是否有新消息 """
        try:
            with pymysql.connect(
                host=self.db_config["host"],
                port=self.db_config["port"],
                user=self.db_config["user"],
                password=self.db_config["password"],
                database=self.db_config["database"],
                cursorclass=pymysql.cursors.DictCursor
            ) as connection:
                with connection.cursor() as cursor:
                    start_date = datetime.now() - timedelta(days=7)
                    query = """
                    SELECT * FROM messages
                    WHERE timestamp >= %s
                    ORDER BY timestamp DESC
                    """
                    cursor.execute(query, (start_date,))
                    rows = cursor.fetchall()

                    filtered_rows = self.filter_data(rows)
                    has_new_message = False
                    if filtered_rows:
                        latest_id = filtered_rows[0]['id']
                        has_new_message = last_id != latest_id
                        # 更新 dbid.txt 文件
                        with open('data/dbid.txt', 'w', encoding='utf-8') as f:
                            f.write(str(latest_id))

                    return filtered_rows, has_new_message

        except pymysql.MySQLError as e:
            # 数据库错误
            self.update_signal.emit(f"数据库错误: {str(e)}", False)
            return [], False
        except FileNotFoundError as e:
            # 文件未找到错误
            self.update_signal.emit(f"找不到文件: {str(e)}", False)
            return [], False
        except Exception as e:
            # 其他异常
            if "Errno 99" in str(e) or "Errno 111" in str(e) or "Errno 10065" in str(e):
                # 处理网络连接错误
                self.update_signal.emit(f"网络错误: {str(e)}", False)
                return [], False
            else:
                # 未知错误
                self.update_signal.emit(f"意外错误: {str(e)}", False)
                return [], False

    def filter_data(self, rows):
        filtered_rows = []
        for row in rows:
            robot_names = self.filter_conditions.get("robot_names", [])
            sender_names = self.filter_conditions.get("sender_names", [])
            conversation_titles = self.filter_conditions.get("conversation_titles", [])

            if (not robot_names or row['robot_name'] in robot_names) or \
               (not sender_names or row['sender_name'] in sender_names) or \
               (not conversation_titles or row['conversationTitle'] in conversation_titles):
                filtered_rows.append(row)
        return filtered_rows

    def format_text(self, rows):
        formatted_text = ""
        for row in rows:
            sender_name = row['sender_name']
            conversationTitle = row['conversationTitle']
            created_at = row['timestamp'].strftime("%m-%d %H:%M")
            message_content = row['message_content']

            # 根据 sender_name 设置颜色
            color = "#FFD700" if "管理组" in conversationTitle else "#4cc2ff"

            formatted_message = f"<b style='color:{color}; font-size:16px;'>{sender_name} ({created_at})</b>{markdown(message_content)}<hr>"
            formatted_text += formatted_message

        return formatted_text

    def update_text_edit(self, text, has_new_message):
        try:
            current_text = self.text_edit.toPlainText()
            if current_text != text:
                self.text_edit.setHtml(text)
                self.last_message_text = text

                if has_new_message:
                    self.play_new_message_sound()

        except Exception as e:
            self.update_text_edit(f"意外错误: {str(e)}", False)

    def play_new_message_sound(self):
        self.sound_effect.play()

class BulletinBoardModule:
    def __init__(self, main_window, text_edit):
        self.encryption_key = 0x5A
        self.main_window = main_window
        self.text_edit = text_edit
        self.timer = QTimer(self.main_window)
        self.timer.timeout.connect(self.update_bulletin_board)
        self.last_message_text = ""  # 用于记录最新的消息内容
        self.sound_effect = QSoundEffect()
        self.sound_effect.setSource(QUrl.fromLocalFile("icon/newmessage.wav"))

        if not self.check_db_config():
            self.timer.stop()  # 停止定时器，避免后续操作

    def check_db_config(self):
        try:
            with open('data/db_config.json', 'r', encoding='utf-8') as f:
                encrypted_data = f.read()
                config_data = self.decrypt_data(encrypted_data, self.encryption_key)
                db_config = config_data.get("db_config", {})

            required_fields = ["host", "port", "user", "password", "database"]
            for field in required_fields:
                if not db_config.get(field):
                    self.update_text_edit(f"配置错误: {field} 在 db_config.json 中为空", False)
                    return False

            db_config['port'] = int(db_config['port'])

            self.db_config = db_config
            self.filter_conditions = config_data.get("filter_conditions", {})
            self.timer.start(10000)  # 每隔10秒更新
            return True

        except FileNotFoundError as e:
            self.update_text_edit(f"找不到文件: {str(e)}", False)
            return False
        except json.JSONDecodeError as e:
            self.update_text_edit(f"JSON 解码错误: {str(e)}", False)
            return False
        except ValueError as e:
            self.update_text_edit(f"值错误: {str(e)}", False)
            return False
        except Exception as e:
            self.update_text_edit(f"意外错误: {str(e)}", False)
            return False

    def decrypt_data(self, encrypted_data, key):
        """解密数据"""
        decoded_data = base64.b64decode(encrypted_data.encode('utf-8'))
        decrypted_data = self.xor_encrypt_decrypt(decoded_data, key)
        return json.loads(decrypted_data.decode('utf-8'))

    def xor_encrypt_decrypt(self, data, key):
        """XOR 加密/解密函数"""
        return bytes([b ^ key for b in data])

    def update_bulletin_board(self):
        try:
            self.worker = BulletinBoardWorker(self.db_config, self.filter_conditions, self.text_edit)
            self.worker.update_signal.connect(self.update_text_edit)
            self.worker.start()

        except Exception as e:
            self.update_text_edit(f"意外错误: {str(e)}", False)

    def update_text_edit(self, text, has_new_message):
        try:
            current_text = self.text_edit.toPlainText()
            if current_text != text:
                self.text_edit.setHtml(text)
                self.last_message_text = text

                if has_new_message:
                    self.play_new_message_sound()

        except Exception as e:
            self.update_text_edit(f"意外错误: {str(e)}", False)

    def play_new_message_sound(self):
        self.sound_effect.play()

    def stop_timer(self):
        if self.timer.isActive():
            self.timer.stop()

    def start_timer(self):
        if not self.timer.isActive():
            self.timer.start(10000)

    def cleanup(self):
        self.stop_timer()
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait()
