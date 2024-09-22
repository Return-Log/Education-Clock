import sys
import os
import imaplib
import smtplib
import email
from email.header import decode_header
from email.message import EmailMessage
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, QPoint, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl
import datetime
import pytz
import pyttsx3
import json

# 邮件检查线程类
class EmailChecker(QThread):
    # 定义新邮件信号
    new_email = pyqtSignal(email.message.Message)
    initial_check_completed_signal = pyqtSignal()

    def __init__(self, email_address, email_password, processed_uids, initial_check, error_signal):
        super().__init__()
        self.email_address = email_address
        self.email_password = email_password
        self.processed_uids = processed_uids
        self.initial_check = initial_check
        self.error_signal = error_signal

    def run(self):
        # 持续检查收件箱
        while True:
            self.check_inbox()
            self.sleep(10)  # 每10秒检查一次新邮件

    def check_inbox(self):
        # 检查收件箱并处理新邮件
        try:
            mail = imaplib.IMAP4_SSL('imap-mail.outlook.com')
            mail.login(self.email_address, self.email_password)
            mail.select('inbox')

            date = (datetime.date.today() - datetime.timedelta(days=7)).strftime('%d-%b-%Y')
            result, data = mail.search(None, f'(SINCE {date})')

            if result != 'OK':
                return

            mail_ids = data[0].split()
            mail_ids.sort(reverse=False)

            for mail_id in mail_ids:
                if mail_id not in self.processed_uids:
                    result, data = mail.fetch(mail_id, '(RFC822)')
                    if result != 'OK':
                        continue

                    raw_email = data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    if not self.initial_check:
                        self.send_auto_reply(msg['From'], msg['Subject'])

                    self.new_email.emit(msg)
                    self.processed_uids.add(mail_id)

            mail.logout()

            if self.initial_check:
                self.initial_check = False
                self.initial_check_completed_signal.emit()

        except Exception as e:
            self.error_signal.emit(f'检查收件箱出错，请输入正确邮箱: {str(e)}')

    def send_auto_reply(self, to_email, original_subject):
        # 自动回复邮件
        try:
            msg = EmailMessage()
            msg.set_content("消息已推送")
            msg['Subject'] = f"Re: {original_subject}"
            msg['From'] = self.email_address
            msg['To'] = to_email

            with smtplib.SMTP('smtp-mail.outlook.com', 587) as server:
                server.starttls()
                server.login(self.email_address, self.email_password)
                server.send_message(msg)

        except Exception as e:
            self.error_signal.emit(f'自动回复出错: {str(e)}')


