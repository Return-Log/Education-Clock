import sys
import os
import json
import time
from datetime import datetime
from distutils.command.config import config

import requests
import numpy as np
import pyaudio
import cv2
import logging


from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import QApplication, QLabel
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt, QUrl
from PyQt6.QtGui import QFont

# 全局变量
CONFIG_FILE = "data/maintain_order_info.json"
LAUNCH_FILE = "data/launch.json"
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
SMMS_TOKEN_URL = "https://sm.ms/api/v2/token"


class Config:
    def __init__(self):
        """初始化配置文件"""
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.webhook_url = data["webhook_url"]
                self.smms_username = data["smms_username"]
                self.smms_password = data["smms_password"]
                self.threshold_db = data["threshold_db"]
                self.mic_device_index = data.get("mic_device_index", 0)
                self.camera_device_index = data.get("camera_device_index", 0)
                self.text_at = data["text_at"]
                self.schedule = data["schedule"]
                self.smms_api_key = self.get_smms_token()
        except FileNotFoundError:
            logging.error(f"配置文件 {CONFIG_FILE} 未找到")
            sys.exit(1)
        except json.JSONDecodeError:
            logging.error(f"配置文件 {CONFIG_FILE} 格式错误")
            sys.exit(1)
        except Exception as e:
            logging.error(f"加载配置文件时出错: {str(e)}")
            sys.exit(1)

    def get_smms_token(self):
        """获取 SM.MS API Token"""
        payload = {"username": self.smms_username, "password": self.smms_password}
        try:
            response = requests.post(SMMS_TOKEN_URL, data=payload, timeout=10)
            response.raise_for_status()
            response_data = response.json()
            if response_data.get("success"):
                token = response_data["data"]["token"]
                logging.info("成功获取 SM.MS API Token")
                return token
            else:
                logging.error(f"获取 Token 失败: {response_data.get('message')}")
                return None
        except requests.RequestException as e:
            logging.error(f"获取 SM.MS Token 网络请求出错: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"获取 SM.MS Token 时出错: {str(e)}")
            return None


class DecibelThread(QThread):
    decibel_exceeded = pyqtSignal(float)

    def __init__(self, config):
        """初始化分贝检测线程"""
        super().__init__()
        self.running = True
        self.config = config
        self.silent_until = 0

    def run(self):
        """运行分贝检测线程"""
        if not self.config.smms_api_key:
            logging.error("未获取到 SM.MS API Token，将关闭 order 并重启程序")
            self.update_launch_json()
            self.restart_program()
            return

        p = None
        stream = None
        try:
            p = pyaudio.PyAudio()
            stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True,
                            frames_per_buffer=CHUNK, input_device_index=self.config.mic_device_index)
            logging.info("音频流初始化成功，开始检测")

            while self.running:
                current_time = time.time()
                if current_time < self.silent_until:
                    remaining = self.silent_until - current_time
                    logging.debug(f"静默期剩余 {remaining:.1f} 秒")
                    time.sleep(min(remaining, 0.1))
                    continue

                trimmed_mean_db = self.detect_noise(stream)
                if trimmed_mean_db is None:
                    time.sleep(1)
                    continue

                if trimmed_mean_db > self.config.threshold_db:
                    logging.info(f"分贝超标: {trimmed_mean_db:.1f} > {self.config.threshold_db}, 触发警告")
                    self.decibel_exceeded.emit(trimmed_mean_db)
                else:
                    logging.info(f"分贝未超标: {trimmed_mean_db:.1f} <= {self.config.threshold_db}")
                time.sleep(0.1)

        except Exception as e:
            logging.error(f"分贝检测线程异常: {str(e)}")
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            if p:
                p.terminate()
            logging.info("音频流已关闭")

    def detect_noise(self, stream):
        """检测15秒内平均分贝值"""
        try:
            now = datetime.now()
            weekday = now.strftime("%A")
            current_time = now.strftime("%H:%M")
            if weekday not in self.config.schedule:
                return None

            for time_range in self.config.schedule[weekday]:
                start, end = time_range.split("-")
                if start <= current_time <= end:
                    logging.info(f"进入 {start}-{end} 时间段，检测15秒噪音")
                    db_values = []
                    for _ in range(int(RATE / CHUNK * 15)):
                        data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
                        rms = np.sqrt(np.mean(data ** 2)) if np.any(data) else 0
                        db = 20 * np.log10(rms) if rms > 0 else -float("inf")
                        db_values.append(db)

                    logging.info(
                        f"15秒原始分贝值 - 最小: {min(db_values):.1f}, 最大: {max(db_values):.1f}, 平均: {np.mean(db_values):.1f}")
                    db_array = np.array(db_values)
                    trimmed_db = np.percentile(db_array, [5, 95])
                    trimmed_mean_db = np.mean(db_array[(db_array > trimmed_db[0]) & (db_array < trimmed_db[1])])
                    logging.info(
                        f"去极值后 - 范围: {trimmed_db[0]:.1f} 到 {trimmed_db[1]:.1f}, 平均: {trimmed_mean_db:.1f}")
                    return trimmed_mean_db
            return None
        except Exception as e:
            logging.error(f"噪音检测出错: {str(e)}")
            return None

    def set_silent_period(self, duration):
        """设置静默期，单位为秒"""
        new_silent_until = time.time() + duration
        if new_silent_until > self.silent_until:
            self.silent_until = new_silent_until
            logging.info(f"进入静默期 {duration} 秒，直到 {datetime.fromtimestamp(self.silent_until).strftime('%H:%M:%S')}")

    def stop(self):
        """停止分贝检测线程"""
        self.running = False

    def update_launch_json(self):
        """更新 launch.json 文件，将 order 改为关闭"""
        try:
            if not os.path.exists(LAUNCH_FILE):
                logging.warning(f"{LAUNCH_FILE} 不存在，创建默认文件")
                data = {"shutdown": "开启", "news": "关闭", "order": "关闭"}
            else:
                with open(LAUNCH_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["order"] = "关闭"

            with open(LAUNCH_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            logging.info(f"已更新 {LAUNCH_FILE}，order 设置为 '关闭'")
        except Exception as e:
            logging.error(f"更新 {LAUNCH_FILE} 失败: {str(e)}")

    def restart_program(self):
        """重启程序"""
        logging.info("正在重启程序...")
        python = sys.executable
        os.execl(python, python, *sys.argv)


class UploadThread(QThread):
    upload_complete = pyqtSignal(str)

    def __init__(self, image_path, api_key):
        """初始化上传线程"""
        super().__init__()
        self.image_path = image_path
        self.api_key = api_key

    def run(self):
        """执行图片上传"""
        try:
            url = "https://sm.ms/api/v2/upload"
            headers = {"Authorization": self.api_key}
            with open(self.image_path, "rb") as f:
                files = {"smfile": f}
                response = requests.post(url, headers=headers, files=files, timeout=10)
                response.raise_for_status()
                data = response.json()
                logging.info(f"SM.MS 上传响应: {json.dumps(data, indent=2)}")

                if data.get("success"):
                    image_url = data["data"]["url"]
                    logging.info(f"上传成功，图片 URL: {image_url}")
                    self.upload_complete.emit(image_url)
                elif data.get("code") == "image_repeated":
                    image_url = data.get("images") or data.get("message", "").split("exists at: ")[-1].strip()
                    logging.info(f"图片重复，使用已有 URL: {image_url}")
                    self.upload_complete.emit(image_url)
                else:
                    logging.error(f"上传失败: {data.get('message')}")
                    self.upload_complete.emit("")
        except requests.RequestException as e:
            logging.error(f"图片上传网络请求出错: {str(e)}")
            self.upload_complete.emit("")
        except Exception as e:
            logging.error(f"图片上传出错: {str(e)}")
            self.upload_complete.emit("")


class DingTalkThread(QThread):
    message_sent = pyqtSignal()

    def __init__(self, image_url, webhook_url):
        """初始化钉钉消息线程"""
        super().__init__()
        self.image_url = image_url
        self.webhook_url = webhook_url
        self.config = Config()
        self.text_at = self.config.text_at

    def run(self):
        """发送钉钉消息"""
        try:
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "监控报警",
                    "text": f"#### 噪音超标警告 {self.text_at}\n> 检测到噪音超标，已拍摄照片\n> ![noise]({self.image_url})\n> ###### {datetime.now().strftime('%H:%M:%S')} 发布\n"
                },
                "at": {"isAtAll": False, "atMobiles": self.text_at}
            }
            headers = {"Content-Type": "application/json"}
            response = requests.post(self.webhook_url, json=data, headers=headers, timeout=10)
            response.raise_for_status()
            logging.info(f"钉钉消息发送响应: {response.text}")
            self.message_sent.emit()
        except requests.RequestException as e:
            logging.error(f"发送钉钉消息网络请求出错: {str(e)}")
        except Exception as e:
            logging.error(f"发送钉钉消息出错: {str(e)}")


