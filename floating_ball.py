import os
import sys
import logging
from PyQt6.QtWidgets import QWidget, QMenu, QApplication
from PyQt6.QtCore import Qt, QPoint, QSettings
from PyQt6.QtGui import QPainter, QBrush, QColor, QPixmap
from roll_call_module import RollCallDialog
from timer_module import TimerApp

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

class FloatingBall(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.active_windows = []  # 用于跟踪打开的窗口，防止垃圾回收

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.ball_size = 32
        self.setFixedSize(self.ball_size, self.ball_size)

        self.png_path = "./icon/ball.png"
        self.pixmap = QPixmap(self.png_path).scaled(self.ball_size, self.ball_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation) if os.path.exists(self.png_path) else None
        self.use_png = bool(self.pixmap)

        self.dragging = False
        self.offset = QPoint()
        self.click_pos = QPoint()
        self.click_threshold = 5

        self.restore_position()
        self.show()
        self.raise_()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(0.6)
        if self.use_png:
            painter.drawPixmap(0, 0, self.pixmap)
        else:
            painter.setBrush(QBrush(QColor(0, 0, 255)))
            painter.drawEllipse(0, 0, self.ball_size, self.ball_size)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.offset = event.pos()
            self.click_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        try:
            global_pos = event.globalPosition().toPoint()
            if not self.dragging and (global_pos - self.click_pos).manhattanLength() > self.click_threshold:
                self.dragging = True
            if self.dragging:
                self.move(global_pos - self.offset)
        except Exception as e:
            logging.error(f"Mouse move error: {e}")

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.dragging:
                self.show_menu(event.globalPosition().toPoint())
            else:
                self.dragging = False
                self.snap_to_edge()
                self.save_position()
            self.raise_()

    def show_menu(self, position):
        menu = QMenu(self)
        menu.addAction("随机点名", self.roll_call_module)
        menu.addAction("计时器", self.timer_module)
        menu.exec(position)

    def roll_call_module(self):
        """直接运行 RollCallDialog"""
        logging.info("Running Random Roll Call")
        try:
            dialog = RollCallDialog()
            dialog.show()  # 显示对话框，不启动新的事件循环
            self.active_windows.append(dialog)  # 防止垃圾回收
            logging.info("RollCallDialog opened")
        except Exception as e:
            logging.error(f"Error running RollCallDialog: {e}")

    def timer_module(self):
        """运行 TimerApp"""
        logging.info("Running TimerApp")
        try:
            timer_app = TimerApp()
            timer_app.show()
            self.active_windows.append(timer_app)  # 防止垃圾回收
            logging.info("TimerApp opened")
        except Exception as e:
            logging.error(f"Error running TimerApp: {e}")

    def snap_to_edge(self):
        screen = QApplication.primaryScreen().availableGeometry()
        pos = self.pos()
        new_x = 0 if pos.x() < screen.width() - (pos.x() + self.ball_size) else screen.width() - self.ball_size
        new_y = max(0, min(pos.y(), screen.height() - self.ball_size))
        self.move(new_x, new_y)

    def save_position(self):
        QSettings("Log", "EC").setValue("floatingBallPosition", self.pos())

    def restore_position(self):
        settings = QSettings("Log", "EC")
        pos = settings.value("floatingBallPosition", QPoint(100, 100), type=QPoint)
        screen = QApplication.primaryScreen().availableGeometry()
        pos.setX(max(0, min(pos.x(), screen.width() - self.ball_size)))
        pos.setY(max(0, min(pos.y(), screen.height() - self.ball_size)))
        self.move(pos)

    def closeEvent(self, event):
        """关闭时清理所有打开的窗口"""
        for window in self.active_windows:
            window.close()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ball = FloatingBall()
    sys.exit(app.exec())