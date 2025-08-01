import json
import logging
import os
import base64
import re
import sys
from queue import Queue
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QUrl, QEasingCurve, QAbstractAnimation, QParallelAnimationGroup
from PyQt6.QtMultimedia import QSoundEffect
from datetime import datetime, timedelta
from markdown import markdown
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QApplication, QTextBrowser
from PyQt6.QtCore import QTimer, Qt, QPropertyAnimation, QRect
from PyQt6.QtGui import QFont, QFontMetrics, QDesktopServices
import uuid
import threading
import time
import urllib3

# 禁用不安全请求警告（仅用于测试）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class MessagePollWorker(QThread):
    """消息轮询工作线程"""
    message_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, server_url, agent_id, filter_conditions):
        super().__init__()
        self.server_url = server_url
        self.agent_id = agent_id
        self.filter_conditions = filter_conditions
        self.running = True
        self.session = None

    def setup_session(self):
        """设置请求会话"""
        self.session = requests.Session()

        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Education-Clock-Client/1.0'
        })

    def run(self):
        """运行消息轮询"""
        try:
            # 设置会话
            self.setup_session()

            while self.running:
                try:
                    # 构建URL参数
                    params = {
                        'agent_id': self.agent_id
                    }

                    if 'sender_names' in self.filter_conditions and self.filter_conditions['sender_names']:
                        params['sender_names'] = ','.join(self.filter_conditions['sender_names'])

                    if 'conversation_titles' in self.filter_conditions and self.filter_conditions[
                        'conversation_titles']:
                        params['conversation_titles'] = ','.join(self.filter_conditions['conversation_titles'])

                    url = f"{self.server_url}/api/messages"
                    logging.info(f"发送轮询请求到: {url}")
                    logging.debug(f"请求参数: {params}")

                    # 发起请求
                    response = self.session.get(
                        url,
                        params=params,
                        timeout=(10, 30),  # 连接超时10秒，读取超时30秒
                    )

                    logging.info(f"收到响应，状态码: {response.status_code}")
                    if response.status_code == 200:
                        data = response.json()
                        logging.info(f"响应数据: {data}")
                        self.message_received.emit(data)
                    else:
                        logging.error(f"请求失败，状态码: {response.status_code}, 响应内容: {response.text}")
                        self.error_occurred.emit(f"请求失败，状态码: {response.status_code}")

                except Exception as e:
                    logging.error(f"轮询错误: {str(e)}", exc_info=True)
                    self.error_occurred.emit(f"轮询错误: {str(e)}")

                # 等待10秒后再次轮询
                logging.info("等待10秒后进行下一次轮询")
                for _ in range(100):  # 10秒 = 100 * 0.1秒
                    if not self.running:
                        break
                    time.sleep(0.1)

        except Exception as e:
            logging.error(f"连接错误: {str(e)}", exc_info=True)
            self.error_occurred.emit(f"连接错误: {str(e)}")
        finally:
            if self.session:
                self.session.close()

    def stop(self):
        """停止工作线程"""
        self.running = False


class DownloadWorker(QThread):
    """文件下载工作线程"""
    download_finished = pyqtSignal(str, str, str, str, str, bool,
                                   str)  # 文件路径, 文件名, 原始消息, sender_name, created_at, 是否成功, 错误信息

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
            self.download_finished.emit(file_path, self.filename, self.message, self.sender_name, self.created_at, True,
                                        "")
            return

        try:
            # 配置请求会话，增加重试机制
            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)

            response = session.get(self.url, stream=True, timeout=30)
            response.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info(f"文件下载成功: {file_path}")
            self.download_finished.emit(file_path, self.filename, self.message, self.sender_name, self.created_at, True,
                                        "")
        except requests.exceptions.HTTPError as e:
            error_msg = str(e)
            if e.response.status_code == 403:
                error_msg = "403 请求已达上限"
            logging.error(f"下载文件失败 {self.url}: {error_msg}")
            self.download_finished.emit(file_path, self.filename, self.message, self.sender_name, self.created_at,
                                        False, error_msg)
        except Exception as e:
            error_msg = str(e)
            logging.error(f"下载文件失败 {self.url}: {error_msg}")
            self.download_finished.emit(file_path, self.filename, self.message, self.sender_name, self.created_at,
                                        False, error_msg)


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
        """检查动画是否完成"""
        self.all_finished = True
        QTimer.singleShot(1000, self.close_danmaku)

    def close_danmaku(self):
        """关闭弹幕窗口"""
        self.finished.emit()
        self.close()


