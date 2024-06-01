"""
https://github.com/Return-Log/Education-Clock
GPL-3.0 license
coding: UTF-8
"""

import sys
from datetime import datetime
import requests
from PyQt5.QtCore import Qt, QTimer, QPoint, QSettings, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QDialog, QLineEdit, QMessageBox
from PyQt5.QtWidgets import QWidget, QVBoxLayout


class WeatherThread(QThread):
    weather_data_fetched = pyqtSignal(dict)

    def __init__(self, api_key, latitude, longitude):
        super().__init__()
        self.api_key = api_key
        self.latitude = latitude
        self.longitude = longitude

    def run(self):
        url = f"http://api.openweathermap.org/data/2.5/forecast?lat={self.latitude}&lon={self.longitude}&appid={self.api_key}"
        response = requests.get(url)
        data = response.json()
        self.weather_data_fetched.emit(data)


class WeatherApp(QWidget):
    def __init__(self):
        super().__init__()
        self.api_key = self.load_api_key()  # 加载 OpenWeather API 密钥
        self.latitude, self.longitude = self.load_location()  # 加载位置信息
        self.setStyleSheet("background-color: black; color: white;")  # 设置窗口样式
        self.init_ui()  # 初始化用户界面
        self.restore_settings()  # 恢复窗口位置设置

    # 加载 OpenWeather API 密钥
    def load_api_key(self):
        with open("data/OpenWeather-API.txt", "r") as file:
            return file.read().strip()

    # 加载位置信息
    def load_location(self):
        with open("data/location.txt", "r") as file:
            location = file.read().strip()
            latitude, longitude = location.split(',')
            return float(latitude), float(longitude)

    # 初始化用户界面
    def init_ui(self):
        self.setWindowTitle("天气预报")
        self.setWindowFlags(Qt.FramelessWindowHint)  # 设置窗口无边框
        layout = QVBoxLayout()

        # 第一行显示当前天气温度天气描述及风速，红色
        self.current_weather_label = QLabel("当前天气", self)
        self.current_weather_label.setFont(QFont("Arial", 24))
        self.current_weather_label.setStyleSheet("color: red")
        layout.addWidget(self.current_weather_label)

        # 第三行显示未来5天每天天气，黄色
        self.future_5_days_label = QLabel("未来5天天气", self)
        self.future_5_days_label.setFont(QFont("Arial", 12))
        self.future_5_days_label.setStyleSheet("color: yellow")
        layout.addWidget(self.future_5_days_label)

        # 最后一行显示更新时间，绿色
        self.update_time_label = QLabel("更新时间：", self)
        self.update_time_label.setFont(QFont("Arial", 12))
        self.update_time_label.setStyleSheet("color: green")
        layout.addWidget(self.update_time_label)

        self.setLayout(layout)
        self.show()

        # 双击窗口弹出设置窗口
        self.mouseDoubleClickEvent = self.open_location_dialog

        # 启动时自动刷新天气
        self.start_weather_thread()

        # 定时器，每隔 5分钟刷新一次
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.start_weather_thread)
        self.timer.start(300000)  # 5分钟 * 60秒 * 1000毫秒

    # 双击窗口弹出设置窗口
    def open_location_dialog(self, event):
        location_dialog = LocationDialog(self)
        location_dialog.exec_()

    def closeEvent(self, event):
        self.save_settings()
        event.accept()

    def save_settings(self):
        settings = QSettings("CloudReturn", "WeatherApp")
        settings.setValue("geometry", self.saveGeometry())

    def restore_settings(self):
        settings = QSettings("CloudReturn", "WeatherApp")
        if settings.contains("geometry"):
            self.restoreGeometry(settings.value("geometry"))

    # 处理鼠标按下事件，用于拖动窗口
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()

    # 处理鼠标移动事件，用于拖动窗口
    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()

    def start_weather_thread(self):
        self.weather_thread = WeatherThread(self.api_key, self.latitude, self.longitude)
        self.weather_thread.weather_data_fetched.connect(self.display_weather)
        self.weather_thread.start()

    # 显示天气信息
    def display_weather(self, weather_data):
        if weather_data is None:
            return

        try:
            current_temp = weather_data['list'][0]['main'].get('temp', -999)
            humidity = weather_data['list'][0]['main'].get('humidity', -999)
            wind_speed = weather_data['list'][0]['wind'].get('speed', -999)
            weather_main = weather_data['list'][0]['weather'][0].get('main', 'N/A')

            if -100 <= current_temp <= 900:  # 检查温度是否在合理范围内
                current_temp_str = f"{current_temp - 273.15:.2f}"  # 转换为摄氏度并保留两位小数
            else:
                current_temp_str = 'N/A'

            # 天气描述中英文对照字典
            weather_desc_dict = {
                'Clear': '晴',
                'Clouds': '多云',
                'Rain': '雨',
                'Drizzle': '细雨',
                'Thunderstorm': '雷暴',
                'Snow': '雪',
                'Mist': '雾',
                'Smoke': '烟',
                'Haze': '霾',
                'Dust': '尘',
                'Fog': '雾',
                'Sand': '沙',
                'Ash': '灰',
                'Squall': '狂风',
                'Tornado': '龙卷风',
            }
            weather_main_cn = weather_desc_dict.get(weather_main, '未知')

            current_weather_str = f"当前温度：{current_temp_str} ℃，{weather_main_cn}   湿度：{humidity}%   风速：{wind_speed} m/s"
            self.current_weather_label.setText(current_weather_str)

            # 获取未来5天每天的总体天气情况
            future_5_days_data = weather_data['list']
            daily_weather = {}  # 存储每天的天气情况
            for day_weather in future_5_days_data:
                date_time = day_weather['dt_txt']  # 提取日期时间
                date = date_time.split()[0].split('-')[1:]  # 提取日期部分并去掉年份
                date_str = '-'.join(date)
                time = date_time.split()[1].split(':')[0]  # 提取小时部分
                weather_desc = day_weather['weather'][0].get('main', 'N/A')
                weather_desc_chinese = weather_desc_dict.get(weather_desc, '未知')
                max_temp = day_weather['main'].get('temp_max', -999)
                min_temp = day_weather['main'].get('temp_min', -999)

                # 更新或添加每天的天气情况
                if date_str in daily_weather:
                    daily_weather[date_str]['weather'].append(f"{time}: {weather_desc_chinese}")
                    daily_weather[date_str]['max_temp'] = max(max_temp, daily_weather[date_str]['max_temp'])
                    daily_weather[date_str]['min_temp'] = min(min_temp, daily_weather[date_str]['min_temp'])
                else:
                    daily_weather[date_str] = {'weather': [f"{time}: {weather_desc_chinese}"], 'max_temp': max_temp,
                                               'min_temp': min_temp}

            future_5_days_str = ""
            for date, weather_info in daily_weather.items():
                max_temp_celsius = round(weather_info['max_temp'] - 273.15, 2) if weather_info[
                                                                                      'max_temp'] != -999 else 'N/A'
                min_temp_celsius = round(weather_info['min_temp'] - 273.15, 2) if weather_info[
                                                                                      'min_temp'] != -999 else 'N/A'
                future_5_days_str += f"{date}：{', '.join(weather_info['weather'])}，最高温度：{max_temp_celsius} ℃，最低温度：{min_temp_celsius} ℃\n"
            self.future_5_days_label.setText("未来5天天气：\n" + future_5_days_str)

            # 更新数据更新时间
            self.update_time_label.setText(
                "更新时间：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "   数据来源：OpenWeather")

            # 调整窗口大小以适应内容
            self.adjustSize()

        except Exception as e:
            print("Error:", e)


# 设置位置对话框
class LocationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置位置")
        self.setWindowFlags(Qt.Dialog)
        self.init_ui()

    # 初始化设置窗口界面
    def init_ui(self):
        layout = QVBoxLayout()

        label_latitude = QLabel("输入纬度:", self)
        layout.addWidget(label_latitude)
        self.latitude_input = QLineEdit(self)
        layout.addWidget(self.latitude_input)

        label_longitude = QLabel("输入经度:", self)
        layout.addWidget(label_longitude)
        self.longitude_input = QLineEdit(self)
        layout.addWidget(self.longitude_input)

        save_button = QPushButton("保存", self)
        save_button.clicked.connect(self.save_location)
        layout.addWidget(save_button)

        self.setLayout(layout)

    # 检查输入的坐标是否有效
    def check_coordinate_validity(self, coordinate):
        try:
            float(coordinate)
            return True
        except ValueError:
            return False

    # 保存位置信息到文件中
    def save_location(self):
        latitude = self.latitude_input.text()
        longitude = self.longitude_input.text()

        if not (self.check_coordinate_validity(latitude) and self.check_coordinate_validity(longitude)):
            QMessageBox.warning(self, "错误", "请输入有效的纬度和经度。")
            return

        latitude = float(latitude)
        longitude = float(longitude)

        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            with open("data/location.txt", "w") as file:
                file.write(f"{latitude},{longitude}")
            self.parent().latitude = latitude
            self.parent().longitude = longitude
            self.parent().start_weather_thread()  # 更新位置后重新获取天气数据
            self.close()
        else:
            QMessageBox.warning(self, "错误", "请输入合法的纬度和经度范围。")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    weather_app = WeatherApp()
    sys.exit(app.exec_())
