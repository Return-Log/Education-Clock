"""
https://github.com/Return-Log/Education-Clock
GPL-3.0 license
coding: UTF-8
"""

import webbrowser
from PyQt5.QtCore import QTimer, QTime
import pyautogui
import win32com.client
import win32con
import win32gui


class AutoCCTVController:
    def __init__(self):
        self.url = "https://tv.cctv.com/live/index.shtml"
        self.start_time = QTime.fromString("19:00:00", "HH:mm:ss")
        self.end_time = QTime.fromString("19:30:04", "HH:mm:ss")

        self.start_timer = QTimer()
        self.start_timer.timeout.connect(self.check_start_time)
        self.start_timer.start(1000)  # 每秒检查一次开始时间

        self.end_timer = QTimer()
        self.end_timer.timeout.connect(self.check_end_time)

    def open_and_play(self):
        webbrowser.open(self.url)
        QTimer.singleShot(5000, self.maximize_and_play)

    def maximize_and_play(self):
        browser_hwnd = win32gui.GetForegroundWindow()
        placement = win32gui.GetWindowPlacement(browser_hwnd)
        if placement[1] == win32con.SW_SHOWNORMAL:
            win32gui.ShowWindow(browser_hwnd, win32con.SW_MAXIMIZE)

        QTimer.singleShot(800, self.click_center)

    def click_center(self):
        screen_width, screen_height = pyautogui.size()
        center_x, center_y = screen_width / 2, screen_height / 2
        pyautogui.click(center_x, center_y, button='left')
        pyautogui.click(center_x, center_y, button='left')

    def close_browser(self):
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys("^w")

    def check_start_time(self):
        current_time = QTime.currentTime()
        if abs(current_time.secsTo(self.start_time)) <= 1:
            self.open_and_play()
            self.start_timer.stop()
            self.end_timer.start(1000)  # 每秒检查一次结束时间

    def check_end_time(self):
        current_time = QTime.currentTime()
        if abs(current_time.secsTo(self.end_time)) <= 1:
            self.close_browser()
            self.end_timer.stop()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    controller = AutoCCTVController()
    sys.exit(app.exec_())
