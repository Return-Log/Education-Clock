import random
from PyQt6.QtWidgets import QDialog, QLabel, QPushButton, QApplication
from PyQt6.uic import loadUi
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class RollCallDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi('./ui/roll-call.ui', self)  # 加载UI文件
        self.setWindowTitle('随机点名')
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        # 读取名字列表（包含标记）
        self.names = self.load_names()

        # 初始化控件
        self.name_label = self.findChild(QLabel, "name_label")
        self.roll_button = self.findChild(QPushButton, "roll_button")
        if not self.name_label or not self.roll_button:
            raise ValueError("找不到 name_label 或 roll_button，请检查 UI 文件")

        # 设置字体大小
        font = QFont()
        font.setPointSize(90)  # 可以根据需要调整字体大小
        self.name_label.setFont(font)

        # 将窗口居中显示
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.geometry()
        x = (screen_geometry.width() - window_geometry.width()) // 2
        y = (screen_geometry.height() - window_geometry.height()) // 2
        self.move(x, y)

        # 连接按钮点击事件
        self.roll_button.clicked.connect(self.start_roll_call)

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

    def start_roll_call(self):
        """开始点名，直接随机选择未标记的名字"""
        if not self.names:
            self.name_label.setText("没有可用的名字")
            return

        # 获取未标记的名字
        unmarked_names = [name for name in self.names if not name.endswith('*')]

        # 如果没有未标记的名字，重置所有标记
        if not unmarked_names:
            self.names = [name.rstrip('*') for name in self.names]  # 清除所有标记
            self.save_names()  # 保存重置后的列表
            unmarked_names = self.names  # 重置后所有名字都可用

        # 随机选择一个名字
        selected_name = random.choice(unmarked_names)
        self.name_label.setText(selected_name)

        # 在名字后添加标记并更新列表
        for i, name in enumerate(self.names):
            if name == selected_name:
                self.names[i] = f"{name}*"
                break

        # 保存更新后的列表
        self.save_names()

    def closeEvent(self, event):
        """窗口关闭时保存当前名字列表"""
        self.save_names()
        super().closeEvent(event)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    dialog = RollCallDialog()
    dialog.show()
    sys.exit(app.exec())