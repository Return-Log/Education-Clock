import random
import time
from PyQt6.QtWidgets import QDialog, QLabel, QToolButton, QVBoxLayout, QPushButton, QApplication
from PyQt6.uic import loadUi
from PyQt6.QtCore import QTimer, Qt, QPropertyAnimation, pyqtProperty, QVariantAnimation, QEasingCurve
from PyQt6.QtGui import QFont

class RollCallDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi('./ui/roll-call.ui', self)  # 加载UI文件
        self.setWindowTitle('随机点名')
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        # 读取名字列表
        self.names = self.load_names()
        self.last_name = None

        # 初始化控件
        self.name_label = self.findChild(QLabel, "name_label")
        self.roll_button = self.findChild(QPushButton, "roll_button")
        if not self.name_label or not self.roll_button:
            raise ValueError("找不到 name_label 或 roll_button，请检查 UI 文件")

        # 设置字体大小
        font = QFont()
        font.setPointSize(90)  # 可以根据需要调整字体大小
        self.name_label.setFont(font)

        # 获取主屏幕的尺寸
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        # 计算窗口在屏幕中心的位置
        window_geometry = self.geometry()
        x = (screen_geometry.width() - window_geometry.width()) // 2
        y = (screen_geometry.height() - window_geometry.height()) // 2
        self.move(x, y)

        # 连接按钮点击事件
        self.roll_button.clicked.connect(self.start_roll_call)

    def load_names(self):
        """从文件中加载名字列表"""
        try:
            with open('./data/name.txt', 'r', encoding='utf-8') as file:
                names = [line.strip() for line in file.readlines()]
            return names
        except FileNotFoundError:
            return []

    def start_roll_call(self):
        """开始点名过程"""
        if not self.names:
            self.name_label.setText("没有可用的名字")
            return

        # 禁用按钮
        self.roll_button.setEnabled(False)

        # 开始滚动
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(1000)  # 持续时间
        self.animation.setStartValue(0)
        self.animation.setEndValue(len(self.names) - 1)
        self.animation.setEasingCurve(QEasingCurve.Type.Linear)  # 线性变化
        self.animation.valueChanged.connect(self.update_name)
        self.animation.finished.connect(self.stop_roll_call)
        self.animation.start()

    def update_name(self, value):
        """更新显示的名字"""
        index = int(value)
        self.name_label.setText(self.names[index])

    def stop_roll_call(self):
        """停止滚动并显示最终结果"""
        available_names = [name for name in self.names if name != self.last_name]
        if not available_names:
            available_names = self.names  # 如果所有名字都被点过，则重置

        selected_name = random.choice(available_names)
        self.name_label.setText(selected_name)
        self.last_name = selected_name
        self.roll_button.setEnabled(True)  # 重新启用按钮