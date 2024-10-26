import psutil
import win32gui
import win32con
import win32process
import win32api
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QEvent, QTimer
from PyQt6.QtGui import QWindow
import pywintypes
import subprocess
import time

class ExternalWindowEmbedder:
    def __init__(self, parent_widget, target_exe_path, status_callback, main_window):
        self.parent_widget = parent_widget
        self.target_exe_path = target_exe_path
        self.external_hwnd = None
        self.embedded_window = None
        self.status_callback = status_callback  # 回调函数，用于更新状态
        self.main_window = main_window  # 主窗口的引用
        self.init_ui()

        # 启动exe文件
        self.start_external_process()

        # 使用定时器定期检查窗口是否存在
        self.check_window_timer = QTimer()
        self.check_window_timer.timeout.connect(self.find_and_embed_window_once)
        self.check_window_timer.start(1000)  # 每隔1秒检查一次窗口

    def init_ui(self):
        layout = QVBoxLayout()
        self.parent_widget.setLayout(layout)

    def start_external_process(self):
        try:
            # 启动目标exe文件
            self.process = subprocess.Popen(self.target_exe_path)
            time.sleep(1)  # 确保exe有时间启动
        except Exception as e:
            self.status_callback(f"启动 {self.target_exe_path} 失败: {e}")

    def find_and_embed_window_once(self):
        # 查找目标进程的窗口
        def enum_windows_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid == self.process.pid:
                        self.external_hwnd = hwnd
                        return False  # 停止枚举
                except pywintypes.error as e:
                    self.status_callback(f"无法访问进程窗口: {e}")
            return True

        win32gui.EnumWindows(enum_windows_callback, None)

        if self.external_hwnd:
            self.check_window_timer.stop()  # 停止定时器
            self.embed_window(self.external_hwnd)
        else:
            self.status_callback(f"未找到 {self.target_exe_path} 的窗口")

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

        # 使主窗口成为焦点
        if self.main_window:
            self.main_window.activateWindow()
            self.main_window.raise_()

    def adjust_container_size(self):
        if self.external_hwnd:
            rect = win32gui.GetClientRect(self.external_hwnd)
            self.parent_widget.resize(rect[2], rect[3])

    def restore_window_to_desktop(self, terminate_process=False):
        if self.external_hwnd:
            try:
                # 将窗口设置回正常的顶级窗口样式
                win32gui.SetWindowLong(self.external_hwnd, win32con.GWL_STYLE, win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE)
                # 移除父窗口关联
                win32gui.SetParent(self.external_hwnd, 0)
                # 显示并激活窗口
                win32gui.ShowWindow(self.external_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self.external_hwnd)

                if terminate_process:
                    # 终止exe进程
                    self.process.terminate()
                    self.process.wait()  # 等待进程真正终止
            except Exception as e:
                print(f"恢复窗口或终止进程时出错: {e}")
