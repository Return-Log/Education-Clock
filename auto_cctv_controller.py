# auto_cctv_controller.py
import webbrowser
from PyQt6.QtCore import QTimer, QTime
import pyautogui
import win32com.client
import win32con
import win32gui
import pyaudio



class AutoCCTVController:
    def __init__(self):
        """
        初始化AutoCCTVController类。
        设置直播URL和直播的开始/结束时间。
        初始化QTimer，每秒检查当前时间是否与开始/结束时间匹配。
        """
        self.url = "https://tv.cctv.com/live/index.shtml"
        self.start_time = QTime.fromString("19:00:00", "HH:mm:ss")
        self.end_time = QTime.fromString("19:30:04", "HH:mm:ss")

        # 初始化用于检测开始时间的定时器
        self.start_timer = QTimer()
        self.start_timer.timeout.connect(self.check_start_time)
        self.start_timer.start(1000)  # 每秒检查一次开始时间

        # 初始化用于检测结束时间的定时器
        self.end_timer = QTimer()
        self.end_timer.timeout.connect(self.check_end_time)

    def open_and_play(self):
        """
        打开默认浏览器并加载直播URL。
        检测到音频输出后，最大化浏览器并全屏播放视频。
        """
        webbrowser.open(self.url)
        self.start_audio_check()

    def start_audio_check(self):
        """
        启动音频输出检测。每2秒检测一次音频输出。
        """
        self.audio_check_timer = QTimer()
        self.audio_check_timer.timeout.connect(self.check_audio_output)
        self.audio_check_timer.start(2000)  # 每2秒检测一次音频输出

    def maximize_and_fullscreen(self):
        """
        最大化当前浏览器窗口并模拟双击屏幕中央以全屏播放直播。
        """
        # 获取当前前台窗口的句柄
        browser_hwnd = win32gui.GetForegroundWindow()
        placement = win32gui.GetWindowPlacement(browser_hwnd)

        # 如果窗口没有最大化，则最大化
        if placement[1] == win32con.SW_SHOWNORMAL:
            win32gui.ShowWindow(browser_hwnd, win32con.SW_MAXIMIZE)

        # 模拟双击屏幕中央以进入全屏播放
        screen_width, screen_height = pyautogui.size()
        center_x, center_y = screen_width / 2, screen_height / 2
        pyautogui.doubleClick(center_x, center_y, button='left')

    def check_audio_output(self):
        """
        检查系统是否有音频输出，判断直播是否开始播放。
        检测到音频输出后，停止定时器并执行最大化及全屏操作。
        """
        p = pyaudio.PyAudio()
        audio_output_detected = False

        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            # print(f"检测到设备: {device_info['name']}")

            # 如果设备有音频输出通道
            if device_info['maxOutputChannels'] > 0:
                # print("检测到音频输出设备")
                audio_output_detected = True
                break

        # 如果检测到音频输出，执行全屏操作
        if audio_output_detected:
            # print("音频输出已检测到，执行全屏操作")
            self.audio_check_timer.stop()  # 停止音频检查定时器
            QTimer.singleShot(1000, self.maximize_and_fullscreen)  # 等待一秒执行最大化和全屏播放

    def close_browser(self):
        """
        通过Alt+F4关闭当前的浏览器窗口。
        """
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys("%{F4}")

    def check_start_time(self):
        """
        检查当前时间是否达到了设定的开始时间。如果时间匹配，则启动直播。
        """
        current_time = QTime.currentTime()
        if abs(current_time.secsTo(self.start_time)) <= 1:
            self.open_and_play()
            self.start_timer.stop()
            self.end_timer.start(1000)  # 每秒检查一次结束时间

    def check_end_time(self):
        """
        检查当前时间是否达到了设定的结束时间。如果时间匹配，则关闭浏览器。
        """
        current_time = QTime.currentTime()
        if abs(current_time.secsTo(self.end_time)) <= 1:
            self.close_browser()
            self.end_timer.stop()

    def stop_timers(self):
        """
        停止所有的定时器。
        """
        self.start_timer.stop()
        self.end_timer.stop()
        if hasattr(self, 'audio_check_timer'):
            self.audio_check_timer.stop()