class WarningPopup(QLabel):
    def __init__(self, text):
        """初始化警告弹窗"""
        super().__init__(text)
        self.setStyleSheet("""
            QLabel {
                color: white;
                background-color: black;
                font-size: 18pt !important;
                font: 微软雅黑 !important;
            }
        """)
        self.setFont(QFont("微软雅黑", 18))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.move(0, 0)
        self.setFixedSize(380, 100)

class SecondDetectionThread(QThread):
    detection_complete = pyqtSignal(float)  # 信号传递检测结果

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.running = True

    def run(self):
        """执行第二次15秒检测"""
        p = None
        stream = None
        try:
            p = pyaudio.PyAudio()
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
                input_device_index=self.config.mic_device_index
            )
            db_values = []
            for _ in range(int(RATE / CHUNK * 15)):
                if not self.running:
                    break
                data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
                rms = np.sqrt(np.mean(data ** 2)) if np.any(data) else 0
                db = 20 * np.log10(rms) if rms > 0 else -float("inf")
                db_values.append(db)

            if db_values:
                logging.info(
                    f"第二次15秒原始分贝值 - 最小: {min(db_values):.1f}, 最大: {max(db_values):.1f}, 平均: {np.mean(db_values):.1f}"
                )
                db_array = np.array(db_values)
                trimmed_db = np.percentile(db_array, [5, 95])
                trimmed_mean_db = np.mean(db_array[(db_array > trimmed_db[0]) & (db_array < trimmed_db[1])])
                logging.info(
                    f"去极值后 - 范围: {trimmed_db[0]:.1f} 到 {trimmed_db[1]:.1f}, 平均: {trimmed_mean_db:.1f}"
                )
                self.detection_complete.emit(trimmed_mean_db)
            else:
                logging.warning("第二次检测被中断，返回 None")
                self.detection_complete.emit(None)
        except Exception as e:
            logging.error(f"第二次检测出错: {str(e)}")
            self.detection_complete.emit(None)
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            if p:
                p.terminate()

    def stop(self):
        """停止检测线程"""
        self.running = False


