import random
import sys
from PySide6.QtWidgets import (QDialog, QLabel, QApplication, QVBoxLayout, QWidget)
from PySide6.QtCore import Qt, QTimer, QRectF, Signal
from PySide6.QtGui import (QPainter, QColor, QFont, QPen, QLinearGradient)

class SlotMachineWidget(QWidget):
    """老虎机风格纵向滚动点名效果"""
    finished = Signal(str)

    def __init__(self, names, selected_name, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self.names = names
        self.selected_name = selected_name.rstrip('*')
        self.clean_names = [n.rstrip('*') for n in self.names]
        try:
            self.target_index = self.clean_names.index(self.selected_name)
        except ValueError:
            self.target_index = 0

        self.total_frames = 180      # 3 秒 @60fps
        self.current_frame = 0
        self.scroll_offset = 0.0
        self.item_height = 80        # 项高度（控制名字大小与间距）
        self.num_names = len(self.clean_names)
        self.laps = 3                # 至少滚动 3 圈
        self.final_offset = self.target_index + self.laps * self.num_names

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)   # ~60fps

    def update_animation(self):
        self.current_frame += 1
        if self.current_frame > self.total_frames:
            self.timer.stop()
            self.update()               # 最后一次重绘，让选中名字变黄
            self.finished.emit(self.selected_name)
            return

        progress = self.current_frame / self.total_frames
        # ease-out 缓出曲线
        eased = 1 - pow(1 - progress, 3)
        self.scroll_offset = eased * self.final_offset
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        center_x = w / 2
        center_y = h / 2

        # 深色背景
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0, QColor(20, 20, 28))
        bg.setColorAt(0.5, QColor(30, 30, 40))
        bg.setColorAt(1, QColor(20, 20, 28))
        painter.fillRect(self.rect(), bg)

        # 中央高亮区域（增强立体感）
        highlight_grad = QLinearGradient(0, center_y - 60, 0, center_y + 60)
        highlight_grad.setColorAt(0, QColor(0, 200, 255, 10))
        highlight_grad.setColorAt(0.5, QColor(0, 230, 255, 25))
        highlight_grad.setColorAt(1, QColor(0, 200, 255, 10))
        painter.setBrush(highlight_grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, center_y - 55, w, 110)

        # 宽的选中框（圆角矩形）
        box_margin = 40
        box_height = self.item_height + 20
        box_rect = QRectF(box_margin, center_y - box_height/2, w - 2*box_margin, box_height)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        box_pen = QPen(QColor(0, 230, 255, 180), 2.5)
        painter.setPen(box_pen)
        painter.drawRoundedRect(box_rect, 12, 12)

        # 绘制滚动中的名字
        offset_px = self.scroll_offset * self.item_height
        # base_y 使得虚拟索引为 scroll_offset 的项刚好位于 center_y
        base_y = center_y - offset_px
        visible_range = int(h / self.item_height) + 4
        base_index_float = self.scroll_offset
        start_index = int(base_index_float) - visible_range
        end_index = int(base_index_float) + visible_range

        stopped = (self.current_frame >= self.total_frames)

        for i in range(start_index, end_index + 1):
            idx = i % self.num_names
            name = self.clean_names[idx]
            y = base_y + i * self.item_height
            dy = y - center_y
            abs_dy = abs(dy)

            max_dy = h * 0.7
            if abs_dy > max_dy:
                continue

            # 缩放与透明度：中间最大，边缘逐渐缩小/淡出
            scale = 1.5 - (abs_dy / max_dy) * 1.0
            scale = max(0.5, scale)
            alpha = 1.0 - abs_dy / max_dy
            alpha = max(0.0, alpha)

            # 颜色：滚动中统一淡蓝白，停止后选中名字变为金色
            if stopped and name == self.selected_name:
                color = QColor(255, 215, 0, int(alpha * 255))
            else:
                color = QColor(220, 220, 255, int(alpha * 255))

            font_family = "Segoe UI, Microsoft YaHei"
            base_font_size = 28
            font_size = int(base_font_size * scale)
            font = QFont(font_family, font_size)
            painter.setFont(font)
            painter.setPen(color)

            fm = painter.fontMetrics()
            text_width = fm.horizontalAdvance(name)
            text_height = fm.height()
            text_rect = QRectF(center_x - text_width/2 - 5,
                               y - text_height/2,
                               text_width + 10,
                               text_height)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, name)

        # 上下边缘渐变遮罩（增强立体纵深）
        top_mask = QLinearGradient(0, 0, 0, 100)
        top_mask.setColorAt(0, QColor(20, 20, 28, 220))
        top_mask.setColorAt(1, QColor(20, 20, 28, 0))
        painter.setBrush(top_mask)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, w, 100)

        bottom_mask = QLinearGradient(0, h - 100, 0, h)
        bottom_mask.setColorAt(0, QColor(20, 20, 28, 0))
        bottom_mask.setColorAt(1, QColor(20, 20, 28, 220))
        painter.setBrush(bottom_mask)
        painter.drawRect(0, h - 100, w, 100)


class Y2KRollCallDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('随机点名')
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(900, 580)
        self.setStyleSheet("background-color: #14141c;")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.current_animation = None
        self.tip_label = QLabel("点击开始随机点名", self)
        self.tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tip_label.setStyleSheet("""
            QLabel {
                color: #00d4ff;
                font-size: 64px;
                letter-spacing: 3px;
            }
        """)
        self.main_layout.addWidget(self.tip_label)

        self.names = self.load_names()
        self.is_rolling = False

    def load_names(self):
        default_names = ["名单为空"]
        try:
            with open('./data/name.txt', 'r', encoding='utf-8') as f:
                names = [line.strip() for line in f if line.strip()]
                # 如果文件存在但内容为空，返回默认列表
                if not names:
                    return default_names
                return names
        except:
            return default_names

    def clear_previous_animation(self):
        if self.current_animation is not None:
            if hasattr(self.current_animation, 'timer') and self.current_animation.timer.isActive():
                self.current_animation.timer.stop()
            self.current_animation.deleteLater()
            self.current_animation = None

    def mousePressEvent(self, event):
        if self.is_rolling or event.button() != Qt.MouseButton.LeftButton:
            return

        self.clear_previous_animation()

        self.is_rolling = True
        self.tip_label.hide()

        unmarked = [n for n in self.names if not n.endswith('*')]
        if not unmarked:
            self.names = [n.rstrip('*') for n in self.names]
            unmarked = self.names

        selected = random.choice(unmarked)

        for i, name in enumerate(self.names):
            if name.rstrip('*') == selected:
                self.names[i] = f"{selected}*"
                break

        self.current_animation = SlotMachineWidget(self.names, selected, self)
        self.current_animation.setGeometry(0, 0, self.width(), self.height())
        self.current_animation.finished.connect(self.on_animation_finished)
        self.main_layout.addWidget(self.current_animation)

    def on_animation_finished(self, name):
        self.is_rolling = False

    def closeEvent(self, event):
        self.clear_previous_animation()
        try:
            with open('./data/name.txt', 'w', encoding='utf-8') as f:
                for name in self.names:
                    f.write(name + '\n')
        except:
            pass
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = Y2KRollCallDialog()
    dialog.show()
    sys.exit(app.exec())