class BulletinBoardModule:
    def __init__(self, main_window, text_browser):
        try:
            self.current_danmaku = None
            self.danmaku_queue = Queue()
            self.main_window = main_window

            # 确保 text_browser 不为 None
            if text_browser is None:
                logging.error("text_browser 为 None")
                raise ValueError("text_browser 不能为 None")

            self.text_browser = text_browser
            self.text_browser.setOpenLinks(False)  # 禁止自动打开链接
            self.text_browser.anchorClicked.connect(self.handle_anchor_clicked)  # 连接点击信号

            self.last_message_text = ""
            self.sound_effect = QSoundEffect()
            try:
                self.sound_effect.setSource(QUrl.fromLocalFile("icon/newmessage.wav"))
            except Exception as e:
                logging.warning(f"无法加载提示音: {e}")

            # 消息轮询相关变量
            self.poll_thread = None
            self.poll_worker = None
            self.server_url = "http://localhost:10240"
            self.agent_id = None
            self.filter_conditions = {}
            self.connection_retry_count = 0
            self.max_retry_count = 5  # 最大重试次数

            # 加载配置并启动轮询
            if not self.load_config():
                logging.error("无法加载配置文件")

        except Exception as e:
            logging.error(f"初始化 BulletinBoardModule 时发生错误: {e}", exc_info=True)

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
                    logging.warning(f"QSS file {qss_file} does not exist, using default.")
                    return default_qss
        except Exception as e:
            logging.error(f"Error reading qss.txt: {e}, using default.")
            return default_qss

    def parse_qss_colors(self, qss_file):
        """解析 QSS 文件中的颜色"""
        colors = {}
        try:
            if not os.path.exists(qss_file):
                logging.warning(f"QSS 文件不存在: {qss_file}")
                return colors

            with open(qss_file, 'r', encoding='utf-8') as f:
                qss_content = f.read()
            pattern = re.compile(r'\.(\w+)\s*\{\s*color:\s*#([0-9a-fA-F]{6})\s*;\s*\}')
            matches = pattern.findall(qss_content)
            for match in matches:
                css_class, hex_color = match
                colors[css_class] = f"#{hex_color}"
        except Exception as e:
            logging.error(f"Error parsing QSS file: {e}")
        return colors

    def load_theme(self):
        """加载主题配置"""
        try:
            qss_path = self.get_qss_path()
            return self.parse_qss_colors(qss_path)
        except Exception as e:
            logging.error(f"加载主题配置时出错: {e}")
            # 返回默认颜色配置
            return {
                'sender': '#4cc2ff',
                'admin-sender': '#ff6b6b'
            }

    def format_messages(self, rows):
        """格式化消息"""
        try:
            logging.info(f"开始格式化 {len(rows)} 条消息")
            formatted_text = ""
            pattern = re.compile(r'&\[(.*?)\]&')

            # 加载主题配置
            try:
                theme_config = self.load_theme()
            except Exception as e:
                logging.error(f"加载主题配置失败: {e}")
                theme_config = {'sender': '#4cc2ff', 'admin-sender': '#ff6b6b'}

            if not rows:
                return "<p style='text-align: center; color: gray;'>暂无符合条件的消息</p>"

            for i, row in enumerate(rows):
                try:
                    logging.debug(f"处理第 {i + 1} 条消息: {row}")

                    # 安全地获取字段值
                    sender_name = str(row.get('sender_name', '未知发送者')) if row.get(
                        'sender_name') is not None else '未知发送者'
                    conversationTitle = str(row.get('conversationTitle', '未知群聊')) if row.get(
                        'conversationTitle') is not None else '未知群聊'

                    # 处理时间格式
                    created_at = "未知时间"
                    timestamp_value = row.get('timestamp')
                    if timestamp_value:
                        try:
                            # 处理不同格式的时间戳
                            if isinstance(timestamp_value, str):
                                # 尝试解析 RFC 格式的时间戳
                                if timestamp_value.endswith(' GMT'):
                                    dt = datetime.strptime(timestamp_value, "%a, %d %b %Y %H:%M:%S GMT")
                                else:
                                    # 尝试解析常见的日期时间格式
                                    dt = datetime.strptime(timestamp_value, "%Y-%m-%d %H:%M:%S")
                            else:
                                dt = timestamp_value
                            created_at = dt.strftime("%m-%d %H:%M")
                        except ValueError as e:
                            logging.warning(f"时间格式解析错误: {e}")
                            created_at = str(timestamp_value)

                    # 安全地获取消息内容
                    message_content = str(row.get('message_content', '')) if row.get(
                        'message_content') is not None else ''

                    css_class = 'admin-sender' if "管理组" in conversationTitle else 'sender'
                    color = theme_config.get(css_class, '#4cc2ff')

                    # 处理文件链接
                    matches = pattern.findall(message_content)
                    processed_message_content = message_content
                    if matches:
                        for url in matches:
                            try:
                                file_path = os.path.join("./data/download/", os.path.basename(url.split('?')[0]))
                                file_url = QUrl.fromLocalFile(file_path).toString()
                                if os.path.exists(file_path):
                                    ext = os.path.splitext(file_path)[1].lower()
                                    new_message = re.sub(r'&\[(.*?)\]&', '', processed_message_content).strip()
                                    if ext in ['.png', '.jpg', '.jpeg', '.gif']:
                                        processed_message_content = f"{new_message}<br><a href='{file_url}'><img src='{file_path}' style='max-width: 100%; width: auto; height: auto;'></a>"
                                    else:
                                        icon_path = "icon/file.png"
                                        if os.path.exists(icon_path):
                                            processed_message_content = f"{new_message}<br><a href='{file_url}'><img src='{icon_path}' width='128'></a>"
                                        else:
                                            processed_message_content = f"{new_message}<br><a href='{file_url}'>{os.path.basename(file_path)} (图标丢失)</a>"
                                else:
                                    processed_message_content = "下载中..."
                            except Exception as e:
                                logging.error(f"处理文件链接时出错: {e}")
                                processed_message_content = "[文件链接处理错误]"

                    # 构建格式化的消息
                    try:
                        formatted_message = f"<b style='color:{color}; font-size:16px;'>{sender_name} ({created_at})</b>{markdown(processed_message_content)}<hr>"
                        formatted_text += formatted_message
                    except Exception as e:
                        logging.error(f"构建格式化消息时出错: {e}")
                        formatted_text += f"<p style='color: red;'>消息格式化错误: {str(e)}</p><hr>"

                except Exception as e:
                    logging.error(f"处理第 {i + 1} 条消息时出错: {e}", exc_info=True)
                    formatted_text += f"<p style='color: red;'>消息处理错误: {str(e)}</p><hr>"

            logging.info(f"消息格式化完成，总长度: {len(formatted_text)}")
            return formatted_text

        except Exception as e:
            logging.error(f"格式化消息时发生严重错误: {e}", exc_info=True)
            return "<p style='color: red; text-align: center;'>消息格式化错误</p>"

    def handle_anchor_clicked(self, url):
        """处理链接点击事件"""
        try:
            if url.isLocalFile():
                file_path = url.toLocalFile()
                if os.path.exists(file_path):
                    QDesktopServices.openUrl(url)  # 使用默认程序打开文件
                    logging.info(f"打开文件: {file_path}")
                else:
                    logging.warning(f"文件不存在: {file_path}")
        except Exception as e:
            logging.error(f"处理链接点击事件时出错: {e}")

    def play_new_message_sound(self):
        """播放新消息提示音并处理弹幕"""
        try:
            self.sound_effect.play()
            # 从文本浏览器中提取最后一条消息用于弹幕显示
            # 这里可以添加弹幕逻辑
        except Exception as e:
            logging.error(f"播放新消息提示音时出错: {e}")

    def cleanup(self):
        """清理资源"""
        try:
            # 停止轮询线程
            if self.poll_worker:
                self.poll_worker.stop()
            if self.poll_thread and self.poll_thread.isRunning():
                self.poll_thread.quit()
                self.poll_thread.wait()
        except Exception as e:
            logging.error(f"清理资源时出错: {e}")

    def load_config(self):
        """加载配置文件"""
        try:
            with open('data/db_config.json', 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # 获取agent_id和server_url
            self.agent_id = config_data.get("agent_id")
            self.server_url = config_data.get("server_url", "http://localhost:10240")  # 修复这里
            self.filter_conditions = config_data.get("filter_conditions", {})

            # 启动消息轮询
            if self.agent_id:
                self.start_polling()
                return True
            else:
                logging.warning("未找到agent_id，无法启动消息轮询")
                return False
        except FileNotFoundError as e:
            logging.error(f"找不到配置文件: {str(e)}")
            return False
        except json.JSONDecodeError as e:
            logging.error(f"JSON 解码错误: {str(e)}")
            return False
        except Exception as e:
            logging.error(f"加载配置时发生意外错误: {str(e)}", exc_info=True)
            return False

    def start_polling(self):
        """启动消息轮询"""
        if not self.agent_id:
            logging.warning("缺少agent_id，无法启动消息轮询")
            return

        # 检查是否超过最大重试次数
        if self.connection_retry_count >= self.max_retry_count:
            logging.error(f"已达到最大重试次数 ({self.max_retry_count})，停止尝试连接")
            return

        logging.info(f"启动消息轮询 (尝试次数: {self.connection_retry_count + 1}/{self.max_retry_count})")

        # 启动轮询线程
        self.poll_thread = QThread()
        self.poll_worker = MessagePollWorker(
            self.server_url,
            self.agent_id,
            self.filter_conditions
        )
        self.poll_worker.moveToThread(self.poll_thread)

        # 连接信号和槽
        self.poll_thread.started.connect(self.poll_worker.run)
        self.poll_worker.message_received.connect(self.handle_message)
        self.poll_worker.error_occurred.connect(self.on_poll_error)  # 这里需要定义方法

        # 启动线程
        self.poll_thread.start()

    def on_poll_error(self, error_msg):
        """轮询错误处理"""
        self.connection_retry_count += 1
        logging.error(f"消息轮询错误: {error_msg}")

        # 如果达到最大重试次数，停止轮询
        if self.connection_retry_count >= self.max_retry_count:
            logging.error(f"已达到最大重试次数 ({self.max_retry_count})，停止消息轮询")

    def handle_message(self, message):
        """处理接收到的消息"""
        try:
            logging.info(f"收到服务器响应: {message}")
            message_type = message.get("type", "unknown")

            if message_type == "messages":
                messages = message.get("data", [])
                logging.info(f"收到 {len(messages)} 条消息")

                if messages is not None and len(messages) > 0:
                    # 检查是否有新消息
                    has_new_message = self.check_for_new_messages(messages)

                    formatted_text = self.format_messages(messages)
                    logging.debug(f"格式化后的文本长度: {len(formatted_text) if formatted_text else 0}")
                    self.update_text_browser(formatted_text, has_new_message)
                else:
                    # 显示"暂无消息"提示
                    self.update_text_browser("<p style='text-align: center; color: gray;'>暂无符合条件的消息</p>",
                                             False)
            else:
                logging.warning(f"收到未知类型的消息: {message}")
        except Exception as e:
            logging.error(f"处理消息时发生错误: {e}", exc_info=True)
            self.update_text_browser("<p style='color: red; text-align: center;'>消息处理错误</p>", False)

    def check_for_new_messages(self, messages):
        """检查是否有新消息"""
        try:
            if not messages:
                return False

            # 获取最新消息的ID
            latest_message = messages[0]  # 消息按时间倒序排列
            latest_id = latest_message.get('id', 0)

            # 读取 dbid.txt 中保存的最后ID
            last_id = self.read_last_message_id()

            # 比较ID
            if latest_id > last_id:
                # 保存新的ID
                self.save_last_message_id(latest_id)

                # 播放提示音并显示弹幕
                self.play_new_message_sound(latest_message)
                return True

            return False
        except Exception as e:
            logging.error(f"检查新消息时出错: {e}")
            return False

    def read_last_message_id(self):
        """读取 dbid.txt 文件中的最后消息 ID"""
        try:
            last_id = 0
            dbid_file = 'data/dbid.txt'
            if os.path.exists(dbid_file):
                with open(dbid_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        last_id = int(content)
            logging.debug(f"读取到最后消息ID: {last_id}")
            return last_id
        except ValueError as e:
            logging.error(f"dbid.txt 中的值不是有效数字: {e}")
            return 0
        except Exception as e:
            logging.error(f"读取 dbid.txt 时出错: {e}")
            return 0

    def save_last_message_id(self, message_id):
        """保存最后消息 ID 到 dbid.txt"""
        try:
            dbid_file = 'data/dbid.txt'
            os.makedirs(os.path.dirname(dbid_file), exist_ok=True)
            with open(dbid_file, 'w', encoding='utf-8') as f:
                f.write(str(message_id))
            logging.debug(f"保存消息ID到文件: {message_id}")
        except Exception as e:
            logging.error(f"保存消息ID到 dbid.txt 时出错: {e}")

    def play_new_message_sound(self, message=None):
        """播放新消息提示音并处理弹幕"""
        try:
            # 播放提示音
            if hasattr(self, 'sound_effect') and self.sound_effect is not None:
                self.sound_effect.play()
                logging.info("播放新消息提示音")

            # 显示弹幕
            if message:
                try:
                    sender_name = message.get('sender_name', '未知发送者')
                    message_content = message.get('message_content', '')
                    # 清理消息内容，移除文件链接标记
                    cleaned_content = re.sub(r'&\[(.*?)\]&', '[文件]', message_content).strip()
                    formatted_message = f"{sender_name}：{cleaned_content}"

                    # 添加到弹幕队列
                    if hasattr(self, 'danmaku_queue'):
                        self.danmaku_queue.put(formatted_message)
                        self.display_next_danmaku()
                except Exception as e:
                    logging.error(f"处理弹幕消息时出错: {e}")

        except Exception as e:
            logging.error(f"播放新消息提示音时出错: {e}")

    def display_next_danmaku(self):
        """显示下一个弹幕"""
        try:
            if (hasattr(self, 'danmaku_queue') and
                    not self.danmaku_queue.empty() and
                    hasattr(self, 'current_danmaku') and
                    self.current_danmaku is None):
                next_message = self.danmaku_queue.get()
                self.current_danmaku = DanmakuWindow([next_message])
                self.current_danmaku.finished.connect(self.on_danmaku_finished)
                self.current_danmaku.show()
                logging.info(f"显示弹幕: {next_message}")
        except Exception as e:
            logging.error(f"显示弹幕时出错: {e}")

    def on_danmaku_finished(self):
        """弹幕结束后的处理"""
        try:
            if hasattr(self, 'current_danmaku') and self.current_danmaku:
                self.current_danmaku.deleteLater()
                self.current_danmaku = None
            self.display_next_danmaku()
        except Exception as e:
            logging.error(f"弹幕结束处理时出错: {e}")

    def format_messages(self, rows):
        """格式化消息"""
        try:
            logging.info(f"开始格式化 {len(rows)} 条消息")
            formatted_text = ""
            pattern = re.compile(r'&\[(.*?)\]&')

            # 加载主题配置
            try:
                theme_config = self.load_theme()
            except Exception as e:
                logging.error(f"加载主题配置失败: {e}")
                theme_config = {'sender': '#4cc2ff', 'admin-sender': '#ff6b6b'}

            if not rows:
                return "<p style='text-align: center; color: gray;'>暂无符合条件的消息</p>"

            for i, row in enumerate(rows):
                try:
                    logging.debug(f"处理第 {i + 1} 条消息: {row}")

                    # 安全地获取字段值
                    sender_name = str(row.get('sender_name', '未知发送者')) if row.get(
                        'sender_name') is not None else '未知发送者'
                    conversationTitle = str(row.get('conversationTitle', '未知群聊')) if row.get(
                        'conversationTitle') is not None else '未知群聊'

                    # 处理时间格式
                    created_at = "未知时间"
                    timestamp_value = row.get('timestamp')
                    if timestamp_value:
                        try:
                            # 处理不同格式的时间戳
                            if isinstance(timestamp_value, str):
                                # 尝试解析 RFC 格式的时间戳
                                if timestamp_value.endswith(' GMT'):
                                    dt = datetime.strptime(timestamp_value, "%a, %d %b %Y %H:%M:%S GMT")
                                else:
                                    # 尝试解析常见的日期时间格式
                                    dt = datetime.strptime(timestamp_value, "%Y-%m-%d %H:%M:%S")
                            else:
                                dt = timestamp_value
                            created_at = dt.strftime("%m-%d %H:%M")
                        except ValueError as e:
                            logging.warning(f"时间格式解析错误: {e}")
                            created_at = str(timestamp_value)

                    # 安全地获取消息内容
                    message_content = str(row.get('message_content', '')) if row.get(
                        'message_content') is not None else ''

                    css_class = 'admin-sender' if "管理组" in conversationTitle else 'sender'
                    color = theme_config.get(css_class, '#4cc2ff')

                    # 处理文件链接
                    matches = pattern.findall(message_content)
                    processed_message_content = message_content
                    if matches:
                        for url in matches:
                            try:
                                file_path = os.path.join("./data/download/", os.path.basename(url.split('?')[0]))
                                file_url = QUrl.fromLocalFile(file_path).toString()
                                if os.path.exists(file_path):
                                    ext = os.path.splitext(file_path)[1].lower()
                                    new_message = re.sub(r'&\[(.*?)\]&', '', processed_message_content).strip()
                                    if ext in ['.png', '.jpg', '.jpeg', '.gif']:
                                        processed_message_content = f"{new_message}<br><a href='{file_url}'><img src='{file_path}' style='max-width: 100%; width: auto; height: auto;'></a>"
                                    else:
                                        icon_path = "icon/file.png"
                                        if os.path.exists(icon_path):
                                            processed_message_content = f"{new_message}<br><a href='{file_url}'><img src='{icon_path}' width='128'></a>"
                                        else:
                                            processed_message_content = f"{new_message}<br><a href='{file_url}'>{os.path.basename(file_path)} (图标丢失)</a>"
                                else:
                                    processed_message_content = "下载中..."
                            except Exception as e:
                                logging.error(f"处理文件链接时出错: {e}")
                                processed_message_content = "[文件链接处理错误]"

                    # 构建格式化的消息
                    try:
                        formatted_message = f"<b style='color:{color}; font-size:16px;'>{sender_name} ({created_at})</b>{markdown(processed_message_content)}<hr>"
                        formatted_text += formatted_message
                    except Exception as e:
                        logging.error(f"构建格式化消息时出错: {e}")
                        formatted_text += f"<p style='color: red;'>消息格式化错误: {str(e)}</p><hr>"

                except Exception as e:
                    logging.error(f"处理第 {i + 1} 条消息时出错: {e}", exc_info=True)
                    formatted_text += f"<p style='color: red;'>消息处理错误: {str(e)}</p><hr>"

            logging.info(f"消息格式化完成，总长度: {len(formatted_text)}")
            return formatted_text

        except Exception as e:
            logging.error(f"格式化消息时发生严重错误: {e}", exc_info=True)
            return "<p style='color: red; text-align: center;'>消息格式化错误</p>"

    def update_text_browser(self, text, has_new_message):
        """更新 QTextBrowser 内容"""
        try:
            logging.info(f"更新文本浏览器，文本长度: {len(text) if text else 0}")

            # 确保文本不为 None
            if text is None:
                text = "<p style='text-align: center; color: gray;'>暂无消息</p>"

            # 检查文本浏览器是否仍然有效
            if hasattr(self, 'text_browser') and self.text_browser is not None:
                # 正常情况下更新内容
                self.text_browser.setHtml(text)
                self.last_message_text = text
                if has_new_message:
                    # 新消息已经在 check_for_new_messages 中处理了
                    pass
            else:
                logging.warning("文本浏览器对象无效")

        except Exception as e:
            # 出现异常时回退到上一次有效内容
            logging.error(f"更新 QTextBrowser 时发生错误: {e}", exc_info=True)
            fallback_text = self.last_message_text or "<font color='red'>无法加载公告板内容</font>"
            try:
                if hasattr(self, 'text_browser') and self.text_browser is not None:
                    self.text_browser.setHtml(fallback_text)
            except:
                logging.error("无法设置回退文本")

    def cleanup(self):
        """清理资源"""
        try:
            # 停止轮询线程
            if self.poll_worker:
                self.poll_worker.stop()
            if self.poll_thread and self.poll_thread.isRunning():
                self.poll_thread.quit()
                self.poll_thread.wait()
        except Exception as e:
            logging.error(f"清理资源时出错: {e}")


