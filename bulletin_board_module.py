import json
import logging
import os
import base64
import re
import sys
from queue import Queue
import requests
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QUrl, QEasingCurve, QAbstractAnimation, QParallelAnimationGroup
from PyQt6.QtMultimedia import QSoundEffect
from datetime import datetime, timedelta
from markdown import markdown
import pymysql
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QApplication, QTextBrowser
from PyQt6.QtCore import QTimer, Qt, QPropertyAnimation, QRect
from PyQt6.QtGui import QFont, QFontMetrics, QDesktopServices

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class DownloadWorker(QThread):
    """文件下载工作线程"""
    download_finished = pyqtSignal(str, str, str, str, str, bool, str)  # 文件路径, 文件名, 原始消息, sender_name, created_at, 是否成功, 错误信息

    def __init__(self, url, message, sender_name, created_at, download_dir="./data/download/"):
        super().__init__()
        self.url = url
        self.message = message
        self.sender_name = sender_name
        self.created_at = created_at
        self.filename = os.path.basename(url.split('?')[0])
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    def run(self):
        """执行文件下载任务"""
        file_path = os.path.join(self.download_dir, self.filename)
        if os.path.exists(file_path):
            logging.info(f"文件已存在，跳过下载: {file_path}")
            self.download_finished.emit(file_path, self.filename, self.message, self.sender_name, self.created_at, True, "")
            return

        try:
            response = requests.get(self.url, stream=True, timeout=10)
            response.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info(f"文件下载成功: {file_path}")
            self.download_finished.emit(file_path, self.filename, self.message, self.sender_name, self.created_at, True, "")
        except requests.exceptions.HTTPError as e:
            error_msg = str(e)
            if e.response.status_code == 403:
                error_msg = "403 请求已达上限"
            logging.error(f"下载文件失败 {self.url}: {error_msg}")
            self.download_finished.emit(file_path, self.filename, self.message, self.sender_name, self.created_at, False, error_msg)
        except Exception as e:
            error_msg = str(e)
            logging.error(f"下载文件失败 {self.url}: {error_msg}")
            self.download_finished.emit(file_path, self.filename, self.message, self.sender_name, self.created_at, False, error_msg)

class DanmakuWindow(QWidget):
    finished = pyqtSignal()

    def __init__(self, messages, parent=None):
        super().__init__(parent)
        self.messages = messages
        self.labels = []
        self.animations = []
        self.animation_group = None
        self.all_finished = False
        self.setup_ui()
        self.init_animations()

    def setup_ui(self):
        """设置弹幕窗口的 UI"""
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
            label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            label.setProperty('bulletin', 'danmaku')
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.adjustSize()
            size_hint = label.sizeHint()
            padding, height_padding = 40, 10
            label.setMinimumSize(size_hint.width() + padding, size_hint.height() + height_padding)
            label.setMaximumSize(size_hint.width() + padding, size_hint.height() + height_padding)
            self.layout.addWidget(label)
            self.labels.append(label)

        if self.labels:
            max_label_height = max(label.height() for label in self.labels)
            total_height = len(self.messages) * (max_label_height + self.layout.spacing()) - self.layout.spacing()
            self.resize(screen_geometry.width(), min(total_height, screen_geometry.height()))
        else:
            self.resize(screen_geometry.width(), 0)

    def sanitize_message(self, message):
        """清理消息内容，去除换行符"""
        return message.replace("\n", " ").strip()

    def init_animations(self):
        """初始化弹幕动画"""
        screen_width = QApplication.primaryScreen().size().width()
        self.animation_group = QParallelAnimationGroup(self)
        for i, label in enumerate(self.labels):
            animation = QPropertyAnimation(label, b"geometry")
            animation.setDuration(30000)
            animation.setStartValue(QRect(screen_width + 50, i * (label.height() + self.layout.spacing()), label.width(), label.height()))
            animation.setEndValue(QRect(-label.width() - 50, i * (label.height() + self.layout.spacing()), label.width(), label.height()))
            animation.setEasingCurve(QEasingCurve.Type.Linear)
            self.animations.append(animation)
            self.animation_group.addAnimation(animation)

        self.animation_group.finished.connect(self.check_animation_finished)
        self.animation_group.start()

    def check_animation_finished(self):
        """检查动画是否完成"""
        self.all_finished = True
        QTimer.singleShot(1000, self.close_danmaku)

    def close_danmaku(self):
        """关闭弹幕窗口"""
        self.finished.emit()
        self.close()

