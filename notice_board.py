import sys
import os
import imaplib
import smtplib
import email
from email.header import decode_header
from email.message import EmailMessage
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QLabel, QSizePolicy
from PyQt5.QtCore import Qt, QPoint, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl
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
        while True:
            self.check_inbox()
            self.sleep(10)  # 每10秒检查一次新邮件

    def check_inbox(self):
        try:
            # 连接到邮件服务器
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
        self.processed_uids = set()  # 用于存储已处理的邮件UID
        self.initial_check_completed = False  # 标志以指示初始检查是否完成
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'zh' in voice.languages:
                self.engine.setProperty('voice', voice.id)
                break

        self.player = QMediaPlayer()
        self.player.setVolume(100)  # 设置音量为100（范围是0到100）

        self.initUI()  # 初始化用户界面

        # 创建并启动邮件检查线程
        self.email_checker = EmailChecker(self.email_address, self.email_password, self.processed_uids, True, self.error_signal)
        self.email_checker.new_email.connect(self.handle_new_email)
        self.email_checker.initial_check_completed_signal.connect(self.set_initial_check_completed)
        self.email_checker.start()
        self.error_signal.connect(self.handle_error)

    def handle_error(self, error_message):
        self.notice_textEdit.append(f'<b>错误:</b> {error_message}')

    def set_initial_check_completed(self):
        self.initial_check_completed = True

    def initUI(self):
        # 设置窗口无边框
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setWindowTitle('邮件公告板')
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint)  # 设置窗口无边框并保持在底层
        self.load_window_settings()  # 加载窗口位置和大小设置

        layout = QVBoxLayout()

        font_label = QFont("微软雅黑", 9)
        font = QFont("微软雅黑", 12)
        self.bg_color = QColor(220, 220, 220)  # 设置背景颜色为灰色
        self.text_color = QColor(0, 0, 0)

        self.notice_label = QLabel("通知")
        self.notice_label.setFont(font_label)
        layout.addWidget(self.notice_label)

        self.notice_textEdit = QTextEdit(self)
        self.notice_textEdit.setReadOnly(True)  # 设置文本框为只读
        self.notice_textEdit.setFont(font)
        self.notice_textEdit.setStyleSheet(
            f"background-color: {self.bg_color.name()}; color: {self.text_color.name()};")
        self.notice_textEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.notice_textEdit, 3)  # 设置伸缩因子为3

        self.report_label = QLabel("通报")
        self.report_label.setFont(font_label)
        layout.addWidget(self.report_label)

        self.report_textEdit = QTextEdit(self)
        self.report_textEdit.setReadOnly(True)  # 设置文本框为只读
        self.report_textEdit.setFont(font)
        self.report_textEdit.setStyleSheet(
            f"background-color: {self.bg_color.name()}; color: {self.text_color.name()};")
        self.report_textEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.report_textEdit, 2)  # 设置伸缩因子为2

        self.call_label = QLabel("广播")
        self.call_label.setFont(font_label)
        layout.addWidget(self.call_label)

        self.call_textEdit = QTextEdit(self)
        self.call_textEdit.setReadOnly(True)  # 设置文本框为只读
        self.call_textEdit.setFont(font)
        self.call_textEdit.setStyleSheet(
            f"background-color: {self.bg_color.name()}; color: {self.text_color.name()};")
        self.call_textEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.call_textEdit, 1)  # 设置伸缩因子为1

        self.setLayout(layout)

        # 用于支持拖动和调整大小的变量
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
        # 在窗口关闭时保存设置
        self.save_window_settings()
        event.accept()

    def mousePressEvent(self, event):
        # 处理鼠标按下事件，用于拖动和调整大小
        if event.button() == Qt.LeftButton:
            if event.pos().x() > self.width() - 10 and event.pos().y() > self.height() - 10:
                self.resizing = True
                self.resize_start_position = event.globalPos()
                self.resize_start_size = self.size()
            else:
                self.dragging = True
                self.drag_start_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        # 处理鼠标移动事件，用于拖动和调整大小
        if self.dragging:
            self.move(event.globalPos() - self.drag_start_position)
            event.accept()
        elif self.resizing:
            delta = event.globalPos() - self.resize_start_position
            new_size = self.resize_start_size + QSize(delta.x(), delta.y())
            self.resize(new_size)
            event.accept()

    def mouseReleaseEvent(self, event):
        # 处理鼠标释放事件，重置拖动和调整大小状态
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.resizing = False
            event.accept()

    def handle_new_email(self, msg):
        try:
            subject, encoding = decode_header(msg['Subject'])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else 'utf-8')
            from_ = msg.get('From')
            date = msg.get('Date')

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition'))

                    try:
                        part_body = part.get_payload(decode=True)
                        for enc in ['utf-8', 'gbk', 'gb2312', 'big5']:
                            try:
                                part_body = part_body.decode(enc)
                                break
                            except (UnicodeDecodeError, AttributeError):
                                pass
                    except Exception as e:
                        part_body = "无法解码"

                    if content_type == "text/plain" and "attachment" not in content_disposition and part_body:
                        body = part_body
                        break
            else:
                part_body = msg.get_payload(decode=True)
                for enc in ['utf-8', 'gbk', 'gb2312', 'big5']:
                    try:
                        body = part_body.decode(enc)
                        break
                    except (UnicodeDecodeError, AttributeError):
                        pass

            date = email.utils.parsedate_to_datetime(date)
            local_tz = pytz.timezone("Asia/Shanghai")
            date = date.astimezone(local_tz)
            date_str = date.strftime('%m-%d %H:%M %A').replace('Monday', '星期一').replace('Tuesday', '星期二').replace(
                'Wednesday', '星期三').replace('Thursday', '星期四').replace('Friday', '星期五').replace('Saturday', '星期六').replace(
                'Sunday', '星期日')

            new_email_content = f'<b>日期:</b> {date_str}&emsp;<b>发件人:</b> {from_}<br><b>主题: {subject}</b><br>{body}<hr>'

            if '通知' in subject:
                current_content = self.notice_textEdit.toHtml()
                self.notice_textEdit.setHtml(f'{new_email_content}{current_content}')
                if self.initial_check_completed:
                    self.play_audio()
            elif '通报' in subject:
                current_content = self.report_textEdit.toHtml()
                self.report_textEdit.setHtml(f'{new_email_content}{current_content}')
                if self.initial_check_completed:
                    self.play_audio()
            elif '呼叫' in subject or '广播' in subject:
                current_content = self.call_textEdit.toHtml()
                self.call_textEdit.setHtml(f'{new_email_content}{current_content}')
                if self.initial_check_completed:
                    self.play_audio()
                    self.speak_text(body)

        except Exception as e:
            self.handle_error(f'处理新邮件时出错: {str(e)}')

    def play_audio(self):
        audio_file = 'audio/notice.wav'
        url = QUrl.fromLocalFile(os.path.abspath(audio_file))
        content = QMediaContent(url)
        self.player.setMedia(content)
        self.player.play()

    def speak_text(self, text):
        self.engine.say(text)
        self.engine.runAndWait()

    def read_email_credentials(self):
        # 从配置文件中读取邮件地址和密码
        try:
            with open('data/[邮箱地址和密码]email_credentials.json', 'r') as f:
                credentials = json.load(f)
                return credentials['email_address'], credentials['email_password']
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            self.handle_error(f'读取邮箱凭据时出错: {str(e)}')
            return '', ''


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = EmailClient()
    ex.show()
    sys.exit(app.exec_())
