import random
import sys
import os
from PyQt6.QtWidgets import QDialog, QLabel, QApplication, QVBoxLayout
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QObject
from PyQt6.QtGui import QFont
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget


class RollCallDialog(QDialog):
    # 定义信号类，用于外部通信
    class RollCallSignals(QObject):
        closed = pyqtSignal()  # 窗口关闭信号

    def __init__(self):
        super().__init__()  # 不接受 parent 参数

        self.setWindowTitle('随机点名')
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)  # 独立窗口，保持顶层
        # 可选：无边框
        # self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)

        # 设置窗口背景为白色，固定16:9比例
        self.setStyleSheet("background-color: white;")
        self.setFixedSize(800, 450)

        # 读取名字列表
        self.names = self.load_names()

        # 初始化布局和控件，去除边距
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # 视频控件（最下层）
        self.video_widget = QVideoWidget(self)
        self.video_widget.hide()
        self.layout.addWidget(self.video_widget)
        self.video_widget.setGeometry(0, 0, self.width(), self.height())
        self.video_widget.lower()

        # 名字标签（黑色文字，强制字体大小和家族）
        self.name_label = QLabel("", self)
        font = QFont("华文行楷", 140)
        self.name_label.setFont(font)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet("""
            QLabel {
                color: black;
                font-size: 140pt !important;
                font-family: 华文行楷 !important;
            }
        """)
        self.layout.addWidget(self.name_label)
        self.name_label.setText("点击开始")

        # 将窗口居中
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

        # 初始化视频播放器
        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.media_player.errorOccurred.connect(self.on_media_error)

        # 启用鼠标事件跟踪
        self.setMouseTracking(True)
        self.is_rolling = False

        # 初始化信号
        self.signals = self.RollCallSignals()

        self.show()


    def load_names(self):
        """从文件中加载名字列表，返回带标记的名字"""
        try:
            with open('./data/name.txt', 'r', encoding='utf-8') as file:
                names = [line.strip() for line in file.readlines()]
            return names if names else []
        except FileNotFoundError:
            self.name_label.setText("找不到 name.txt 文件")
            return []

    def save_names(self):
        """将当前名字列表（含标记）保存到文件"""
        try:
            with open('./data/name.txt', 'w', encoding='utf-8') as file:
                for name in self.names:
                    file.write(f"{name}\n")
        except Exception as e:
            self.name_label.setText(f"保存名字失败: {str(e)}")

    def mousePressEvent(self, event):
        """处理鼠标点击事件，开始点名"""
        if self.is_rolling:
            return
        self.start_roll_call()

    def start_roll_call(self):
        """开始点名，先尝试播放视频，结束后显示名字"""
        if not self.names:
            self.name_label.setText("没有可用的名字")
            return

        self.is_rolling = True
        self.name_label.hide()

        video_path = "./icon/roll_call_background.mp4"
        if os.path.exists(video_path):
            try:
                self.video_widget.setGeometry(0, 0, self.width(), self.height())
                self.video_widget.show()
                self.video_widget.lower()
                self.media_player.setSource(QUrl.fromLocalFile(video_path))
                self.media_player.play()
            except Exception as e:
                self.cleanup_media()
                self.display_name()
        else:
            self.display_name()

    def on_media_status_changed(self, status):
        """处理视频播放状态变化"""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.cleanup_media()
            self.display_name()
        elif status == QMediaPlayer.MediaStatus.NoMedia or status == QMediaPlayer.MediaStatus.InvalidMedia:
            self.cleanup_media()
            self.display_name()

    def on_media_error(self, error):
        """处理视频播放错误"""
        self.cleanup_media()
        self.display_name()

    def cleanup_media(self):
        """清理视频播放资源"""
        try:
            self.media_player.stop()
            self.media_player.setSource(QUrl())
            self.video_widget.hide()
        except Exception as e:
            pass

    def display_name(self):
        """显示随机选择的一个名字并仅标记该名字"""
        if not self.is_rolling:
            return

        unmarked_names = [name for name in self.names if not name.endswith('*')]
        if not unmarked_names:
            self.names = [name.rstrip('*') for name in self.names]
            self.save_names()
            unmarked_names = self.names

        selected_name = random.choice(unmarked_names)
        self.name_label.setText(selected_name)
        self.name_label.show()

        marked = False
        for i, name in enumerate(self.names):
            if name == selected_name and not name.endswith('*') and not marked:
                self.names[i] = f"{name}*"
                marked = True
                break
        self.save_names()

        self.is_rolling = False

    def resizeEvent(self, event):
        """保持16:9比例并调整视频大小"""
        super().resizeEvent(event)
        new_width = self.width()
        new_height = int(new_width * 9 / 16)
        self.setFixedSize(new_width, new_height)
        if self.video_widget.isVisible():
            self.video_widget.setGeometry(0, 0, new_width, new_height)
            self.video_widget.lower()

    def closeEvent(self, event):
        """窗口关闭时保存名字并释放资源"""
        self.save_names()
        self.cleanup_media()
        self.signals.closed.emit()  # 发射关闭信号
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = RollCallDialog()
    dialog.show()
    sys.exit(app.exec())