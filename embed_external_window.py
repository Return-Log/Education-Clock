import win32gui
import win32con
import win32process
import win32api
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QWindow, QScreen
import pywintypes

class ExternalWindowEmbedder:
    def __init__(self, parent_widget, target_exe_name, status_callback):
        self.parent_widget = parent_widget
        self.target_exe_name = target_exe_name.lower()
        self.external_hwnd = None
        self.embedded_window = None
        self.status_callback = status_callback  # 回调函数，用于更新状态
        self.init_ui()

    def init_ui(self):
        # 创建一个垂直布局
        layout = QVBoxLayout()
        self.parent_widget.setLayout(layout)

    def find_and_embed_window(self):
        # 查找目标进程
        def enum_windows_callback(hwnd, lparam):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    h_process = win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                    exe_name = win32process.GetModuleFileNameEx(h_process, 0).lower()
                    if self.target_exe_name in exe_name:
                        self.external_hwnd = hwnd
                        return False  # 停止枚举
                except pywintypes.error as e:
                    self.status_callback(f"无法访问进程: {e}")
            return True

        win32gui.EnumWindows(enum_windows_callback, None)

        if self.external_hwnd:
            self.embed_window(self.external_hwnd)
        else:
            self.status_callback(f"未找到 {self.target_exe_name} 的窗口")

    def embed_window(self, hwnd):
        # 获取外部窗口的句柄
        external_window = QWindow.fromWinId(hwnd)
        external_window.setFlags(Qt.WindowType.FramelessWindowHint)

        # 创建一个 QWidget 容器来嵌入外部窗口
        container = QWidget.createWindowContainer(external_window, self.parent_widget)
        self.parent_widget.layout().addWidget(container)

        # 调整容器大小以适应外部窗口
        self.adjust_container_size()

        # 设置外部窗口为子窗口
        win32gui.SetParent(hwnd, int(self.parent_widget.winId()))
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, win32con.WS_CHILD | win32con.WS_VISIBLE)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

    def adjust_container_size(self):
        if self.external_hwnd:
            rect = win32gui.GetClientRect(self.external_hwnd)
            self.parent_widget.resize(rect[2], rect[3])

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Resize:
            self.adjust_container_size()
        return super().eventFilter(obj, event)