import sys
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox, QFormLayout
)
from PyQt6.QtCore import QUrl
from PyQt6.QtWebSockets import QWebSocket
from PyQt6.QtNetwork import QAbstractSocket

class BulletinClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("教室公告显示端")
        self.setMinimumSize(600, 400)

        # 修改为你的服务器地址
        self.server_url = QLineEdit("ws://49.232.95.215:8000/ws")
        self.class_id = QLineEdit("1")
        self.token = QLineEdit("schoolA_class1_1_key")
        self.connect_btn = QPushButton("连接")
        self.connect_btn.clicked.connect(self.toggle_connection)

        settings_group = QGroupBox("连接设置")
        form = QFormLayout()
        form.addRow("服务器地址:", self.server_url)
        form.addRow("班级ID:", self.class_id)
        form.addRow("设备密钥:", self.token)
        form.addRow("", self.connect_btn)
        settings_group.setLayout(form)

        self.display = QTextEdit()
        self.display.setReadOnly(True)

        self.status_bar = self.statusBar()
        self.status_label = QLabel("未连接")
        self.status_bar.addWidget(self.status_label)

        central = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(settings_group)
        layout.addWidget(QLabel("收到的公告:"))
        layout.addWidget(self.display)
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.ws = QWebSocket()
        self.ws.connected.connect(self.on_connected)
        self.ws.disconnected.connect(self.on_disconnected)
        self.ws.textMessageReceived.connect(self.on_message)
        self.ws.errorOccurred.connect(self.on_error)

        self.is_connected = False

    def toggle_connection(self):
        if not self.is_connected:
            url = self.server_url.text().strip()
            cid = self.class_id.text().strip()
            tok = self.token.text().strip()
            if not url or not cid or not tok:
                self.status_label.setText("请填写完整连接信息")
                return
            ws_url = f"{url}?class_id={cid}&token={tok}"
            self.ws.open(QUrl(ws_url))
            self.connect_btn.setEnabled(False)
            self.status_label.setText("正在连接...")
        else:
            self.ws.close()
            self.connect_btn.setText("连接")
            self.is_connected = False
            self.status_label.setText("已断开")

    def on_connected(self):
        self.is_connected = True
        self.connect_btn.setText("断开")
        self.connect_btn.setEnabled(True)
        self.status_label.setText("已连接")
        self.display.append("<系统> 已成功连接到服务器")

    def on_disconnected(self):
        self.is_connected = False
        self.connect_btn.setText("连接")
        self.connect_btn.setEnabled(True)
        self.status_label.setText("连接已断开")

    def on_message(self, message: str):
        try:
            data = json.loads(message)
            content = data.get("content", message)
            self.display.append(f"<公告> {content}")
        except json.JSONDecodeError:
            self.display.append(f"<原始消息> {message}")

    def on_error(self, error: QAbstractSocket.SocketError):
        self.status_label.setText(f"连接错误: {error}")
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("连接")
        self.is_connected = False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BulletinClient()
    window.show()
    sys.exit(app.exec())