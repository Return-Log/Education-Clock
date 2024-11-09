from PyQt6.QtWidgets import QDialog, QPushButton, QLabel, QFileDialog, QTextBrowser, QTabWidget
from PyQt6.uic import loadUi
from PyQt6.QtCore import QTimer

class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        # 加载 setting.ui 文件
        loadUi('./ui/setting.ui', self)

        # 设置 textBrowser 样式
        self.textBrowser.setStyleSheet("background-color: black; color: green; font-family: 'Courier New', Courier, monospace;")

        # 连接 tab_6 的激活事件
        self.tabWidget.currentChanged.connect(self.on_tab_changed)


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
            "版本: 3.2",
            "更新日志: ",
            " - 取消嵌入窗口，改为通知栏",
            " - 使用钉钉机器人和远程服务器实现消息更新",
            " - 增加运行稳定性",
            " - 界面美化",
            "作者: Return-Log",
            "日期: 2024/11/3",
            "项目仓库: https://github.com/Return-Log/Education-Clock",
            "本软件遵循CPL-3.0协议发布",
            "============================================",
            "Copyright © 2024  Log  All rights reserved.",

        ]

        # 将软件信息转换为包含换行符的字符串
        software_info_str = "\n".join(software_info) + "\n"
        self.add_text_line(software_info_str, delay=2)  # 每个字符之间的延迟


    def add_text_line(self, text, delay=2):
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
        else:
            cursor = self.textBrowser.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertHtml(
                "<br><a href='https://github.com/Return-Log/Education-Clock' style='color:green;'>GitHub仓库</a>")
            self.textBrowser.setTextCursor(cursor)

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