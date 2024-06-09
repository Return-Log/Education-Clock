import sys
import os
import imaplib
import smtplib
import email
from email.header import decode_header
from email.message import EmailMessage
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit
from PyQt5.QtCore import QTimer
from PyQt5.QtMultimedia import QSound
import datetime
import pytz

class EmailClient(QWidget):
    def __init__(self):
        super().__init__()
        self.email_address, self.email_password = self.read_email_credentials()
        self.processed_uids = set()  # 用于存储已处理的邮件UID
        self.initial_check = True  # 标志以指示初始检查

        # 每 10 秒检查一次新邮件
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_inbox)
        self.timer.start(10000)

        self.initUI()  # 初始化用户界面

    def initUI(self):
        self.setWindowTitle('邮件客户端')
        self.setGeometry(100, 100, 800, 600)
        layout = QVBoxLayout()

        self.textEdit = QTextEdit(self)
        self.textEdit.setReadOnly(True)  # 设置文本框为只读
        layout.addWidget(self.textEdit)

        self.setLayout(layout)

    def read_email_credentials(self):
        try:
            with open('data/email.txt', 'r') as file:
                lines = file.readlines()
                email_address = lines[0].strip()
                email_password = lines[1].strip()
            return email_address, email_password
        except FileNotFoundError:
            print("邮箱配置文件不存在，请确保 'data/email.txt' 存在并包含正确的邮箱地址和密码。")
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
            if self.initial_check:
                date = (datetime.date.today() - datetime.timedelta(days=7)).strftime('%d-%b-%Y')
            else:
                date = (datetime.date.today() - datetime.timedelta(days=7)).strftime('%d-%b-%Y')
            result, data = mail.search(None, f'(SINCE {date})')

            if result != 'OK':
                self.textEdit.append(f'无法搜索邮件: {result}')
                return

            mail_ids = data[0].split()
            mail_ids.sort(reverse=False)  # 按顺序排序邮件ID

            for mail_id in mail_ids:
                if mail_id not in self.processed_uids:  # 只处理未处理过的邮件
                    result, data = mail.fetch(mail_id, '(RFC822)')
                    if result != 'OK':
                        self.textEdit.append(f'无法获取邮件: {result}')
                        continue

                    raw_email = data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    if not self.initial_check:  # 初始检查时不播放音频和发送自动回复
                        self.play_audio()
                        self.send_auto_reply(msg['From'], msg['Subject'])

                    self.handle_new_email(msg)
                    self.processed_uids.add(mail_id)  # 处理后将邮件ID加入已处理集合

            mail.logout()

            # 初始检查完成后将标志设置为False
            if self.initial_check:
                self.initial_check = False

        except imaplib.IMAP4.error as e:
            self.textEdit.append(f'IMAP4 错误: {str(e)}')
        except Exception as e:
            self.textEdit.append(f'检查收件箱出错: {str(e)}')

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
                        part_body = part.get_payload(decode=True).decode('utf-8')
                    except:
                        part_body = "无法解码"

                    if content_type == "text/plain" and "attachment" not in content_disposition and part_body:
                        body = part_body
                        break
            else:
                body = msg.get_payload(decode=True).decode('utf-8')

            # 转换日期
            date = email.utils.parsedate_to_datetime(date)
            local_tz = pytz.timezone("Asia/Shanghai")  # 东八区
            date = date.astimezone(local_tz)
            date_str = date.strftime('%Y-%m-%d %H:%M:%S %A').replace('Monday', '星期一').replace('Tuesday', '星期二').replace('Wednesday', '星期三').replace('Thursday', '星期四').replace('Friday', '星期五').replace('Saturday', '星期六').replace('Sunday', '星期日')

            # 使用 HTML 显示邮件内容，并将新邮件添加到顶部
            new_email_content = f'<b>日期:</b> {date_str}<br><b>发件人:</b> {from_}<br><b>主题:</b> {subject}<br><pre>{body}</pre><hr>'
            current_content = self.textEdit.toHtml()
            updated_content = f'{new_email_content}{current_content}'
            self.textEdit.setHtml(updated_content)
        except Exception as e:
            self.textEdit.append(f'处理新邮件时出错: {str(e)}')

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
            self.textEdit.append(f'自动回复出错: {str(e)}')

    def play_audio(self):
        try:
            audio_path = os.path.join(os.getcwd(), 'audio', 'notice.wav')  # 获取音频文件路径
            QSound.play(audio_path)  # 播放音频
        except Exception as e:
            self.textEdit.append(f'播放音频出错: {str(e)}')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = EmailClient()
    ex.show()
    sys.exit(app.exec_())
