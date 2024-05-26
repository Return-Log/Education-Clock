import webbrowser  # 导入webbrowser模块，用于在浏览器中打开网页
import schedule  # 导入schedule模块，用于定时执行任务
import time  # 导入time模块，用于时间相关操作
import pyautogui  # 导入pyautogui模块，用于模拟鼠标点击
import win32com.client  # 导入win32com.client模块，用于发送按键操作
import win32con  # 导入win32con模块，用于Windows常量
import win32gui  # 导入win32gui模块，用于窗口操作


class AutoCCTVController:
    def __init__(self):
        self.url = "https://tv.cctv.com/live/index.shtml"  # 央视网直播地址
        self.start_time = "15:55:05"  # 开始播放的时间
        self.end_time = "15:40:05"  # 关闭播放的时间

    def open_and_play(self):
        # 在浏览器中打开央视网直播页面
        webbrowser.open(self.url)
        time.sleep(5)  # 等待页面加载完成

        # 获取浏览器窗口句柄
        browser_hwnd = win32gui.GetForegroundWindow()
        # 将浏览器窗口最大化
        placement = win32gui.GetWindowPlacement(browser_hwnd)
        if placement[1] == win32con.SW_SHOWNORMAL:
            win32gui.ShowWindow(browser_hwnd, win32con.SW_MAXIMIZE)

        time.sleep(0.8)  # 等待窗口最大化完成

        # 获取屏幕尺寸
        screen_width, screen_height = pyautogui.size()
        # 计算屏幕中心坐标
        center_x, center_y = screen_width / 2, screen_height / 2
        # 在屏幕中心模拟鼠标点击，播放视频
        pyautogui.click(center_x, center_y, button='left')
        time.sleep(0.05)
        pyautogui.click(center_x, center_y, button='left')

    def close_browser(self):
        # 发送组合键Ctrl+W，关闭浏览器标签页
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys("^w")

    def job(self):
        # 在指定时间打开并播放直播，同时设置定时任务在结束时间关闭浏览器
        self.open_and_play()
        schedule.every().day.at(self.end_time).do(self.close_browser)

    def start_schedule(self):
        # 设置定时任务，在开始时间执行播放任务
        schedule.every().day.at(self.start_time).do(self.job)
        # 循环执行定时任务
        while True:
            schedule.run_pending()  # 执行待处理的定时任务
            time.sleep(1)  # 每次检查任务之间休眠1秒


# 使用示例
if __name__ == "__main__":
    controller = AutoCCTVController()
    controller.start_schedule()
