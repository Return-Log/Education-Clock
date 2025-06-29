import logging
import os
import sys
from datetime import datetime
import requests
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QToolTip
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal, QThread

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QMouseEvent

class ClickableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)  # 启用鼠标追踪以便接收鼠标事件

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # 手动显示 ToolTip
            QToolTip.showText(event.globalPosition().toPoint(), self.toolTip(), self)


class RealTimeWorker(QObject):
    """实时天气数据获取工作线程"""
    data_ready = pyqtSignal(dict)       # 数据就绪信号
    error_occurred = pyqtSignal(str)    # 错误发生信号

    def __init__(self, api_key, location):
        super().__init__()
        self.api_key = api_key
        self.lat, self.lon = location  # 从配置加载的经纬度

    def fetch(self):
        """执行实时天气数据获取"""
        try:
            url = f"https://devapi.qweather.com/v7/weather/now?location={self.lon},{self.lat}&key={self.api_key}&lang=zh"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '200':
                    self.data_ready.emit(data)
                else:
                    self.error_occurred.emit(f"API错误码: {data.get('code')}")
            else:
                self.error_occurred.emit(f"HTTP错误: {response.status_code}")
        except Exception as e:
            self.error_occurred.emit(f"请求异常: {str(e)}")

class ForecastWorker(QObject):
    """天气预报数据获取工作线程"""
    data_ready = pyqtSignal(dict)       # 数据就绪信号
    error_occurred = pyqtSignal(str)    # 错误发生信号

    def __init__(self, api_key, location):
        super().__init__()
        self.api_key = api_key
        self.lat, self.lon = location  # 从配置加载的经纬度

    def fetch(self):
        """执行天气预报数据获取"""
        try:
            url = f"https://devapi.qweather.com/v7/weather/3d?location={self.lon},{self.lat}&key={self.api_key}&lang=zh"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '200':
                    self.data_ready.emit(data)
                else:
                    self.error_occurred.emit(f"API错误码: {data.get('code')}")
            else:
                self.error_occurred.emit(f"HTTP错误: {response.status_code}")
        except Exception as e:
            self.error_occurred.emit(f"请求异常: {str(e)}")

