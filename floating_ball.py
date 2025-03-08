import os
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPoint, QRect, QSettings
from PyQt6.QtGui import QPainter, QBrush, QColor, QPixmap
from PyQt6.QtWidgets import QApplication
import sys


class FloatingBall(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.ball_size = 32
        self.setFixedSize(self.ball_size, self.ball_size)

        self.png_path = "./icon/ball.png"
        if os.path.exists(self.png_path):
            self.pixmap = QPixmap(self.png_path).scaled(self.ball_size, self.ball_size,
                                                        Qt.AspectRatioMode.KeepAspectRatio,
                                                        Qt.TransformationMode.SmoothTransformation)
            self.use_png = True
        else:
            self.use_png = False

        self.dragging = False
        self.offset = QPoint()

        self.restore_position()
        self.show()
        self.raise_()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(0.6)  # 半透明，范围 0.0 - 1.0
        if self.use_png:
            painter.drawPixmap(0, 0, self.pixmap)
        else:
            painter.setBrush(QBrush(QColor(0, 0, 255)))
            painter.drawEllipse(0, 0, self.ball_size, self.ball_size)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        try:
            if self.dragging:
                global_pos = event.globalPosition().toPoint()
                new_pos = global_pos - self.offset
                self.move(new_pos)
        except Exception:
            pass

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.dragging = False
            self.snap_to_edge()
            self.save_position()
            self.show()
            self.raise_()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pass  # 信号在 MainWindow 中处理

    def snap_to_edge(self):
        screen = QApplication.primaryScreen().availableGeometry()
        current_pos = self.pos()
        left_distance = current_pos.x()
        right_distance = screen.width() - (current_pos.x() + self.ball_size)
        if left_distance < right_distance:
            new_x = 0
        else:
            new_x = screen.width() - self.ball_size
        new_y = max(0, min(current_pos.y(), screen.height() - self.ball_size))
        self.move(new_x, new_y)

    def save_position(self):
        settings = QSettings("Log", "EC")
        settings.setValue("floatingBallPosition", self.pos())

    def restore_position(self):
        settings = QSettings("Log", "EC")
        default_pos = QPoint(100, 100)
        pos = settings.value("floatingBallPosition", default_pos, type=QPoint)
        screen = QApplication.primaryScreen().availableGeometry()
        pos.setX(max(0, min(pos.x(), screen.width() - self.ball_size)))
        pos.setY(max(0, min(pos.y(), screen.height() - self.ball_size)))
        self.move(pos)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ball = FloatingBall()
    ball.show()
    sys.exit(app.exec())