# 邮件客户端主窗口类
class EmailClient(QWidget):
    error_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.email_address, self.email_password = self.read_email_credentials()
        self.processed_uids = set()  # 已处理邮件的UID集合
        self.initial_check_completed = False  # 初始检查是否完成
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'zh' in voice.languages:
                self.engine.setProperty('voice', voice.id)
                break

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)  # 设置音量为100%
        self.dragging = False  # 确保初始状态为 False
        self.resizing = False  # 确保初始状态为 False
        self.drag_start_position = QPoint()
        self.resize_start_position = QPoint()
        self.resize_start_size = QSize()

        self.initUI()  # 初始化用户界面

        # 创建并启动邮件检查线程
        self.email_checker = EmailChecker(self.email_address, self.email_password, self.processed_uids, True, self.error_signal)
        self.email_checker.new_email.connect(self.handle_new_email)
        self.email_checker.initial_check_completed_signal.connect(self.set_initial_check_completed)
        self.email_checker.start()
        self.error_signal.connect(self.handle_error)

    def handle_error(self, error_message):
        # 处理错误信息
        self.notice_textEdit.append(f'<b>错误:</b> {error_message}')

    def set_initial_check_completed(self):
        # 设置初始检查完成标志
        self.initial_check_completed = True

    def initUI(self):
        # 初始化UI界面
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle('邮件公告板')
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnBottomHint)  # 无边框且保持窗口在底层
        self.load_window_settings()  # 加载窗口位置和大小设置

        layout = QVBoxLayout()

        font_label = QFont("微软雅黑", 9)
        font = QFont("微软雅黑", 12)
        self.bg_color = QColor(220, 220, 220)  # 设置背景颜色为灰色
        self.text_color = QColor(0, 0, 0)

        # 通知部分
        self.notice_label = QLabel("通知")
        self.notice_label.setFont(font_label)
        layout.addWidget(self.notice_label)

        self.notice_textEdit = QTextEdit(self)
        self.notice_textEdit.setReadOnly(True)
        self.notice_textEdit.setFont(font)
        self.notice_textEdit.setStyleSheet(
            f"background-color: {self.bg_color.name()}; color: {self.text_color.name()};")
        self.notice_textEdit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.notice_textEdit, 3)

        # 通报部分
        self.report_label = QLabel("通报")
        self.report_label.setFont(font_label)
        layout.addWidget(self.report_label)

        self.report_textEdit = QTextEdit(self)
        self.report_textEdit.setReadOnly(True)
        self.report_textEdit.setFont(font)
        self.report_textEdit.setStyleSheet(
            f"background-color: {self.bg_color.name()}; color: {self.text_color.name()};")
        self.report_textEdit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.report_textEdit, 2)

        # 广播部分
        self.call_label = QLabel("广播")
        self.call_label.setFont(font_label)
        layout.addWidget(self.call_label)

        self.call_textEdit = QTextEdit(self)
        self.call_textEdit.setReadOnly(True)
        self.call_textEdit.setFont(font)
        self.call_textEdit.setStyleSheet(
            f"background-color: {self.bg_color.name()}; color: {self.text_color.name()};")
        self.call_textEdit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.call_textEdit, 1)

        self.setLayout(layout)

        # 支持拖动和调整窗口大小
        self.dragging = False
        self.resizing = False
        self.drag_start_position = QPoint()
        self.resize_start_position = QPoint()
        self.resize_start_size = QSize()

    def load_window_settings(self):
        # 从 JSON 文件加载窗口设置
        try:
            with open('data/[公告板位置]window_settings.json', 'r') as f:
                settings = json.load(f)
                self.move(QPoint(settings['pos_x'], settings['pos_y']))
                self.resize(QSize(settings['width'], settings['height']))
        except (FileNotFoundError, KeyError, json.JSONDecodeError):
            self.setGeometry(100, 100, 800, 600)

    def save_window_settings(self):
        # 保存窗口设置到 JSON 文件
        settings = {
            'pos_x': self.pos().x(),
            'pos_y': self.pos().y(),
            'width': self.size().width(),
            'height': self.size().height()
        }
        with open('data/[公告板位置]window_settings.json', 'w') as f:
            json.dump(settings, f)

    def closeEvent(self, event):
        # 窗口关闭时保存设置
        self.save_window_settings()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查是否在窗口右下角，用于调整大小
            if event.pos().x() >= self.width() - 10 and event.pos().y() >= self.height() - 10:
                self.resizing = True
                self.resize_start_position = event.globalPosition().toPoint()
                self.resize_start_size = self.size()
            else:
                # 否则处理拖动逻辑
                self.dragging = True
                self.drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging:
            # 拖动窗口逻辑
            new_pos = event.globalPosition().toPoint() - self.drag_start_position
            self.move(new_pos)
            event.accept()
        elif self.resizing:
            # 缩放窗口逻辑
            delta = event.globalPosition().toPoint() - self.resize_start_position
            new_size = self.resize_start_size + QSize(delta.x(), delta.y())
            self.resize(max(new_size.width(), 400), max(new_size.height(), 300))  # 设置最小尺寸
            event.accept()

    def mouseReleaseEvent(self, event):
        # 释放鼠标时清除拖动和缩放状态
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.resizing = False
            event.accept()

    def handle_new_email(self, msg):
        # 处理新邮件，更新界面并播放提示音
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain' or content_type == 'text/html':
                    message_body = part.get_payload(decode=True).decode()
                    break
        else:
            message_body = msg.get_payload(decode=True).decode()

        subject = decode_header(msg['Subject'])[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode()

        from_ = msg['From']
        email_time = email.utils.parsedate_to_datetime(msg['Date'])
        email_time = email_time.astimezone(pytz.timezone('Asia/Shanghai'))

        if '通报' in subject:
            self.report_textEdit.append(f'<b>新邮件:</b> {from_} - {subject} ({email_time})<br>{message_body}')
        elif '通知' in subject:
            self.notice_textEdit.append(f'<b>新邮件:</b> {from_} - {subject} ({email_time})<br>{message_body}')
        elif '广播' in subject:
            self.call_textEdit.append(f'<b>新邮件:</b> {from_} - {subject} ({email_time})<br>{message_body}')

        self.player.setSource(QUrl.fromLocalFile("data/[公告板声音]new_email_sound.mp3"))
        self.player.play()

        self.engine.say(f"新邮件, 发件人: {from_}, 主题: {subject}")
        self.engine.runAndWait()

    def read_email_credentials(self):
        # 从文件中读取邮箱地址和密码
        try:
            with open('data/[公告板登录]email_credentials.json', 'r') as f:
                credentials = json.load(f)
                return credentials['email_address'], credentials['email_password']
        except (FileNotFoundError, KeyError, json.JSONDecodeError):
            return '', ''


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = EmailClient()
    window.show()
    sys.exit(app.exec())
