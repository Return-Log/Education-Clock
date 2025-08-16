import json
from PyQt6.QtWidgets import QLabel, QMainWindow, QScrollArea, QWidget, QVBoxLayout, QSizePolicy
from datetime import time, datetime, timedelta
from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtGui import QTextDocument, QPainter, QFontMetrics

class ScrollingLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._x = 0.0
        self.paused = False
        self.subject_doc = QTextDocument(self)
        self.time_doc = QTextDocument(self)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._scroll)
        self.speed = 20  # pixels per second
        self.gap = 20  # gap for smoother scrolling
        self.setWordWrap(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subject_text = ""
        self.time_text = ""
        self.subject_width = 0

    def setText(self, subject_text, time_text=""):
        self.subject_text = subject_text
        self.time_text = time_text

        # Set up subject document
        self.subject_doc.setHtml(self.subject_text)
        self.subject_doc.setUseDesignMetrics(True)
        self.subject_doc.setTextWidth(-1)
        self.subject_width = self.subject_doc.idealWidth()

        # Set up time document
        self.time_doc.setHtml(f"<span style='font-size: 12px;'>{self.time_text}</span>")
        self.time_doc.setUseDesignMetrics(True)
        self.time_doc.setTextWidth(-1)

        self._x = 0.0
        if self.timer.isActive():
            self.timer.stop()

        # Start scrolling only if subject text is too wide
        if self.subject_width > self.width() and self.width() > 0:
            self._x = float(self.width())
            self.timer.start(1000 // self.speed)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.subject_text:
            self.setText(self.subject_text, self.time_text)

    def _scroll(self):
        if not self.paused:
            self._x -= 1.0
            if self._x < -(self.subject_width + self.gap):
                self._x += self.subject_width + self.gap
        self.update()

    def enterEvent(self, event: QEvent):
        self.paused = True
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        self.paused = False
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.subject_doc.toPlainText():
            return

        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)

        # 添加内边距，避免文字紧贴边缘
        padding = 5
        content_rect = self.rect().adjusted(padding, padding, -padding, -padding)

        # 计算总高度和垂直偏移
        total_height = self.subject_doc.size().height() + (self.time_doc.size().height() if self.time_text else 0)
        # 减小课程和时间之间的间距
        spacing = -9  # 从默认间距减小到2像素
        total_height_with_spacing = self.subject_doc.size().height() + spacing + (
            self.time_doc.size().height() if self.time_text else 0)
        y_offset = (content_rect.height() - total_height_with_spacing) / 2 + padding

        # 绘制课程文本
        if self.subject_width <= content_rect.width():
            # 课程文本居中显示（考虑内边距）
            x_offset = (content_rect.width() - self.subject_width) / 2 + padding
            painter.translate(x_offset, y_offset)
            self.subject_doc.drawContents(painter)
            painter.translate(-x_offset, -y_offset)
        else:
            # 滚动课程文本
            x_offset = padding
            painter.translate(self._x + x_offset, y_offset)
            self.subject_doc.drawContents(painter)
            painter.translate(self.subject_width + self.gap, 0)
            self.subject_doc.drawContents(painter)
            painter.translate(-self._x - x_offset - (self.subject_width + self.gap), -y_offset)

        # 绘制时间文本（始终居中且静态）
        if self.time_text:
            time_y_offset = y_offset + self.subject_doc.size().height() + spacing
            time_x_offset = (content_rect.width() - self.time_doc.idealWidth()) / 2 + padding
            painter.translate(time_x_offset, time_y_offset)
            self.time_doc.drawContents(painter)

class TimetableModule:
    def __init__(self, main_window: QMainWindow):
        self.timetable = None
        self.main_window = main_window
        self.layout = main_window.verticalLayout_2
        self.comboBox = main_window.comboBox
        self.labels = []
        self.scroll_area = None  # Initialize scroll_area as None
        self.load_timetable()
        self.setup_ui()

        # 设置焦点策略以支持鼠标滚轮滚动
        self.scroll_area.setFocusPolicy(Qt.FocusPolicy.WheelFocus)
        self.scroll_area.setMouseTracking(True)

        # Connect comboBox signal
        self.comboBox.currentIndexChanged.connect(self.on_combobox_changed)

        # Set up timer for updates
        self.timer = QTimer(self.main_window)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.on_timer_timeout)

        self.update_timetable(datetime.now().time())

    def setup_mouse_scroll(self):
        """设置鼠标拖动滚动功能"""
        self.scroll_area.setMouseTracking(True)
        self.scroll_widget.mousePressEvent = self.mouse_press_event
        self.scroll_widget.mouseMoveEvent = self.mouse_move_event
        self.scroll_widget.mouseReleaseEvent = self.mouse_release_event
        self.drag_start_pos = None

    def mouse_press_event(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()

    def mouse_move_event(self, event):
        if self.drag_start_pos is not None:
            delta = self.drag_start_pos - event.pos()
            self.scroll_area.verticalScrollBar().setValue(
                self.scroll_area.verticalScrollBar().value() + delta.y()
            )
            self.drag_start_pos = event.pos()

    def mouse_release_event(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = None

    def load_timetable(self):
        with open('data/timetable.json', 'r', encoding='utf-8') as file:
            self.timetable = json.load(file)

    def setup_ui(self):
        # Remove any existing scroll_area from the layout
        if self.scroll_area is not None:
            self.layout.removeWidget(self.scroll_area)
            self.scroll_area.setParent(None)  # 断开父级关系
            self.scroll_area.deleteLater()
            self.scroll_area = None

        # Create scroll area
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        # 减小布局中控件之间的间距
        self.scroll_layout.setSpacing(2)  # 设置较小的间距使布局更紧凑
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # 隐藏垂直滚动条
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)  # 移除边框

        # 启用鼠标拖动滚动
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Move comboBox to bottom
        self.layout.removeWidget(self.comboBox)
        self.layout.insertWidget(0, self.scroll_area)
        self.layout.addWidget(self.comboBox)
        self.setup_mouse_scroll()

    def on_combobox_changed(self):
        index = self.comboBox.currentIndex()
        self.update_timetable(datetime.now().time(), index)

    def on_timer_timeout(self):
        self.update_timetable(datetime.now().time())

    def clear_layout(self):
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.labels.clear()

    def add_label(self, subject, start_str, end_str, is_intime):
        combined_label = ScrollingLabel()
        subject_text = f"<b><span style='font-size: 24px;'>{subject}</span></b>"
        time_text = f"{start_str} - {end_str}"
        combined_label.setText(subject_text, time_text)
        combined_label.setProperty("timetable", "intime" if is_intime else "untimely")
        # 添加内边距样式，避免文字紧贴边缘
        combined_label.setStyleSheet(combined_label.styleSheet() + "; padding: 5px;")
        self.scroll_layout.addWidget(combined_label)
        self.labels.append(combined_label)

    def schedule_next_update(self, current_time: time, selected_day_name: str):
        days = ["无调休", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        current_weekday = days[datetime.now().weekday() + 1]
        if selected_day_name != current_weekday:
            return

        boundaries = set()
        if selected_day_name in self.timetable:
            for entry in self.timetable[selected_day_name]:
                start = time.fromisoformat(entry[1])
                end = time.fromisoformat(entry[2])
                boundaries.add(start)
                boundaries.add(end)

        if not boundaries:
            return

        boundaries = sorted(list(boundaries))
        next_times = [t for t in boundaries if t > current_time]

        if next_times:
            next_t = next_times[0]
            now_dt = datetime.combine(datetime.today(), current_time)
            next_dt = datetime.combine(datetime.today(), next_t)
            delta = next_dt - now_dt
        else:
            next_dt = datetime.combine(datetime.today() + timedelta(days=1), time(0, 0, 0))
            now_dt = datetime.combine(datetime.today(), current_time)
            delta = next_dt - now_dt

        ms = int(delta.total_seconds() * 1000)
        self.timer.start(max(ms, 1))

    def update_timetable(self, current_time: time, selected_day_index: int = None):
        self.clear_layout()
        days = ["无调休", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        if selected_day_index is None:
            selected_day_index = self.comboBox.currentIndex()

        if selected_day_index >= 0 and selected_day_index < len(days):
            selected_day_name = days[selected_day_index]
        else:
            selected_day_name = days[0]

        if selected_day_name == "无调休":
            selected_day_name = days[datetime.now().weekday() + 1]

        if selected_day_name in self.timetable:
            for entry in self.timetable[selected_day_name]:
                subject, start_str, end_str = entry
                start = time.fromisoformat(start_str)
                end = time.fromisoformat(end_str)
                is_intime = start <= current_time < end
                self.add_label(subject, start_str, end_str, is_intime)

        self.schedule_next_update(current_time, selected_day_name)

        self.scroll_widget.update()
        self.scroll_widget.repaint()
        self.scroll_area.update()
        self.scroll_area.repaint()