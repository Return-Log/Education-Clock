import logging
import os
import sys
import requests
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QLabel, QWidget, QToolButton, QTextEdit, QLabel, \
    QTextBrowser, QDialog
from PyQt6.uic import loadUi
from PyQt6.QtCore import QTimer, Qt, QUrl, pyqtSignal, QSharedMemory
from PyQt6.QtGui import QDesktopServices, QIcon, QPixmap
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QSettings
from datetime import datetime
import json
from timetable_module import TimetableModule
from auto_cctv_controller import AutoCCTVController  # 导入自动新闻联播模块
from shutdown_module import ShutdownModule  # 导入关机模块
from time_module import TimeModule  # 导入时间模块
from weather_module import WeatherModule
from settings_window import SettingsWindow  # 导入设置窗口类
from bulletin_board_module import BulletinBoardModule  # 导入公告板模块
from API_display_module import APIDisplayModule

def main():
    app = QApplication(sys.argv)

    # 使用 QSharedMemory 来确保只有一个实例运行
    shared_memory = QSharedMemory("Education-Clock-Unique-ID")
    if not shared_memory.create(1):
        # 如果已经存在
        msg_box = QMessageBox()
        msg_box.setWindowTitle("提示")
        msg_box.setText("该程序已经在运行中。")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()
        sys.exit(0)

    window = MainWindow()
    qss_path = window.get_qss_path()

    try:
        with open(qss_path, 'r', encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        window.show_message(f"Failed to load QSS file: {e}")

    window.show()
    sys.exit(app.exec())


class MainWindow(QMainWindow):
    # 自定义刷新信号
    refresh_timetable_signal = pyqtSignal()
    refresh_weather_signal = pyqtSignal()
    refresh_news_signal = pyqtSignal()
    refresh_shutdown_signal = pyqtSignal()
    refresh_bulletin_signal = pyqtSignal()
    refresh_api_display_signal = pyqtSignal()
    refresh_time_signal = pyqtSignal()
    def __init__(self):
        super().__init__()
        # 加载 .ui 文件
        loadUi('./ui/mainwindow.ui', self)  # 替换为实际路径

        # 连接信号到对应的刷新方法
        self.refresh_timetable_signal.connect(self.refresh_timetable)
        self.refresh_weather_signal.connect(self.refresh_weather)
        self.refresh_news_signal.connect(self.refresh_news)
        self.refresh_shutdown_signal.connect(self.refresh_shutdown)
        self.refresh_bulletin_signal.connect(self.refresh_bulletin)
        self.refresh_api_display_signal.connect(self.refresh_api_display)
        self.refresh_time_signal.connect(self.refresh_time)

        # 初始化各个模块
        self.init_modules()

        # 设置定时器每分钟更新一次
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timetable)
        self.timer.start(60000)  # 每分钟更新

        # 初始更新
        self.update_timetable()

        # 调用 setup_weather_module 方法并添加调试信息
        self.setup_weather_module()

        # 启动定时器以每分钟检查一次设置
        self.settings_timer = QTimer(self)
        self.settings_timer.timeout.connect(self.check_settings)
        self.settings_timer.start(60000)  # 每分钟检查一次设置

        # 初始化时间模块
        self.time_module = TimeModule(self)

        self.api_display_module = APIDisplayModule(self)


        # 保存和恢复窗口大小和位置
        self.restore_window_geometry()

        # 连接 toolButton_3 到打开设置窗口的方法
        self.toolButton_3.clicked.connect(self.open_settings_window)

        # 初始化悬浮球模块
        self.init_floating_ball()

        # 初始化公告板模块
        self.init_bulletin_board_module()

        # 移除窗口边框
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        # 固定窗口位置和大小
        self.fix_window_position_and_size()

        # 将窗口置于最下层
        self.lower()

        self.github_tags = None


        # 找到 label_update 控件
        self.label_update = self.findChild(QLabel, "label_update")
        if self.label_update is None:
            raise ValueError("找不到 label_update，请检查 UI 文件")

        # 启动检查更新
        self.check_for_updates()

    def refresh_timetable(self):
        """刷新课表模块"""
        # 清理旧的课表模块
        if hasattr(self, 'timetable_module') and self.timetable_module is not None:
            # 确保清理旧模块的UI组件
            if self.timetable_module.scroll_area:
                self.timetable_module.scroll_area.setParent(None)
                self.timetable_module.scroll_area.deleteLater()

        # 创建新的课表模块
        self.timetable_module = TimetableModule(self)
        self.update_timetable()

    def refresh_time(self):
        self.time_module = TimeModule(self)
        logging.info("更新时间模块")

    def refresh_weather(self):
        """刷新天气模块"""
        widget_2 = self.findChild(QWidget, "widget_2")
        if widget_2 is not None:
            self.weather_module = WeatherModule(widget_2)
            layout = QVBoxLayout()
            layout.addWidget(self.weather_module)
            widget_2.setLayout(layout)
        else:
            self.show_message("找不到 widget_2，请检查 UI 文件")

    def refresh_news(self):
        """刷新自动新闻模块"""
        self.load_settings()
        self.init_news_module()

    def refresh_shutdown(self):
        """刷新关机模块"""
        self.load_settings()
        self.init_shutdown_module()

    def refresh_bulletin(self):
        """刷新公告板模块"""
        try:
            # 清理旧的公告板模块（如果存在）
            if hasattr(self, 'bulletin_board_module') and self.bulletin_board_module is not None:
                try:
                    logging.info("清理旧的公告板模块")
                    self.bulletin_board_module.cleanup()
                except Exception as e:
                    logging.error(f"清理旧公告板模块时出错: {e}")
                finally:
                    # 确保引用被清除
                    self.bulletin_board_module = None

            text_edit = self.findChild(QTextBrowser, "textBrowser")
            if text_edit is not None:
                try:
                    logging.info("初始化新的公告板模块")
                    self.bulletin_board_module = BulletinBoardModule(self, text_edit)
                    logging.info("公告板模块初始化完成")
                except Exception as e:
                    logging.error(f"初始化公告板模块时出错: {e}", exc_info=True)
                    # 在文本浏览器中显示错误信息
                    try:
                        text_edit.setHtml("<p style='color: red; text-align: center;'>公告板模块初始化失败</p>")
                    except:
                        pass
                    self.show_message(f"公告板模块初始化失败: {str(e)}")
            else:
                error_msg = "找不到 textBrowser，请检查 UI 文件"
                self.show_message(error_msg)
                logging.error(error_msg)
        except Exception as e:
            logging.error(f"刷新公告板模块时发生未预期的错误: {e}", exc_info=True)
            self.show_message(f"刷新公告板模块失败: {str(e)}")

    def refresh_api_display(self):
        if hasattr(self, 'api_display_module') and self.api_display_module is not None:
            self.api_display_module.update()
        else:
            self.show_message("API 显示模块未初始化")

    def init_floating_ball(self):
        """初始化悬浮球"""
        from floating_ball import FloatingBall
        self.floating_ball = FloatingBall()  # 无父窗口


    def closeEvent(self, event):
        """在窗口关闭时清理独立窗口"""
        settings = QSettings("Log", "EC")
        settings.setValue("windowGeometry", self.saveGeometry())
        settings.setValue("windowPosition", self.pos())
        if hasattr(self, 'floating_ball'):
            self.floating_ball.close()
        if hasattr(self, 'roll_call_dialog'):
            self.roll_call_dialog.close()
        event.accept()

    def fix_window_position_and_size(self):
        # 获取屏幕的尺寸
        screen = QApplication.primaryScreen().geometry()
        screen_width = screen.width()
        screen_height = screen.height()

        # 获取任务栏的高度
        taskbar_height = self.get_taskbar_height()

        # 确保任务栏高度合理
        if taskbar_height >= screen_height:
            taskbar_height = 25  # 使用默认任务栏高度

        # 计算窗口的宽度和高度
        window_width = min(screen_width // 3, screen_width)  # 确保不超过屏幕宽度
        window_height = min(screen_height - taskbar_height, screen_height)  # 确保不超过屏幕高度

        # 确保窗口高度不为负数
        if window_height <= 0:
            window_height = screen_height - 25  # 使用默认任务栏高度

        # 计算窗口的位置
        window_x = screen_width - window_width
        window_y = 0

        # 设置窗口的位置和大小
        self.setGeometry(window_x, window_y, window_width, window_height)

    def get_taskbar_height(self):
        """获取任务栏的高度"""
        screen = QApplication.primaryScreen()
        available_geometry = screen.availableGeometry()
        screen_geometry = screen.geometry()

        # 获取屏幕的高度
        screen_height = screen_geometry.height()

        # 获取任务栏的高度
        taskbar_height = screen_height - available_geometry.height()

        return taskbar_height

    def show_message(self, message):
        # 创建 QMessageBox
        msg_box = QMessageBox(self)
        msg_box.setText(message)
        msg_box.setWindowTitle("提示")
        msg_box.setIcon(QMessageBox.Icon.Information)

        # 显示消息框并设置自动关闭
        msg_box.show()
        QTimer.singleShot(2000, msg_box.close)  # 2秒后关闭消息框

    def status_callback(self, message):
        # 使用 show_message 方法显示消息
        self.show_message(message)

    def init_modules(self):
        self.timetable_module = TimetableModule(self)
        self.shutdown_module = None
        self.cctv_controller = None
        self.plan_tasks_module = None
        self.load_settings()  # 确保设置已加载
        self.init_shutdown_module()  # 在设置加载后初始化关机模块
        self.init_news_module()
        self.init_plan_tasks_module()

    def update_timetable(self):
        current_time = datetime.now().time()
        self.timetable_module.update_timetable(current_time)

    def load_settings(self):
        """加载设置"""
        try:
            with open('data/launch.json', 'r', encoding='utf-8') as file:
                settings = json.load(file)
                self.shutdown_status = settings.get('shutdown', '关闭')
                self.news_status = settings.get('news', '关闭')
        except (FileNotFoundError, json.JSONDecodeError):
            self.shutdown_status = '关闭'
            self.news_status = '关闭'

    def check_settings(self):
        """检查设置并更新状态"""
        self.load_settings()

    def init_plan_tasks_module(self):
        """初始化计划任务模块"""
        try:
            from plan_tasks_module import PlanTasksModule
            tab_widget = self.findChild(QWidget, "tabWidget")  # 根据实际UI结构调整
            if tab_widget:
                self.plan_tasks_module = PlanTasksModule(self)
                tab_widget.addTab(self.plan_tasks_module, "计划任务")

            else:
                logging.warning("未找到tabWidget")
        except Exception as e:
            logging.error(f"初始化计划任务模块出错: {e}")

    def refresh_plan_tasks(self):
        """刷新计划任务模块"""
        if self.plan_tasks_module:
            self.plan_tasks_module.refresh()

    def init_news_module(self):
        """根据设置初始化新闻联播模块"""
        if self.news_status == '开启':
            if not hasattr(self, 'cctv_controller') or self.cctv_controller is None:
                self.cctv_controller = AutoCCTVController()  # 确保初始化时自动启动定时器
        elif self.news_status == '关闭' and hasattr(self, 'cctv_controller'):
            if self.cctv_controller is not None:
                self.cctv_controller.stop_timers()
            del self.cctv_controller

    def init_shutdown_module(self):
        """根据设置初始化关机模块"""
        if self.shutdown_status == '开启':
            if not hasattr(self, 'shutdown_module') or self.shutdown_module is None:
                self.shutdown_module = ShutdownModule(self)  # 传递 self 作为父窗口引用
        elif self.shutdown_status == '关闭' and hasattr(self, 'shutdown_module'):
            if self.shutdown_module is not None:
                self.shutdown_module.stop()  # 确保 self.shutdown_module 不是 None
            del self.shutdown_module
            self.shutdown_module = None  # 清除引用

    def setup_weather_module(self):
        widget_2 = self.findChild(QWidget, "widget_2")
        if widget_2 is not None:
            self.weather_module = WeatherModule(widget_2)
            layout = QVBoxLayout()
            layout.addWidget(self.weather_module)
            widget_2.setLayout(layout)
        else:
            self.show_message("找不到 widget_2，请检查 UI 文件")

    def restore_window_geometry(self):
        """恢复窗口大小和位置"""
        settings = QSettings("Log", "EC")

        # 恢复窗口几何信息
        geometry = settings.value("windowGeometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # 如果没有保存的几何信息，使用默认值
            default_width = 400
            default_height = 600
            self.resize(default_width, default_height)

        # 恢复窗口位置
        position = settings.value("windowPosition")
        if position:
            self.move(position)
        else:
            # 如果没有保存的位置信息，使用默认值
            default_x = 100
            default_y = 100
            self.move(default_x, default_y)

    def closeEvent(self, event):
        """在窗口关闭时清理独立窗口"""
        settings = QSettings("Log", "EC")
        settings.setValue("windowGeometry", self.saveGeometry())
        settings.setValue("windowPosition", self.pos())
        if hasattr(self, 'floating_ball'):
            self.floating_ball.close()
        if hasattr(self, 'roll_call_dialog'):
            self.roll_call_dialog.close()
        if hasattr(self, 'ranking_module'):  # 添加这部分
            self.ranking_module.stop()
        event.accept()

    def open_settings_window(self):
        settings_window = SettingsWindow(self)

        # 安全地尝试断开旧连接（仅当存在该属性）
        if hasattr(settings_window, 'refresh_signal'):
            try:
                settings_window.refresh_signal.disconnect()
            except TypeError:
                pass

            settings_window.refresh_signal.connect(self.handle_module_refresh)

        if settings_window.exec() == QDialog.DialogCode.Accepted:
            pass

    def handle_module_refresh(self, module_name: str):
        QTimer.singleShot(0, lambda: self.emit_specific_signal(module_name))

    def emit_specific_signal(self, module_name: str):
        if module_name == "timetable":
            self.refresh_timetable_signal.emit()
        elif module_name == "weather":
            self.refresh_weather_signal.emit()
        elif module_name == "news":
            self.refresh_news_signal.emit()
        elif module_name == "shutdown":
            self.refresh_shutdown_signal.emit()
        elif module_name == "bulletin":
            self.refresh_bulletin_signal.emit()
        elif module_name == "api_display":
            self.refresh_api_display_signal.emit()
        elif module_name == "time":
            self.refresh_time_signal.emit()
        elif module_name == "plan_tasks":
            self.refresh_plan_tasks()


    def init_bulletin_board_module(self):
        try:
            # 清理旧的公告板模块（如果存在）
            if hasattr(self, 'bulletin_board_module') and self.bulletin_board_module is not None:
                try:
                    logging.info("清理旧的公告板模块（初始化时）")
                    self.bulletin_board_module.cleanup()
                except Exception as e:
                    logging.error(f"清理旧公告板模块时出错: {e}")
                finally:
                    self.bulletin_board_module = None

            text_edit = self.findChild(QTextBrowser, "textBrowser")
            if text_edit is not None:
                try:
                    logging.info("初始化公告板模块")
                    self.bulletin_board_module = BulletinBoardModule(self, text_edit)
                    logging.info("公告板模块初始化完成")
                except Exception as e:
                    logging.error(f"初始化公告板模块时出错: {e}", exc_info=True)
                    # 在文本浏览器中显示错误信息
                    try:
                        text_edit.setHtml("<p style='color: red; text-align: center;'>公告板模块初始化失败</p>")
                    except:
                        pass
                    self.show_message(f"公告板模块初始化失败: {str(e)}")
            else:
                error_msg = "找不到 textBrowser，请检查 UI 文件"
                self.show_message(error_msg)
                logging.error(error_msg)
        except Exception as e:
            logging.error(f"初始化公告板模块时发生未预期的错误: {e}", exc_info=True)
            self.show_message(f"初始化公告板模块失败: {str(e)}")

    def check_for_updates(self):
        """检测最新版本并更新状态"""
        self.links = [
            '<a href="https://github.com/Return-Log/Education-Clock/releases/latest" style="color: red;">检测到新版本 {latest_tag}, 当前版本 {current_version}</a>',
        ]
        self.current_link_index = 0
        self.github_tags = None
        self.current_version = "v5.2"

        try:
            response = requests.get('https://api.github.com/repos/Return-Log/Education-Clock/tags', timeout=5)
            response.raise_for_status()
            self.github_tags = response.json()  # 缓存结果
        except requests.RequestException:
            self.label_update.setText("无法检测更新")
            return

        if self.github_tags:
            latest_tag = self.github_tags[0]['name']
            if latest_tag != self.current_version:
                self.label_update.setText(
                    self.links[self.current_link_index].format(latest_tag=latest_tag,
                                                               current_version=self.current_version)
                )
            else:
                self.label_update.setText(
                    f'<a href="https://github.com/Return-Log/Education-Clock/releases/latest" style="color: green;">已是最新版 {latest_tag}</a>')
            self.label_update.setOpenExternalLinks(True)
        else:
            self.label_update.setText("无法检测更新")

        # 设置定时器，每隔 5 秒更新一次链接（不调用 API）
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_link)
        self.update_timer.start(5000)

    def update_link(self):
        """更新标签中的链接（仅使用已缓存的 tags 数据）"""
        if not self.github_tags:
            self.label_update.setText("无法检测更新")
            return

        latest_tag = self.github_tags[0]['name']
        if latest_tag != self.current_version:
            self.label_update.setText(
                self.links[self.current_link_index].format(latest_tag=latest_tag,
                                                           current_version=self.current_version)
            )
            self.label_update.setOpenExternalLinks(True)
            self.current_link_index = (self.current_link_index + 1) % len(self.links)

    def get_qss_path(self):
        default_qss = './ui/qss/Dark.qss'
        qss_txt_path = './data/qss.txt'

        if not os.path.exists(qss_txt_path):
            return default_qss

        try:
            with open(qss_txt_path, 'r', encoding='utf-8') as f:
                qss_file = f.read().strip()
                if not qss_file:
                    return default_qss
                qss_path = os.path.join('./ui/qss', qss_file)
                if os.path.exists(qss_path):
                    return qss_path
                else:
                    self.show_message(f"QSS file {qss_file} does not exist, using default.")
                    return default_qss
        except Exception as e:
            self.show_message(f"Error reading qss.txt: {e}, using default.")
            return default_qss

if __name__ == "__main__":
    main()