class WeatherModule(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_key = self.load_api_key()    # 加载API密钥
        self.location = self.load_location()  # 加载地理位置
        self.init_ui()
        self.init_workers()  # 初始化工作线程
        self.setup_timers()  # 设置定时器
        self.trigger_initial_update()  # 触发初始更新

    def init_ui(self):
        """初始化用户界面"""
        # 实时天气标签
        self.real_time_weather_label = ClickableLabel(self)
        self.real_time_weather_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.real_time_weather_label.setProperty("weather", "now")
        self.real_time_weather_label.setContentsMargins(0, 0, 0, 0)

        # 天气预报标签
        self.forecast_weather_label = ClickableLabel(self)
        self.forecast_weather_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.forecast_weather_label.setProperty("weather", "next")
        self.forecast_weather_label.setContentsMargins(0, 0, 0, 0)

        # 布局设置
        layout = QVBoxLayout()
        layout.addWidget(self.real_time_weather_label)
        layout.addWidget(self.forecast_weather_label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def init_workers(self):
        """初始化工作线程"""
        # 实时天气工作线程
        self.real_time_worker = RealTimeWorker(self.api_key, self.location)
        self.real_time_thread = QThread()
        self.real_time_worker.moveToThread(self.real_time_thread)
        self.real_time_worker.data_ready.connect(self.handle_real_time_data)
        self.real_time_worker.error_occurred.connect(self.handle_real_time_error)
        self.real_time_thread.start()

        # 天气预报工作线程
        self.forecast_worker = ForecastWorker(self.api_key, self.location)
        self.forecast_thread = QThread()
        self.forecast_worker.moveToThread(self.forecast_thread)
        self.forecast_worker.data_ready.connect(self.handle_forecast_data)
        self.forecast_worker.error_occurred.connect(self.handle_forecast_error)
        self.forecast_thread.start()

    def setup_timers(self):
        """设置定时触发器"""
        # 实时天气定时器（16分钟）
        self.real_time_timer = QTimer(self)
        self.real_time_timer.timeout.connect(self.real_time_worker.fetch)
        self.real_time_timer.start(960000)

        # 天气预报定时器（2小时）
        self.forecast_timer = QTimer(self)
        self.forecast_timer.timeout.connect(self.forecast_worker.fetch)
        self.forecast_timer.start(7200000)

    def trigger_initial_update(self):
        """触发初始数据更新"""
        QTimer.singleShot(0, self.real_time_worker.fetch)
        QTimer.singleShot(0, self.forecast_worker.fetch)

    def load_api_key(self):
        """加载天气API密钥"""
        try:
            with open('data/weather.txt', 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            self.display_error("缺少weather.txt文件")
            return None

    def load_location(self):
        """加载地理位置信息"""
        try:
            with open('data/location.txt', 'r', encoding='utf-8') as f:
                return f.read().strip().split(',')
        except FileNotFoundError:
            self.display_error("缺少location.txt文件")
            return None

    def get_wind_description(self, speed_mps):
        """根据风速(m/s)返回风力等级和描述"""
        if speed_mps < 0.3:
            return "0级无风"
        elif speed_mps < 1.6:
            return "1级软风"
        elif speed_mps < 3.4:
            return "2级轻风"
        elif speed_mps < 5.5:
            return "3级微风"
        elif speed_mps < 8.0:
            return "4级和风"
        elif speed_mps < 10.8:
            return "5级清风"
        elif speed_mps < 13.9:
            return "6级强风"
        elif speed_mps < 17.2:
            return "7级劲风"
        elif speed_mps < 20.8:
            return "8级大风"
        elif speed_mps < 24.5:
            return "9级烈风"
        elif speed_mps < 28.5:
            return "10级狂风"
        elif speed_mps < 32.7:
            return "11级暴风"
        elif speed_mps < 36.9:
            return "一级飓风"
        elif speed_mps < 41.4:
            return "一级飓风"
        elif speed_mps < 46.1:
            return "二级飓风"
        elif speed_mps < 50.9:
            return "三级飓风"
        elif speed_mps < 56.0:
            return "三级飓风"
        else:
            return "四级飓风"

    def handle_real_time_data(self, data):
        """处理实时天气数据"""
        try:
            now = data['now']
            wind_speed_kmh = float(now['windSpeed'])  # 确保是浮点数
            wind_speed_mps = round(wind_speed_kmh / 3.6, 1)  # 转换为 m/s，保留一位小数
            wind_desc = self.get_wind_description(wind_speed_mps)

            real_time_text = (
                f"当前: {now['text']}\n"
                f"温度: {now['temp']}°C 体感: {now['feelsLike']}°C\n"
                f"湿度: {now['humidity']}%\n"
                f"风速: {wind_speed_mps} m/s ({wind_desc})"
            )
            self.real_time_weather_label.setText(real_time_text)
        except KeyError as e:
            self.handle_real_time_error(f"数据解析失败")

    def handle_forecast_data(self, data):
        """处理天气预报数据"""
        try:
            today = data['daily'][0]
            tomorrow = data['daily'][1]
            forecast_text = (
                f"今: {today['textDay']}, {today['tempMax']}至{today['tempMin']}°C\n"
                f"明: {tomorrow['textDay']}, {tomorrow['tempMax']}至{tomorrow['tempMin']}°C"
            )
            self.forecast_weather_label.setText(forecast_text)
        except (KeyError, IndexError) as e:
            self.handle_forecast_error(f"数据解析失败: {str(e)}")


    def handle_real_time_error(self, error_msg):
        """处理实时天气错误"""
        full_msg = f"实时天气错误: {error_msg}"
        self.real_time_weather_label.setToolTip(full_msg)
        self.real_time_weather_label.setText("实时天气错误")

    def handle_forecast_error(self, error_msg):
        """处理天气预报错误"""
        full_msg = f"天气预报错误: {error_msg}"
        self.forecast_weather_label.setToolTip(full_msg)
        self.forecast_weather_label.setText("天气预报错误")

    def display_error(self, error_msg):
        """显示通用错误信息"""
        full_msg = f"错误: {error_msg}"
        self.real_time_weather_label.setToolTip(full_msg)
        self.real_time_weather_label.setText("错误")
        self.forecast_weather_label.setToolTip(full_msg)
        self.forecast_weather_label.setText("错误")

    def closeEvent(self, event):
        """窗口关闭时停止所有线程"""
        self.real_time_thread.quit()
        self.real_time_thread.wait()
        self.forecast_thread.quit()
        self.forecast_thread.wait()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WeatherModule()
    window.show()
    sys.exit(app.exec())