class BulletinBoardWorker(QThread):
    update_signal = pyqtSignal(str, bool)

    def __init__(self, db_config, filter_conditions, text_browser):
        super().__init__()
        self.db_config = db_config
        self.filter_conditions = filter_conditions
        self.text_browser = text_browser
        self.theme_config = self.load_theme()
        self.download_queue = Queue()
        self.current_download = None
        self.failed_urls = self.load_failed_urls()  # 从文件加载失败的 URL

    def load_failed_urls(self):
        """从文件加载失败的 URL"""
        failed_urls_file = './data/failed_urls.json'
        if os.path.exists(failed_urls_file):
            try:
                with open(failed_urls_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"加载 failed_urls.json 失败: {e}")
                return {}
        return {}

    def save_failed_urls(self):
        """保存失败的 URL 到文件"""
        failed_urls_file = './data/failed_urls.json'
        os.makedirs(os.path.dirname(failed_urls_file), exist_ok=True)
        try:
            with open(failed_urls_file, 'w', encoding='utf-8') as f:
                json.dump(self.failed_urls, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logging.error(f"保存 failed_urls.json 失败: {e}")

    def run(self):
        last_id = self.read_last_db_id()
        new_messages, has_new_message, error = self.fetch_and_filter_messages(last_id)

        if error:
            formatted_text = error
        elif not new_messages and not has_new_message:
            formatted_text = "数据库中暂无公告信息"
        else:
            self.process_downloads(new_messages)
            formatted_text = self.format_text(new_messages)

        self.update_signal.emit(formatted_text, has_new_message)

    def read_last_db_id(self):
        """读取 dbid.txt 文件中的最后一条消息 ID"""
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
        """从数据库中获取并过滤消息，同时检查是否有新消息"""
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
                        with open('data/dbid.txt', 'w', encoding='utf-8') as f:
                            f.write(str(latest_id))

                    # 如果有数据就返回正常结果
                    return filtered_rows, has_new_message, None

        except pymysql.MySQLError as e:
            # return [], False, f"数据库错误: {str(e)}"
            return [], False, f"您與伺服器的連線已中斷"
        except FileNotFoundError as e:
            return [], False, f"找不到文件: {str(e)}"
        except Exception as e:
            if "Errno 99" in str(e) or "Errno 111" in str(e) or "Errno 10065" in str(e):
                return [], False, f"网络错误: {str(e)}"
            else:
                return [], False, f"意外错误: {str(e)}"

    def filter_data(self, rows):
        """过滤消息数据"""
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
        """获取 QSS 文件路径"""
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
                    self.update_signal.emit(f"QSS file {qss_file} does not exist, using default.", False)
                    return default_qss
        except Exception as e:
            self.update_signal.emit(f"Error reading qss.txt: {e}, using default.", False)
            return default_qss

    def parse_qss_colors(self, qss_file):
        """解析 QSS 文件中的颜色"""
        colors = {}
        try:
            with open(qss_file, 'r', encoding='utf-8') as f:
                qss_content = f.read()
            pattern = re.compile(r'\.(\w+)\s*\{\s*color:\s*#([0-9a-fA-F]{6})\s*;\s*\}')
            matches = pattern.findall(qss_content)
            for match in matches:
                css_class, hex_color = match
                colors[css_class] = f"#{hex_color}"
        except Exception as e:
            self.update_signal.emit(f"Error parsing QSS file: {e}", False)
        return colors

    def load_theme(self):
        """加载主题配置"""
        qss_path = self.get_qss_path()
        return self.parse_qss_colors(qss_path)

    def process_downloads(self, rows):
        """处理新消息中的下载任务"""
        pattern = re.compile(r'&\[(.*?)\]&')
        for row in rows:
            message_content = row['message_content']
            sender_name = row['sender_name']
            created_at = row['timestamp'].strftime("%m-%d %H:%M")
            matches = pattern.findall(message_content)
            for url in matches:
                file_path = os.path.join("./data/download/", os.path.basename(url.split('?')[0]))
                # 如果文件不存在且 URL 未标记为 403，则加入下载队列
                if not os.path.exists(file_path) and (url not in self.failed_urls or "403" not in self.failed_urls.get(url, "")):
                    self.download_queue.put((url, message_content, sender_name, created_at))
        self.start_next_download()

    def start_next_download(self):
        """启动下一个下载任务"""
        if self.current_download is None and not self.download_queue.empty():
            url, message, sender_name, created_at = self.download_queue.get()
            self.current_download = DownloadWorker(url, message, sender_name, created_at)
            self.current_download.download_finished.connect(self.on_download_finished)
            self.current_download.start()

    def on_download_finished(self, file_path, filename, original_message, sender_name, created_at, success, error_msg):
        """下载完成后的处理"""
        self.current_download = None
        url = re.search(r'&\[(.*?)\]&', original_message).group(1)
        if not success:
            self.failed_urls[url] = error_msg  # 记录失败原因
            self.save_failed_urls()  # 保存到文件
            logging.debug(f"记录失败 URL: {url} - {error_msg}")
        # 无论成功或失败，都更新界面
        messages, _ = self.fetch_and_filter_messages(self.read_last_db_id())
        formatted_text = self.format_text(messages)
        self.update_signal.emit(formatted_text, False)
        self.start_next_download()

    def format_text(self, rows):
        """格式化消息文本，保持原有格式"""
        formatted_text = ""
        pattern = re.compile(r'&\[(.*?)\]&')
        for row in rows:
            sender_name = row['sender_name']
            conversationTitle = row['conversationTitle']
            created_at = row['timestamp'].strftime("%m-%d %H:%M")
            message_content = row['message_content']
            css_class = 'admin-sender' if "管理组" in conversationTitle else 'sender'
            color = self.theme_config.get(css_class, '#4cc2ff')

            matches = pattern.findall(message_content)
            if matches:
                for url in matches:
                    file_path = os.path.join("./data/download/", os.path.basename(url.split('?')[0]))
                    file_url = QUrl.fromLocalFile(file_path).toString()
                    if os.path.exists(file_path):
                        ext = os.path.splitext(file_path)[1].lower()
                        new_message = re.sub(r'&\[(.*?)\]&', '', message_content).strip()
                        if ext in ['.png', '.jpg', '.jpeg', '.gif']:
                            message_content = f"{new_message}<br><a href='{file_url}'><img src='{file_path}' style='max-width: 100%; width: auto; height: auto;'></a>"
                        else:
                            icon_path = "icon/file.png"
                            if os.path.exists(icon_path):
                                message_content = f"{new_message}<br><a href='{file_url}'><img src='{icon_path}' width='128'></a>"
                            else:
                                message_content = f"{new_message}<br><a href='{file_url}'>{os.path.basename(file_path)} (图标丢失)</a>"
                    elif url in self.failed_urls and "403" in self.failed_urls[url]:
                        message_content = re.sub(r'&\[(.*?)\]&', "403 Forbidden, 资源超时, 请重新发送", message_content)
                    elif url in self.failed_urls:
                        message_content = re.sub(r'&\[(.*?)\]&', f"下载失败: {self.failed_urls[url]}", message_content)
                    else:
                        message_content = "下载中..."
            formatted_message = f"<b style='color:{color}; font-size:16px;'>{sender_name} ({created_at})</b>{markdown(message_content)}<hr>"
            formatted_text += formatted_message
        return formatted_text

class BulletinBoardModule:
    def __init__(self, main_window, text_browser):
        self.encryption_key = 0x5A
        self.current_danmaku = None
        self.danmaku_queue = Queue()
        self.main_window = main_window
        self.text_browser = text_browser  # 使用 QTextBrowser
        self.text_browser.setOpenLinks(False)  # 禁止自动打开链接
        self.text_browser.anchorClicked.connect(self.handle_anchor_clicked)  # 连接点击信号
        self.timer = QTimer(self.main_window)
        self.timer.setSingleShot(True)  # 设置为单次触发
        self.timer.timeout.connect(self.update_bulletin_board)
        self.timer.start(0)  # 立即触发第一次
        self.last_message_text = ""
        self.sound_effect = QSoundEffect()
        self.sound_effect.setSource(QUrl.fromLocalFile("icon/newmessage.wav"))
        if not self.check_db_config():
            self.timer.stop()

    def handle_anchor_clicked(self, url):
        """处理链接点击事件"""
        if url.isLocalFile():
            file_path = url.toLocalFile()
            if os.path.exists(file_path):
                QDesktopServices.openUrl(url)  # 使用默认程序打开文件
                logging.info(f"打开文件: {file_path}")
            else:
                logging.warning(f"文件不存在: {file_path}")

    def check_db_config(self):
        """检查数据库配置"""
        try:
            with open('data/db_config.json', 'r', encoding='utf-8') as f:
                encrypted_data = f.read()
                config_data = self.decrypt_data(encrypted_data, self.encryption_key)
                db_config = config_data.get("db_config", {})
            required_fields = ["host", "port", "user", "password", "database"]
            for field in required_fields:
                if not db_config.get(field):
                    self.update_text_browser(f"配置错误: {field} 在 db_config.json 中为空", False)
                    return False
            db_config['port'] = int(db_config['port'])
            self.db_config = db_config
            self.filter_conditions = config_data.get("filter_conditions", {})
            self.timer.start(10000)
            return True
        except FileNotFoundError as e:
            self.update_text_browser(f"找不到文件: {str(e)}", False)
            return False
        except json.JSONDecodeError as e:
            self.update_text_browser(f"JSON 解码错误: {str(e)}", False)
            return False
        except ValueError as e:
            self.update_text_browser(f"值错误: {str(e)}", False)
            return False
        except Exception as e:
            self.update_text_browser(f"意外错误: {str(e)}", False)
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
        """更新公告板"""
        try:
            self.worker = BulletinBoardWorker(self.db_config, self.filter_conditions, self.text_browser)
            self.worker.update_signal.connect(self.update_text_browser)
            self.worker.start()
            self.timer.start(10000)  # 启动下一次定时器
        except Exception as e:
            self.update_text_browser(f"意外错误: {str(e)}", False)

    def update_text_browser(self, text, has_new_message):
        """更新 QTextBrowser 内容"""
        try:
            # 如果是错误信息，则直接显示并停止后续操作
            if text.startswith("数据库错误:") or text.startswith("网络错误:") or text.startswith(
                    "找不到文件:") or text.startswith("意外错误:"):
                self.text_browser.setHtml(f"<font color='red'>{text}</font>")
                return

            # 正常情况下只有内容变化才更新
            current_text = self.text_browser.toPlainText()
            if current_text != text:
                self.text_browser.setHtml(text)
                self.last_message_text = text
                if has_new_message:
                    self.play_new_message_sound()
        except Exception as e:
            # 出现异常时回退到上一次有效内容
            logging.error(f"更新 QTextBrowser 时发生错误: {e}")
            self.text_browser.setHtml(self.last_message_text or "<font color='red'>无法加载公告板内容</font>")

    def play_new_message_sound(self):
        """播放新消息提示音并处理弹幕"""
        self.sound_effect.play()
        fetched_messages, _ = self.worker.fetch_and_filter_messages(self.worker.read_last_db_id())
        filtered_messages = self.worker.filter_data(fetched_messages)
        if isinstance(filtered_messages, tuple):
            filtered_messages = filtered_messages[0]
        if filtered_messages:
            last_message = filtered_messages[0]
            formatted_message = f"{last_message['sender_name']}：{last_message['message_content'].replace(' ', ' ').strip()}"
            self.danmaku_queue.put(formatted_message)
            self.display_next_danmaku()

    def display_next_danmaku(self):
        """显示下一个弹幕"""
        if not self.danmaku_queue.empty() and self.current_danmaku is None:
            next_message = self.danmaku_queue.get()
            self.current_danmaku = DanmakuWindow([next_message])
            self.current_danmaku.finished.connect(self.on_danmaku_finished)
            self.current_danmaku.show()

    def on_danmaku_finished(self):
        """弹幕结束后的处理"""
        if self.current_danmaku:
            self.current_danmaku.deleteLater()
            self.current_danmaku = None
        self.display_next_danmaku()

    def stop_timer(self):
        """停止定时器"""
        if self.timer.isActive():
            self.timer.stop()

    def start_timer(self):
        """启动定时器"""
        if not self.timer.isActive():
            self.timer.start(10000)

    def cleanup(self):
        """清理资源"""
        self.stop_timer()
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait()

