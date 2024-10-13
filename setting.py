import json
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox
from PyQt6.uic import loadUi
from PyQt6.QtCore import pyqtSignal

class SettingsWindow(QMainWindow):
    settings_changed = pyqtSignal()  # 信号用于通知设置已更改

    def __init__(self, parent=None):
        super().__init__(parent)
        # 加载 .ui 文件
        loadUi('./ui/setting.ui', self)  # 替换为实际路径
        self.setWindowTitle("设置")

        # 初始化设置
        self.load_settings()

        # 连接按钮信号与槽
        self.buttonBox.accepted.connect(self.save_settings)
        self.buttonBox.rejected.connect(self.close)
        self.buttonBox_3.accepted.connect(self.save_settings)
        self.buttonBox_3.rejected.connect(self.close)

        # 自动关机模块按钮
        self.buttonBox.button(self.buttonBox.Open).clicked.connect(self.toggle_auto_shutdown_status)
        self.buttonBox.button(self.buttonBox.Close).clicked.connect(self.toggle_auto_shutdown_status)

        # 新闻联播模块按钮
        self.buttonBox_3.button(self.buttonBox_3.Open).clicked.connect(self.toggle_news_broadcast_status)
        self.buttonBox_3.button(self.buttonBox_3.Close).clicked.connect(self.toggle_news_broadcast_status)

    def load_settings(self):
        """加载设置"""
        try:
            with open('data/launch.json', 'r', encoding='utf-8') as file:
                settings = json.load(file)
                self.auto_shutdown_status = settings.get('auto_shutdown_status', False)
                self.news_broadcast_status = settings.get('news_broadcast_status', False)
                self.update_labels()
        except (FileNotFoundError, json.JSONDecodeError):
            self.auto_shutdown_status = False
            self.news_broadcast_status = False
            self.update_labels()

    def save_settings(self):
        """保存设置"""
        settings = {
            'auto_shutdown_status': self.auto_shutdown_status,
            'news_broadcast_status': self.news_broadcast_status
        }
        with open('data/launch.json', 'w', encoding='utf-8') as file:
            json.dump(settings, file, ensure_ascii=False, indent=4)
        self.settings_changed.emit()  # 发送设置已更改的信号
        self.close()

    def update_labels(self):
        """更新标签显示内容"""
        self.label_4.setText('打开' if self.auto_shutdown_status else '关闭')
        self.label_2.setText('打开' if self.news_broadcast_status else '关闭')

    def toggle_auto_shutdown_status(self):
        """切换自动关机模块状态"""
        self.auto_shutdown_status = not self.auto_shutdown_status
        self.update_labels()

    def toggle_news_broadcast_status(self):
        """切换新闻联播模块状态"""
        self.news_broadcast_status = not self.news_broadcast_status
        self.update_labels()

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = loadUi('./ui/setting.ui')
    window.show()
    sys.exit(app.exec())