class PhotoUploadThread(QThread):
    """拍照和上传的专用线程"""
    upload_complete = pyqtSignal(str)  # 信号传递上传完成的URL

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        """执行拍照和上传"""
        cap = None
        try:
            cap = cv2.VideoCapture(self.config.camera_device_index)
            if not cap.isOpened():
                logging.error(f"无法打开摄像头 {self.config.camera_device_index}")
                self.upload_complete.emit("")
                return

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

            logging.info("摄像头预热中...")
            time.sleep(2)  # 等待2秒让摄像头稳定

            max_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            max_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            if max_width == 0 or max_height == 0:
                logging.warning("无法获取有效分辨率，使用默认值")
                max_width, max_height = 640, 480
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, max_width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, max_height)
            else:
                logging.info(f"使用摄像头分辨率: {max_width}x{max_height}")

            ret, frame = cap.read()
            if not ret:
                logging.error("无法读取摄像头图像")
                self.upload_complete.emit("")
                return

            image_path = "./data/noise_photo.png"
            compression_params = [cv2.IMWRITE_PNG_COMPRESSION, 9]
            cv2.imwrite(image_path, frame, compression_params)
            file_size = os.path.getsize(image_path) / 1024
            logging.info(f"照片保存至 {image_path}，分辨率: {max_width}x{max_height}，大小: {file_size:.2f} KB")

            # 上传照片
            url = self.upload_image(image_path)
            self.upload_complete.emit(url)

        except Exception as e:
            logging.error(f"拍照或上传出错: {str(e)}")
            self.upload_complete.emit("")
        finally:
            if cap:
                cap.release()

    def upload_image(self, image_path):
        """上传图片到SM.MS"""
        try:
            url = "https://sm.ms/api/v2/upload"
            headers = {"Authorization": self.config.smms_api_key}
            with open(image_path, "rb") as f:
                files = {"smfile": f}
                response = requests.post(url, headers=headers, files=files, timeout=10)
                response.raise_for_status()
                data = response.json()
                logging.info(f"SM.MS 上传响应: {json.dumps(data, indent=2)}")

                if data.get("success"):
                    image_url = data["data"]["url"]
                    logging.info(f"上传成功，图片 URL: {image_url}")
                    return image_url
                elif data.get("code") == "image_repeated":
                    image_url = data.get("images") or data.get("message", "").split("exists at: ")[-1].strip()
                    logging.info(f"图片重复，使用已有 URL: {image_url}")
                    return image_url
                else:
                    logging.error(f"上传失败: {data.get('message')}")
                    return ""
        except requests.RequestException as e:
            logging.error(f"图片上传网络请求出错: {str(e)}")
            return ""
        except Exception as e:
            logging.error(f"图片上传出错: {str(e)}")
            return ""


