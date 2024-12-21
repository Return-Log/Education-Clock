import json
import logging
import os
import base64
import re
import sys
from queue import Queue

from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QUrl, QEasingCurve, QAbstractAnimation, QParallelAnimationGroup
from PyQt6.QtMultimedia import QSoundEffect
from datetime import datetime, timedelta
from markdown import markdown
import pymysql
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QApplication
from PyQt6.QtCore import QTimer, Qt, QPropertyAnimation, QRect
from PyQt6.QtGui import QFont, QFontMetrics


class DanmakuWindow(QWidget):
    finished = pyqtSignal()

    def __init__(self, messages, parent=None):
        super().__init__(parent)
        self.messages = messages
        self.labels = []
        self.animations = []
        self.animation_group = None  # 保存动画组
        self.all_finished = False

        # 窗口属性和布局初始化
        self.setup_ui()
        self.init_animations()

    def setup_ui(self):
        screen_geometry = QApplication.primaryScreen().geometry()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("弹幕显示")
        self.move(0, 0)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)

        for message in self.messages:
            label = QLabel(self.sanitize_message(message), self)
            label.setStyleSheet("color: #ffffff; font-size: 30px;")
            label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            label.setProperty('bulletin', 'danmaku')  # 设置自定义属性
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # 确保所有属性设置完毕后调整大小
            label.adjustSize()  # 根据内容自动调整大小

            # 获取调整后的尺寸并设置最小和最大尺寸
            size_hint = label.sizeHint()
            padding = 40  # 左右各20像素的填充
            height_padding = 10  # 上下各5像素的填充

            label.setMinimumSize(size_hint.width() + padding, size_hint.height() + height_padding)
            label.setMaximumSize(size_hint.width() + padding, size_hint.height() + height_padding)

            self.layout.addWidget(label)
            self.labels.append(label)

        # 调整窗口大小以适应所有标签
        if self.labels:
            max_label_height = max(label.height() for label in self.labels)
            total_height = len(self.messages) * (max_label_height + self.layout.spacing()) - self.layout.spacing()
            self.resize(screen_geometry.width(), min(total_height, screen_geometry.height()))
        else:
            self.resize(screen_geometry.width(), 0)

    def sanitize_message(self, message):
        return message.replace("\n", " ").strip()

    def init_animations(self):
        screen_width = QApplication.primaryScreen().size().width()
        self.animation_group = QParallelAnimationGroup(self)
        for i, label in enumerate(self.labels):
            animation = QPropertyAnimation(label, b"geometry")
            animation.setDuration(30000)
            animation.setStartValue(
                QRect(screen_width + 50, i * (label.height() + self.layout.spacing()), label.width(), label.height()))
            animation.setEndValue(
                QRect(-label.width() - 50, i * (label.height() + self.layout.spacing()), label.width(), label.height()))
            animation.setEasingCurve(QEasingCurve.Type.Linear)
            self.animations.append(animation)
            self.animation_group.addAnimation(animation)

        self.animation_group.finished.connect(self.check_animation_finished)
        self.animation_group.start()

    def check_animation_finished(self):
        self.all_finished = True
        QTimer.singleShot(1000, self.close_danmaku)

    def close_danmaku(self):
        self.finished.emit()
        self.close()



class BulletinBoardWorker(QThread):
    update_signal = pyqtSignal(str, bool)  # 新增一个布尔参数，表示是否播放提示音

    def __init__(self, db_config, filter_conditions, text_edit):
        super().__init__()
        self.db_config = db_config
        self.filter_conditions = filter_conditions
        self.text_edit = text_edit
        self.theme_config = self.load_theme()


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
                        has_new_message = any(row['id'] > last_id for row in filtered_rows)
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

    def get_qss_path(self):
        default_qss = './ui/qss/dark.qss'
        qss_txt_path = './data/qss.txt'

        if not os.path.exists(qss_txt_path):
            return default_qss

        try:
            with open(qss_txt_path, 'r', encoding='utf-8') as f:
                qss_file = f.read().strip()
                if not qss_file:
                    return default_qss
                qss_path = os.path.join('./ui/qss', qss_file)
                if os.path.exists(qss_path):
                    return qss_path
                else:
                    print(f"QSS file {qss_file} does not exist, using default.")
                    return default_qss
        except Exception as e:
            print(f"Error reading qss.txt: {e}, using default.")
            return default_qss

    def parse_qss_colors(self, qss_file):
        colors = {}
        try:
            with open(qss_file, 'r', encoding='utf-8') as f:
                qss_content = f.read()

            # 使用正则表达式匹配颜色值
            pattern = re.compile(r'\.(\w+)\s*\{\s*color:\s*#([0-9a-fA-F]{6})\s*;\s*\}')
            matches = pattern.findall(qss_content)

            for match in matches:
                css_class, hex_color = match
                colors[css_class] = f"#{hex_color}"
        except Exception as e:
            print(f"Error parsing QSS file: {e}")
        return colors

    def load_theme(self):
        qss_path = self.get_qss_path()
        return self.parse_qss_colors(qss_path)

    def format_text(self, rows):
        formatted_text = ""
        for row in rows:
            sender_name = row['sender_name']
            conversationTitle = row['conversationTitle']
            created_at = row['timestamp'].strftime("%m-%d %H:%M")
            message_content = row['message_content']

            # 根据 conversationTitle 设置 CSS 类
            css_class = 'admin-sender' if "管理组" in conversationTitle else 'sender'
            color = self.theme_config.get(css_class, '#4cc2ff')  # 默认颜色

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
        super().__init__()
        self.encryption_key = 0x5A
        self.current_danmaku = None  # 当前正在显示的弹幕窗口
        self.danmaku_queue = Queue()  # 弹幕消息队列
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

        # 获取新消息
        fetched_messages, success = self.worker.fetch_and_filter_messages(self.worker.read_last_db_id())


        filtered_messages = self.worker.filter_data(fetched_messages)
        if isinstance(filtered_messages, tuple):  # 检查是否是元组
            filtered_messages = filtered_messages[0]

        if filtered_messages:
            # 获取最后一条消息
            last_message = filtered_messages[0]
            formatted_message = f"{last_message['sender_name']}：{last_message['message_content'].replace(' ', ' ').strip()}"

            # 将新消息加入弹幕队列
            self.danmaku_queue.put(formatted_message)
            self.display_next_danmaku()

    def display_next_danmaku(self):
        if not self.danmaku_queue.empty() and self.current_danmaku is None:
            # 从队列中获取下一个消息
            next_message = self.danmaku_queue.get()
            self.current_danmaku = DanmakuWindow([next_message])
            self.current_danmaku.finished.connect(self.on_danmaku_finished)  # 连接结束信号
            self.current_danmaku.show()

    def on_danmaku_finished(self):
        if self.current_danmaku:
            self.current_danmaku.deleteLater()  # 确保对象销毁
            self.current_danmaku = None  # 重置当前弹幕窗口
        self.display_next_danmaku()  # 检查是否需要显示下一个弹幕

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
