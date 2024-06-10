import sys
import os
import imaplib
import smtplib
import email
from email.header import decode_header
from email.message import EmailMessage
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QLabel
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtMultimedia import QSound
import datetime
import pytz
import pyttsx3


class EmailClient(QWidget):
    def __init__(self):
        super().__init__()
        self.email_address, self.email_password = self.read_email_credentials()
        self.processed_uids = set()  # 用于存储已处理的邮件UID
        self.initial_check = True  # 标志以指示初始检查
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)  # 设置语速
        self.engine.setProperty('voice', 'zh')  # 设置语音为中文

        # 每 10 秒检查一次新邮件
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_inbox)
        self.timer.start(10000)

        self.initUI()  # 初始化用户界面

    def initUI(self):
        # 隐藏窗口的标题栏
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setWindowTitle('邮件公告板')
        self.setGeometry(100, 100, 800, 600)
        layout = QVBoxLayout()

        font = QFont("微软雅黑", 10)
        bg_color = QColor(255, 255, 255)
        text_color = QColor(0, 0, 0)

        self.notice_label = QLabel("通知")
        self.notice_label.setFont(font)
        layout.addWidget(self.notice_label)
        self.notice_textEdit = QTextEdit(self)
        self.notice_textEdit.setReadOnly(True)  # 设置文本框为只读
        self.notice_textEdit.setFont(font)
        self.notice_textEdit.setStyleSheet(
            f"background-color: {bg_color.name()}; color: {text_color.name()}; height: 230px;")
        layout.addWidget(self.notice_textEdit)

        self.report_label = QLabel("通报")
        self.report_label.setFont(font)
        layout.addWidget(self.report_label)
        self.report_textEdit = QTextEdit(self)
        self.report_textEdit.setReadOnly(True)  # 设置文本框为只读
        self.report_textEdit.setFont(font)
        self.report_textEdit.setStyleSheet(
            f"background-color: {bg_color.name()}; color: {text_color.name()}; height: 100px;")
        layout.addWidget(self.report_textEdit)

        self.call_label = QLabel("广播")
        self.call_label.setFont(font)
        layout.addWidget(self.call_label)
        self.call_textEdit = QTextEdit(self)
        self.call_textEdit.setReadOnly(True)  # 设置文本框为只读
        self.call_textEdit.setFont(font)
        self.call_textEdit.setStyleSheet(
            f"background-color: {bg_color.name()}; color: {text_color.name()}; height: 70px;")
        layout.addWidget(self.call_textEdit)

        self.setLayout(layout)

    def read_email_credentials(self):
        try:
            with open('data/[公告板邮箱]email.txt', 'r') as file:
                lines = file.readlines()
                email_address = lines[0].strip()
                email_password = lines[1].strip()
            return email_address, email_password
        except FileNotFoundError:
            print("邮箱配置文件不存在，请确保 'data/[公告板邮箱]email.txt' 存在并包含正确的邮箱地址和密码。")
            sys.exit(1)
        except Exception as e:
            print(f"读取邮箱配置文件时出现错误: {e}")
            sys.exit(1)

    def check_inbox(self):
        try:
            # 连接到 IMAP 服务器
            mail = imaplib.IMAP4_SSL('imap-mail.outlook.com')  # 使用 Outlook 的 IMAP 服务器
            mail.login(self.email_address, self.email_password)
            mail.select('inbox')

            # 如果是初始检查，获取过去7天的邮件；否则获取最近7天的邮件
            date = (datetime.date.today() - datetime.timedelta(days=7)).strftime('%d-%b-%Y')
            result, data = mail.search(None, f'(SINCE {date})')

            if result != 'OK':
                self.notice_textEdit.append(f'无法搜索邮件: {result}')
                return

            mail_ids = data[0].split()
            mail_ids.sort(reverse=False)  # 按顺序排序邮件ID

            for mail_id in mail_ids:
                if mail_id not in self.processed_uids:  # 只处理未处理过的邮件
                    result, data = mail.fetch(mail_id, '(RFC822)')
                    if result != 'OK':
                        self.notice_textEdit.append(f'无法获取邮件: {result}')
                        continue

                    raw_email = data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    if not self.initial_check:  # 初始检查时不播放音频和发送自动回复
                        self.send_auto_reply(msg['From'], msg['Subject'])

                    self.handle_new_email(msg)
                    self.processed_uids.add(mail_id)  # 处理后将邮件ID加入已处理集合

            mail.logout()

            # 初始检查完成后将标志设置为False
            if self.initial_check:
                self.initial_check = False

        except imaplib.IMAP4.error as e:
            self.notice_textEdit.append(f'IMAP4 错误: {str(e)}')
        except Exception as e:
            self.notice_textEdit.append(f'检查收件箱出错: {str(e)}')

    def handle_new_email(self, msg):
        try:
            subject, encoding = decode_header(msg['Subject'])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else 'utf-8')
            from_ = msg.get('From')
            date = msg.get('Date')

            body = ""
            # 如果邮件是多部分的，则获取其内容
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition'))

                    try:
                        part_body = part.get_payload(decode=True)
                        # 尝试用不同的编码解码
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
                # 尝试用不同的编码解码
                for enc in ['utf-8', 'gbk', 'gb2312', 'big5']:
                    try:
                        body = part_body.decode(enc)
                        break
                    except (UnicodeDecodeError, AttributeError):
                        pass

            # 转换日期
            date = email.utils.parsedate_to_datetime(date)
            local_tz = pytz.timezone("Asia/Shanghai")  # 东八区
            date = date.astimezone(local_tz)
            date_str = date.strftime('%m-%d %H:%M %A').replace('Monday', '星期一').replace('Tuesday',
                                                                                           '星期二').replace(
                'Wednesday', '星期三').replace('Thursday', '星期四').replace('Friday', '星期五').replace('Saturday',
                                                                                                         '星期六').replace(
                'Sunday', '星期日')

            new_email_content = f'<b>日期:</b> {date_str}&emsp;<b>发件人:</b> {from_}<br><b>主题: {subject}</b><br>{body}<hr>'

            if '通知' in subject:
                current_content = self.notice_textEdit.toHtml()
                self.notice_textEdit.setHtml(f'{new_email_content}{current_content}')
                if not self.initial_check:
                    self.play_audio()  # 播放通知音
            elif '通报' in subject:
                current_content = self.report_textEdit.toHtml()
                self.report_textEdit.setHtml(f'{new_email_content}{current_content}')
                if not self.initial_check:
                    self.play_audio()  # 播放通知音
            elif '呼叫' in subject or '广播' in subject:
                current_content = self.call_textEdit.toHtml()
                self.call_textEdit.setHtml(f'{new_email_content}{current_content}')
                if not self.initial_check:
                    self.play_audio()  # 播放通知音
                    self.speak_text(body)  # 播报邮件内容
        except Exception as e:
            self.notice_textEdit.append(f'处理新邮件时出错: {str(e)}')

    def send_auto_reply(self, to_email, original_subject):
        try:
            msg = EmailMessage()
            msg.set_content("消息已推送")
            msg['Subject'] = f"Re: {original_subject}"
            msg['From'] = self.email_address
            msg['To'] = to_email

            with smtplib.SMTP('smtp-mail.outlook.com', 587) as server:  # 使用 Outlook 的 SMTP 服务器
                server.starttls()  # 启用 TLS
                server.login(self.email_address, self.email_password)
                server.send_message(msg)

        except Exception as e:
            self.notice_textEdit.append(f'自动回复出错: {str(e)}')

    def play_audio(self):
        try:
            audio_path = os.path.join(os.getcwd(), 'audio', 'notice.wav')  # 获取音频文件路径
            QSound.play(audio_path)  # 播放音频
        except Exception as e:
            self.notice_textEdit.append(f'播放音频出错: {str(e)}')

    def speak_text(self, text):
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            self.notice_textEdit.append(f'语音播报出错: {str(e)}')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = EmailClient()
    ex.show()
    sys.exit(app.exec_())