class NoiseMonitor:
    def __init__(self):
        """初始化噪音监控器"""

        self.config = Config()
        if not self.config.smms_api_key:
            logging.error("程序启动失败：无法获取 SM.MS API Token，将关闭 order 并重启程序")
            self.update_launch_json()
            self.restart_program()
            return

        self.app = QApplication.instance() or QApplication(sys.argv)
        self.decibel_thread = DecibelThread(self.config)
        self.decibel_thread.decibel_exceeded.connect(self.on_decibel_exceeded)
        self.decibel_thread.start()
        self.is_processing = False
        self.sound_effect = QSoundEffect()
        self.sound_effect.setSource(QUrl.fromLocalFile("icon/warning.wav"))

    def update_launch_json(self):
        """更新 launch.json 文件，将 order 改为关闭"""
        try:
            if not os.path.exists(LAUNCH_FILE):
                logging.warning(f"{LAUNCH_FILE} 不存在，创建默认文件")
                data = {"shutdown": "开启", "news": "关闭", "order": "关闭"}
            else:
                with open(LAUNCH_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["order"] = "关闭"

            with open(LAUNCH_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            logging.info(f"已更新 {LAUNCH_FILE}，order 设置为 '关闭'")
        except Exception as e:
            logging.error(f"更新 {LAUNCH_FILE} 失败: {str(e)}")

    def restart_program(self):
        """重启程序"""
        logging.info("正在重启程序...")
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def on_decibel_exceeded(self, db):
        """处理分贝超标事件"""
        if self.is_processing:
            logging.info(f"正在处理中，忽略超标信号: {db:.1f} dB")
            return

        logging.info(f"收到超标信号: {db:.1f} dB")
        self.is_processing = True
        self.decibel_thread.set_silent_period(10)
        self.sound_effect.play()
        popup = WarningPopup(f"噪音超标，15秒平均值: {db:.1f} dB\n如果噪音持续超标则会上报")
        popup.show()
        QTimer.singleShot(10000, lambda: self.start_second_detection(popup))

    def start_second_detection(self, popup):
        """启动第二次检测线程"""
        popup.hide()
        popup.deleteLater()
        logging.info("警告窗口关闭，开始第二次15秒检测")
        self.second_detection_thread = SecondDetectionThread(self.config)
        self.second_detection_thread.detection_complete.connect(self.on_second_detection_complete)
        self.second_detection_thread.start()

    def on_second_detection_complete(self, second_db):
        """处理第二次检测完成事件"""
        if second_db is None:
            logging.warning("第二次检测失败，返回循环检测")
            self.is_processing = False
            return

        if second_db <= self.config.threshold_db:
            logging.info(f"第二次检测未超标: {second_db:.1f} <= {self.config.threshold_db}，返回循环检测")
            self.is_processing = False
        else:
            logging.info(f"第二次检测仍超标: {second_db:.1f} > {self.config.threshold_db}，执行拍照上传")
            self.start_photo_upload()

    def start_photo_upload(self):
        """启动拍照和上传线程"""
        self.decibel_thread.set_silent_period(240)  # 设置4分钟静默期
        self.photo_upload_thread = PhotoUploadThread(self.config)
        self.photo_upload_thread.upload_complete.connect(self.on_upload_complete)
        self.photo_upload_thread.start()

    def on_upload_complete(self, url):
        """处理上传完成事件"""
        if url:
            logging.info(f"图片上传成功，URL: {url}")
            timer = QTimer(self.app)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: self.send_dingtalk_message(url))
            timer.start(60000)  # 延迟1分钟发送钉钉消息
        else:
            logging.error("未获取到有效图片 URL，跳过钉钉消息发送")
            self.is_processing = False

    def send_dingtalk_message(self, url):
        """发送钉钉消息"""
        logging.info(f"开始发送钉钉消息，URL: {url}")
        self.dingtalk_thread = DingTalkThread(url, self.config.webhook_url)
        self.dingtalk_thread.message_sent.connect(self.on_dingtalk_finished)
        self.dingtalk_thread.start()

    def on_dingtalk_finished(self):
        """钉钉消息发送完成"""
        logging.info("钉钉消息发送完成")
        self.is_processing = False


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        monitor = NoiseMonitor()
        sys.exit(app.exec())
    except Exception as e:
        logging.error(f"程序主循环异常: {str(e)}")
        sys.exit(1)