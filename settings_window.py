from PyQt6.QtWidgets import QDialog, QPushButton, QLabel, QFileDialog, QTextBrowser, QTabWidget
from PyQt6.uic import loadUi
from PyQt6.QtCore import QTimer

class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        # 加载 setting.ui 文件
        loadUi('./ui/setting.ui', self)

        # 初始化时读取 data/exe.txt 并更新 label_5
        self.load_exe_path()

        # 设置 textBrowser 样式
        self.textBrowser.setStyleSheet("background-color: black; color: green; font-family: 'Courier New', Courier, monospace;")

        # 连接 tab_6 的激活事件
        self.tabWidget.currentChanged.connect(self.on_tab_changed)

    def connect_signals(self):
        # 连接 pushButton 的点击事件到 open_file_dialog 方法
        self.pushButton.clicked.connect(self.open_file_dialog)

    def open_file_dialog(self):
        # 打开文件对话框，只允许选择 .exe 文件
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择可执行文件", "", "Executable Files (*.exe)"
        )
        if file_path:
            # 保存路径到 data/exe.txt
            with open('data/exe.txt', 'w', encoding='utf-8') as file:
                file.write(file_path)
            # 更新 label_5 显示路径
            self.label_5.setText(file_path)

    def load_exe_path(self):
        # 读取 data/exe.txt 文件内容
        try:
            with open('data/exe.txt', 'r', encoding='utf-8') as file:
                exe_path = file.read().strip()
                if exe_path:
                    # 如果文件不为空，更新 label_5 显示路径
                    self.label_5.setText(exe_path)
                else:
                    # 如果文件为空，显示默认文本
                    self.label_5.setText("未选择文件")
        except FileNotFoundError:
            # 如果文件不存在，显示默认文本
            self.label_5.setText("未选择文件")

    def on_tab_changed(self, index):
        # 当切换到 tab_6 时开始流式输出
        if index == 6:  # 假设 tab_6 的索引是 6
            self.init_streaming_text()

    def init_streaming_text(self):
        # 清空 textBrowser
        self.textBrowser.clear()

        # 添加软件信息
        software_info = [
            """                               
  ______    _                 _   _             
 |  ____|  | |               | | (_)            
 | |__   __| |_   _  ___ __ _| |_ _  ___  _ __  
 |  __| / _` | | | |/ __/ _` | __| |/ _ \| '_ \ 
 | |___| (_| | |_| | (_| (_| | |_| | (_) | | | |
 |______\__,_|\__,_|\___\__,_|\__|_|\___/|_| |_|
           / ____| |          | |               
          | |    | | ___   ___| | __            
          | |    | |/ _ \ / __| |/ /            
          | |____| | (_) | (__|   <             
           \_____|_|\___/ \___|_|\_\                     
           """,
            "欢迎使用本软件！",
            "版本: 3.1",
            "更新日志: ",
            " - 嵌入窗口程序可由程序启动不再需要设置自启动",
            " - 修复自动新闻联播没有运行问题",
            " - 设置窗口初步实现",
            " - 界面美化",
            "作者: Return-Log",
            "日期: 2024/10/27",
            "项目仓库: https://github.com/Return-Log/Education-Clock",
            "本软件遵循CPL-3.0协议发布",
            "============================================",
            "Copyright © 2024  Log  All rights reserved.",

        ]

        # 将软件信息转换为包含换行符的字符串
        software_info_str = "\n".join(software_info) + "\n"
        self.add_text_line(software_info_str, delay=10)  # 每个字符之间的延迟

    def add_text_line(self, text, delay=10):
        self.target_text = text
        self.character_delay = delay
        self.current_index = 0
        self.print_next_character()

    def print_next_character(self):
        if self.current_index < len(self.target_text):
            current_char = self.target_text[self.current_index]
            cursor = self.textBrowser.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(current_char)
            self.textBrowser.setTextCursor(cursor)
            self.current_index += 1
            QTimer.singleShot(self.character_delay, self.print_next_character)

# 主程序入口
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    # 加载 QSS 文件
    with open('data/qss.qss', 'r', encoding="utf-8") as f:
        app.setStyleSheet(f.read())
    window = SettingsWindow()
    window.show()
    sys.exit(app.exec())