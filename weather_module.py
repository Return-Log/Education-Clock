import logging
import os
import sys
from datetime import datetime
import requests
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer

class WeatherModule(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_key = self.load_api_key()  # 加载天气 API 密钥
        self.location = self.load_location()  # 加载手动存储的坐标
        self.init_ui()

        # 定时器：实时天气每16分钟更新，天气预报每1小时更新
        self.real_time_weather_timer = QTimer(self)
        self.real_time_weather_timer.timeout.connect(self.update_real_time_weather)
        self.real_time_weather_timer.start(960000)  # 16分钟

        self.forecast_weather_timer = QTimer(self)
        self.forecast_weather_timer.timeout.connect(self.update_forecast_weather)
        self.forecast_weather_timer.start(3600000)  # 1小时

        # 初始获取天气信息
        self.update_real_time_weather()
        self.update_forecast_weather()

    def load_api_key(self):
        # 从文件中加载 API 密钥
        try:
            with open('data/weather.txt', 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            self.display_error("找不到 weather.txt 文件")
            return None

    def load_location(self):
        # 从文件中加载手动存储的坐标
        try:
            with open('data/location.txt', 'r', encoding='utf-8') as f:
                return f.read().strip().split(',')  # 读取经纬度
        except FileNotFoundError:
            self.display_error("找不到 location.txt 文件")
            return None

    def init_ui(self):
        # 实时天气和预报天气标签
        self.real_time_weather_label = QLabel(self)
        self.real_time_weather_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.real_time_weather_label.setProperty("weather", "now")  # 设置样式属性
        self.real_time_weather_label.setContentsMargins(0, 0, 0, 0)  # 设置边距为1像素

        self.forecast_weather_label = QLabel(self)
        self.forecast_weather_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.forecast_weather_label.setProperty("weather", "next")  # 设置样式属性
        self.forecast_weather_label.setContentsMargins(0, 0, 0, 0)  # 设置边距为1像素

        layout = QVBoxLayout()
        layout.addWidget(self.real_time_weather_label)
        layout.addWidget(self.forecast_weather_label)
        self.setLayout(layout)

        # 设置 layout 的边距为 1 像素
        layout.setContentsMargins(0, 0, 0, 0)


    def display_error(self, error_message):
        self.real_time_weather_label.setText(f"错误: {error_message}")
        self.forecast_weather_label.setText(f"错误: {error_message}")

    def update_real_time_weather(self):
        if not self.api_key or not self.location:
            return

        lat, lon = self.location

        try:
            # 请求和风天气实时天气 API
            weather_url = f"https://devapi.qweather.com/v7/weather/now?location={lon},{lat}&key={self.api_key}&lang=zh"
            response = requests.get(weather_url)

            if response.status_code == 200:
                weather_data = response.json()
                self.parse_real_time_weather_data(weather_data)
            else:
                self.display_error(f"获取实时天气信息失败")
        except requests.RequestException as e:
            self.display_error(f"网络请求失败")

    def update_forecast_weather(self):
        if not self.api_key or not self.location:
            return

        lat, lon = self.location

        try:
            # 请求和风天气3天预报 API
            forecast_url = f"https://devapi.qweather.com/v7/weather/3d?location={lon},{lat}&key={self.api_key}&lang=zh"
            response = requests.get(forecast_url)

            if response.status_code == 200:
                forecast_data = response.json()
                self.parse_forecast_weather_data(forecast_data)
            else:
                self.display_error(f"获取天气预报信息失败")
        except requests.RequestException as e:
            self.display_error(f"网络请求失败")

    def parse_real_time_weather_data(self, data):
        try:
            if data['code'] != '200':
                self.display_error(f"错误代码: {data['code']}")
                return

            now = data['now']
            temp = now['temp']  # 当前温度
            feels_like = now['feelsLike']  # 体感温度
            wind_dir = now['windDir']  # 风向
            wind_speed = now['windSpeed']  # 风速
            humidity = now['humidity']  # 湿度
            text = now['text']  # 天气描述

            real_time_text = f"当前: {text}\n温度: {temp}°C 体感: {feels_like}°C\n湿度: {humidity}%\n风速: {wind_speed} km/h"
            self.real_time_weather_label.setText(real_time_text)

        except KeyError:
            self.display_error("解析实时天气数据失败")

    def parse_forecast_weather_data(self, data):
        try:
            if data['code'] != '200':
                self.display_error(f"错误代码: {data['code']}")
                return

            forecast_today = data['daily'][0]
            forecast_tomorrow = data['daily'][1]

            today_weather = f"今: {forecast_today['textDay']}, {forecast_today['tempMax']}至{forecast_today['tempMin']}°C"
            tomorrow_weather = f"明: {forecast_tomorrow['textDay']}, {forecast_tomorrow['tempMax']}至{forecast_tomorrow['tempMin']}°C"

            forecast_text = f"{today_weather}\n{tomorrow_weather}"
            self.forecast_weather_label.setText(forecast_text)

        except KeyError:
            self.display_error("解析天气预报数据失败")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WeatherModule()
    window.show()
    sys.exit(app.exec())