import random
import sys
import os
import logging
from PyQt6.QtWidgets import QDialog, QLabel, QApplication, QVBoxLayout
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget

# # 配置日志
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler("roll_call.log"),
#         logging.StreamHandler()
#     ]
# )

class RollCallDialog(QDialog):
    class RollCallSignals(QObject):
        closed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle('随机点名')
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("background-color: white;")
        self.setFixedSize(800, 450)

        # 读取名字列表
        self.names = self.load_names()
        if not self.names:
            logging.error("No names loaded, dialog may not function correctly")

        # 初始化布局和控件
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # 视频控件
        self.video_widget = QVideoWidget(self)
        self.video_widget.hide()
        self.layout.addWidget(self.video_widget)

        # 名字标签
        self.name_label = QLabel("点击开始", self)
        preferred_font = "华文行楷"
        fallback_font = "微软雅黑"
        font = QFont(preferred_font, 140) if preferred_font in QFontDatabase.families() else QFont(fallback_font, 140, QFont.Weight.Bold)
        self.name_label.setFont(font)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet(f"""
            QLabel {{
                color: black;
                font-size: 140pt;
                font-family: {font.family()};
            }}
        """)
        self.layout.addWidget(self.name_label)

        # 居中窗口
        screen = QApplication.primaryScreen().availableGeometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

        # 初始化视频播放器
        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.media_player.errorOccurred.connect(self.on_media_error)

        self.setMouseTracking(True)
        self.is_rolling = False
        self.signals = self.RollCallSignals()

        logging.info("RollCallDialog initialized")

    def load_names(self):
        try:
            with open('./data/name.txt', 'r', encoding='utf-8') as file:
                names = [line.strip() for line in file.readlines() if line.strip()]
            logging.info(f"Loaded {len(names)} names from name.txt")
            return names
        except FileNotFoundError:
            logging.error("name.txt not found")
            return []
        except Exception as e:
            logging.error(f"Error loading names: {e}")
            return []

    def save_names(self):
        try:
            with open('./data/name.txt', 'w', encoding='utf-8') as file:
                for name in self.names:
                    file.write(f"{name}\n")
            logging.info("Names saved successfully")
        except Exception as e:
            logging.error(f"Error saving names: {e}")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.is_rolling:
            self.start_roll_call()

    def start_roll_call(self):
        if not self.names:
            self.name_label.setText("没有可用的名字")
            logging.warning("No names available for roll call")
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
                logging.info("Playing roll call video")
            except Exception as e:
                logging.error(f"Video playback error: {e}")
                self.cleanup_media()
                self.display_name()
        else:
            logging.warning(f"Video file not found: {video_path}")
            self.display_name()

    def on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            logging.info("Video playback finished")
            self.cleanup_media()
            self.display_name()
        elif status in (QMediaPlayer.MediaStatus.NoMedia, QMediaPlayer.MediaStatus.InvalidMedia):
            logging.warning("No or invalid media detected")
            self.cleanup_media()
            self.display_name()

    def on_media_error(self, error):
        logging.error(f"Media error: {error}")
        self.cleanup_media()
        self.display_name()

    def cleanup_media(self):
        try:
            self.media_player.stop()
            self.media_player.setSource(QUrl())
            self.video_widget.hide()
            logging.info("Media resources cleaned up")
        except Exception as e:
            logging.error(f"Error cleaning up media: {e}")

    def display_name(self):
        if not self.is_rolling:
            return

        unmarked_names = [name for name in self.names if not name.endswith('*')]
        if not unmarked_names:
            self.names = [name.rstrip('*') for name in self.names]
            self.save_names()
            unmarked_names = self.names
            logging.info("All names were marked, resetting marks")

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
        logging.info(f"Selected and marked name: {selected_name}")

        self.is_rolling = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        new_width = self.width()
        new_height = int(new_width * 9 / 16)
        self.setFixedSize(new_width, new_height)
        if self.video_widget.isVisible():
            self.video_widget.setGeometry(0, 0, new_width, new_height)
            self.video_widget.lower()

    def closeEvent(self, event):
        self.save_names()
        self.cleanup_media()
        self.signals.closed.emit()
        super().closeEvent(event)
        logging.info("RollCallDialog closed")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = RollCallDialog()
    dialog.show()
    sys.exit(app.exec())