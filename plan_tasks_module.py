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
        current_weekday = current_date.strftime("%A")  # 获取当前星期几的英文名
        display_messages = []

        # 处理预约消息
        appointment_messages = self.config.get("appointment_message", {})
        for message_key, message_data in appointment_messages.items():
            try:
                # 检查是否是新的多时间点格式
                schedules = []
                if "schedules" in message_data and isinstance(message_data["schedules"], list):
                    # 新格式：多个时间点
                    schedules = message_data["schedules"]
                else:
                    # 兼容旧格式：单个时间点
                    schedules = [message_data]

                # 遍历所有时间点
                for schedule in schedules:
                    time_value = schedule.get("time", "")
                    if not time_value:
                        continue

                    # 支持多种日期格式，用逗号分隔
                    time_values = [t.strip().replace("，", ",") for t in time_value.split(",")]
                    matched = False

                    for time_val in time_values:
                        time_val = time_val.strip()
                        # 检查是否是星期几
                        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                        weekdays_chinese = {
                            "Monday": "星期一", "Tuesday": "星期二", "Wednesday": "星期三",
                            "Thursday": "星期四", "Friday": "星期五", "Saturday": "星期六", "Sunday": "星期日"
                        }

                        if time_val in weekdays or time_val in weekdays_chinese.values():
                            # 如果是星期几，检查是否匹配今天
                            weekday_match = (time_val == current_weekday or
                                             time_val == weekdays_chinese.get(current_weekday, ""))
                            if weekday_match:
                                matched = True
                                break

                        else:
                            # 检查是否为日期格式
                            try:
                                # 尝试解析 YYYY-MM-DD 格式
                                message_date = datetime.strptime(time_val, "%Y-%m-%d").date()
                                if message_date == current_date:
                                    matched = True
                                    break
                            except ValueError:
                                try:
                                    # 尝试解析 MM-DD 格式
                                    message_date = datetime.strptime(time_val, "%m-%d").date()
                                    if message_date.month == current_date.month and message_date.day == current_date.day:
                                        matched = True
                                        break
                                except ValueError:
                                    logging.warning(f"无效的日期格式: {time_val}")
                                    continue

                    if matched:
                        remind_time_str = schedule.get("remind_time", "")
                        if remind_time_str:
                            remind_time = datetime.strptime(remind_time_str, "%H:%M").time()
                            # 检查是否到达提醒时间
                            if self.is_time_just_passed(remind_time, current_time):
                                # 播放提示音并显示弹幕
                                self.play_sound_and_danmaku(schedule.get("message", ""))

                        # 添加到显示列表
                        text = schedule.get("text", "")
                        if text:
                            display_messages.append(f"*预约通知 {time_value}*\n{text}\n---")

            except Exception as e:
                logging.error(f"处理预约消息出错: {e}")

        # 处理循环消息（保持原有逻辑）
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
                    remain_time_str = current_message_data.get("remain_time", "")
                    if remain_time_str:
                        remain_time = datetime.strptime(remain_time_str, "%H:%M").time()
                        # 检查是否到达提醒时间
                        if self.is_time_just_passed(remain_time, current_time):
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
            # 处理中文逗号
            suspension_date = suspension_date.strip().replace("，", ",")
            # 支持逗号分隔的多个日期
            date_parts = [d.strip() for d in suspension_date.split(",")]

            for date_part in date_parts:
                # 检查是否为星期几 (Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday)
                weekdays = {
                    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
                    "Friday": 4, "Saturday": 5, "Sunday": 6
                }
                weekdays_chinese = {
                    "星期一": 0, "星期二": 1, "星期三": 2, "星期四": 3,
                    "星期五": 4, "星期六": 5, "星期日": 6
                }

                if date_part in weekdays:
                    if current_date.weekday() == weekdays[date_part]:
                        return True
                elif date_part in weekdays_chinese:
                    if current_date.weekday() == weekdays_chinese[date_part]:
                        return True
                else:
                    try:
                        # 检查是否为特定日期格式 YYYY-MM-DD
                        suspended_date = datetime.strptime(date_part, "%Y-%m-%d").date()
                        if suspended_date == current_date:
                            return True
                    except ValueError:
                        try:
                            # 检查是否为 MM-DD 格式
                            suspended_date = datetime.strptime(date_part, "%m-%d").date()
                            if suspended_date.month == current_date.month and suspended_date.day == current_date.day:
                                return True
                        except ValueError:
                            # 不是有效的日期格式，跳过
                            logging.warning(f"无效的暂停日期格式: {date_part}")
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