import os
import json
import pymysql
from datetime import datetime, timedelta
from markdown import markdown
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QUrl
from PyQt6.QtMultimedia import QSoundEffect


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        return super(DateTimeEncoder, self).default(obj)

class BulletinBoardWorker(QThread):
    update_signal = pyqtSignal(str)

    def __init__(self, db_config, filter_conditions):
        super().__init__()
        self.db_config = db_config
        self.filter_conditions = filter_conditions

    def run(self):
        try:
            # 连接数据库
            connection = pymysql.connect(
                host=self.db_config["host"],
                port=self.db_config["port"],
                user=self.db_config["user"],
                password=self.db_config["password"],
                database=self.db_config["database"],
                cursorclass=pymysql.cursors.DictCursor
            )
            cursor = connection.cursor()

            # 获取最近7天的数据
            start_date = datetime.now() - timedelta(days=7)
            query = """
            SELECT * FROM messages
            WHERE timestamp >= %s
            ORDER BY timestamp DESC
            """
            cursor.execute(query, (start_date,))
            rows = cursor.fetchall()

            # 过滤数据
            filtered_rows = self.filter_data(rows)

            # 存储在 data/sql.json
            with open('data/sql.json', 'w', encoding='utf-8') as f:
                json.dump(filtered_rows, f, ensure_ascii=False, indent=4, cls=DateTimeEncoder)

            # 更新 textEdit
            formatted_text = self.format_text(filtered_rows)
            self.update_signal.emit(formatted_text)

        except pymysql.MySQLError as e:
            self.update_signal.emit(f"Database Error: {str(e)}")
        except FileNotFoundError as e:
            self.update_signal.emit(f"File Not Found Error: {str(e)}")
        except json.JSONDecodeError as e:
            self.update_signal.emit(f"JSON Decode Error: {str(e)}")
        except Exception as e:
            self.update_signal.emit(f"Unexpected Error: {str(e)}")
        finally:
            if connection:
                connection.close()

    def filter_data(self, rows):
        filtered_rows = []
        for row in rows:
            # 检查每个过滤条件是否为空，为空则跳过该条件
            robot_names = self.filter_conditions["robot_names"]
            sender_names = self.filter_conditions["sender_names"]
            conversation_titles = self.filter_conditions["conversation_titles"]

            if (not robot_names or row['robot_name'] in robot_names) and \
               (not sender_names or row['sender_name'] in sender_names) and \
               (not conversation_titles or row['conversationTitle'] in conversation_titles):
                filtered_rows.append(row)
        return filtered_rows

    def format_text(self, rows):
        formatted_text = ""
        for row in rows:
            sender_name = row['sender_name']
            created_at = row['timestamp'].strftime("%m-%d %H:%M")
            message_content = row['message_content']

            # 格式化消息
            formatted_message = f"<b style='color:#4cc2ff; font-size:16px;'>{sender_name} ({created_at})</b>{markdown(message_content)}<hr>"
            formatted_text += formatted_message

        return formatted_text

class BulletinBoardModule:
    def __init__(self, main_window, text_edit):
        self.main_window = main_window
        self.text_edit = text_edit
        self.timer = QTimer(self.main_window)
        self.timer.timeout.connect(self.update_bulletin_board)
        self.last_update_time = datetime.now()
        self.last_message_text = ""  # 用于记录最新的消息内容
        self.sound_effect = QSoundEffect()
        self.sound_effect.setSource(QUrl.fromLocalFile("icon/newmessage.wav"))
        self.played_for_latest_message = False  # 标志位，用于控制每条新消息只播放一次音效

        # 初始化时检查配置文件
        if not self.check_db_config():
            self.timer.stop()  # 停止定时器，避免后续操作

    def check_db_config(self):
        try:
            # 读取数据库配置和过滤条件
            with open('data/db_config.json', 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                db_config = config_data.get("db_config", {})

            # 检查配置项是否为空
            required_fields = ["host", "port", "user", "password", "database"]
            for field in required_fields:
                if not db_config.get(field):
                    self.update_text_edit(f"Configuration Error: {field} is empty in db_config.json")
                    return False

            # 保存配置项
            self.db_config = db_config
            self.filter_conditions = config_data.get("filter_conditions", {})
            self.timer.start(5000)  # 每隔5秒更新
            return True

        except FileNotFoundError as e:
            self.update_text_edit(f"File Not Found Error: {str(e)}")
            return False
        except json.JSONDecodeError as e:
            self.update_text_edit(f"JSON Decode Error: {str(e)}")
            return False
        except Exception as e:
            self.update_text_edit(f"Unexpected Error: {str(e)}")
            return False

    def update_bulletin_board(self):
        try:
            self.worker = BulletinBoardWorker(self.db_config, self.filter_conditions)
            self.worker.update_signal.connect(self.update_text_edit)
            self.worker.start()

        except Exception as e:
            self.update_text_edit(f"Unexpected Error: {str(e)}")

    def update_text_edit(self, text):
        try:
            current_text = self.text_edit.toPlainText()
            if "Error" not in text and current_text != text:
                # 检查是否需要播放音效
                if text != self.last_message_text:
                    self.play_new_message_sound_if_needed()
                    self.last_message_text = text  # 更新最新消息内容
                    self.played_for_latest_message = False  # 重置标志位，以便下次新消息可以播放音效

            self.text_edit.setHtml(text)
            self.last_update_time = datetime.now()
        except Exception as e:
            print(f"Error updating text edit: {str(e)}")

    def play_new_message_sound_if_needed(self):
        current_time = datetime.now()
        time_diff = current_time - self.last_update_time

        # 如果新消息和系统时间的差值小于等于5秒，并且音效还未播放
        if time_diff.total_seconds() <= 5 and not self.played_for_latest_message:
            self.sound_effect.play()
            self.played_for_latest_message = True  # 设置标志位，确保当前消息音效只播放一次

    def stop_timer(self):
        if self.timer.isActive():
            self.timer.stop()

    def start_timer(self):
        if not self.timer.isActive():
            self.timer.start(5000)

    def cleanup(self):
        self.stop_timer()
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait()