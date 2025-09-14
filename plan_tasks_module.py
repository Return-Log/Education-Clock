import json
import os
import logging
from datetime import datetime, time
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtCore import QUrl
from markdown import markdown
from bulletin_board_module import DanmakuWindow  # 使用已有的弹幕窗口


class PlanTasksModule(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.config_file = 'data/message_config.json'
        self.sound_effect = QSoundEffect()

        try:
            self.sound_effect.setSource(QUrl.fromLocalFile("icon/newmessage.wav"))
        except Exception as e:
            logging.warning(f"无法加载提示音: {e}")

        self.setup_ui()
        self.load_config()
        self.setup_timers()

    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(False)
        layout.addWidget(self.text_browser)

    def load_config(self):
        """加载消息配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = {"appointment_message": {}, "loop_message": {}}
                logging.warning(f"配置文件 {self.config_file} 不存在")
        except Exception as e:
            logging.error(f"加载配置文件出错: {e}")
            self.config = {"appointment_message": {}, "loop_message": {}}

    def setup_timers(self):
        """设置定时器检查消息"""
        # 每分钟检查一次
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_messages)
        self.timer.start(60000)  # 每分钟检查一次

        # 立即检查一次
        self.check_messages()

    def check_messages(self):
        """检查并处理消息"""
        self.load_config()
        current_date = datetime.now().date()
        current_time = datetime.now().time()
        display_messages = []

        # 处理预约消息
        appointment_messages = self.config.get("appointment_message", {})
        for date_str, message_data in appointment_messages.items():
            try:
                message_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if message_date == current_date:
                    remind_time_str = message_data.get("remind_time", "")
                    if remind_time_str:
                        remind_time = datetime.strptime(remind_time_str, "%H:%M").time()
                        # 检查是否到达提醒时间
                        if self.is_time_just_passed(remind_time, current_time):
                            # 播放提示音并显示弹幕
                            self.play_sound_and_danmaku(message_data.get("message", ""))

                    # 添加到显示列表
                    text = message_data.get("text", "")
                    if text:
                        display_messages.append(f"*预约通知 {date_str}*\n{text}\n---")
            except Exception as e:
                logging.error(f"处理预约消息出错: {e}")

        # 处理循环消息
        loop_messages = self.config.get("loop_message", {})
        config_changed = False  # 标记配置是否发生变化

        for list_key, list_data in loop_messages.items():
            try:
                suspension_dates = list_data.get("suspension_date", [])
                # 检查是否在暂停日期中
                if self.is_suspended(current_date, suspension_dates):
                    continue

                text_data = list_data.get("text", {})
                id_now = text_data.get("id_now", "")
                date_now = text_data.get("date_now", "")

                # 如果是新的一天，更新id_now
                if date_now != str(current_date):
                    # 获取所有可用的文本项键名（排除id_now和date_now）
                    available_keys = [k for k in text_data.keys()
                                      if isinstance(text_data[k], dict) and k not in ["id_now", "date_now"]]
                    if available_keys:
                        # 简单循环选择下一个key
                        if id_now in available_keys:
                            current_index = available_keys.index(id_now)
                            next_index = (current_index + 1) % len(available_keys)
                        else:
                            next_index = 0
                        id_now = available_keys[next_index]

                        # 更新配置文件中的id_now和date_now
                        text_data["id_now"] = id_now
                        text_data["date_now"] = str(current_date)
                        config_changed = True

                # 显示当前key的消息
                if id_now and id_now in text_data:
                    current_message_data = text_data[id_now]
                    remind_time_str = current_message_data.get("remain_time", "")
                    if remind_time_str:
                        remind_time = datetime.strptime(remind_time_str, "%H:%M").time()
                        # 检查是否到达提醒时间
                        if self.is_time_just_passed(remind_time, current_time):
                            # 播放提示音并显示弹幕
                            self.play_sound_and_danmaku(current_message_data.get("message", ""))

                    # 添加到显示列表
                    text = current_message_data.get("text", "")
                    if text:
                        display_messages.append(f"*循环通知 {list_key}*\n{text}\n---")

            except Exception as e:
                logging.error(f"处理循环消息出错: {e}")

        # 如果配置发生变化，保存更新后的配置
        if config_changed:
            self.save_config()

        # 更新显示
        if display_messages:
            html_content = ""
            for msg in display_messages:
                html_content += markdown(msg) + "\n"
            self.text_browser.setHtml(html_content)
        else:
            self.text_browser.setHtml("<p style='text-align: center; color: gray;'>暂无计划消息</p>")

    def is_time_just_passed(self, target_time, current_time):
        """检查是否刚刚到达目标时间（过去1分钟内）"""
        # 创建完整的datetime对象用于比较
        dummy_date = datetime(2000, 1, 1)
        target_datetime = datetime.combine(dummy_date, target_time)
        current_datetime = datetime.combine(dummy_date, current_time)

        # 如果当前时间刚好在目标时间之后的一分钟内
        time_diff = current_datetime - target_datetime
        return 0 <= time_diff.total_seconds() <= 60

    def is_suspended(self, current_date, suspension_dates):
        """检查当前日期是否在暂停日期中"""
        for suspension_date in suspension_dates:
            # 检查是否为星期几 (Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday)
            weekdays = {
                "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
                "Friday": 4, "Saturday": 5, "Sunday": 6
            }

            if suspension_date in weekdays:
                if current_date.weekday() == weekdays[suspension_date]:
                    return True
            else:
                try:
                    # 检查是否为特定日期格式 YYYY-MM-DD
                    suspended_date = datetime.strptime(suspension_date, "%Y-%m-%d").date()
                    if suspended_date == current_date:
                        return True
                except ValueError:
                    # 不是有效的日期格式，跳过
                    logging.warning(f"无效的暂停日期格式: {suspension_date}")
                    continue
        return False

    def play_sound_and_danmaku(self, message):
        """播放提示音并显示弹幕"""
        try:
            # 播放提示音
            self.sound_effect.play()
            logging.info("播放计划任务提示音")

            # 显示弹幕
            if message:
                # 使用与公告板模块相同的弹幕窗口类
                # 确保弹幕窗口有正确的父级关系
                danmaku_window = DanmakuWindow([message], self.main_window)
                danmaku_window.show()
                danmaku_window.raise_()  # 确保窗口在最前面
                danmaku_window.activateWindow()  # 激活窗口
                logging.info(f"显示计划任务弹幕: {message}")
        except Exception as e:
            logging.error(f"播放提示音或显示弹幕出错: {e}", exc_info=True)

    def save_config(self):
        """保存配置文件"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"保存配置文件出错: {e}")

    def refresh(self):
        """刷新模块"""
        self.check_messages()
