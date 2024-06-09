"""
https://github.com/Return-Log/Education-Clock
GPL-3.0 license
coding: UTF-8
"""

import sys
from datetime import datetime
import requests
from PyQt5.QtCore import Qt, QTimer, QPoint, QSettings, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QDialog, QLineEdit, QMessageBox, \
    QPushButton


class WeatherThread(QThread):
    weather_data_fetched = pyqtSignal(dict)

    def __init__(self, api_key, latitude, longitude):
        super().__init__()
        self.api_key = api_key
        self.latitude = latitude
        self.longitude = longitude

    def run(self):
        url = f"http://api.openweathermap.org/data/2.5/forecast?lat={self.latitude}&lon={self.longitude}&appid={self.api_key}&units=metric"
        response = requests.get(url)
        data = response.json()
        self.weather_data_fetched.emit(data)


class WeatherApp(QWidget):
    def __init__(self):
        super().__init__()
        self.api_key = self.load_api_key()
        self.latitude, self.longitude = self.load_location()
        self.init_ui()
        self.restore_settings()

    def load_api_key(self):
        with open("data/[天气服务API]OpenWeather-API.txt", "r") as file:
            return file.read().strip()

    def load_location(self):
        with open("data/[天气坐标]location.txt", "r") as file:
            location = file.read().strip()
            latitude, longitude = location.split(',')
            return float(latitude), float(longitude)

    def init_ui(self):
        self.setWindowTitle("天气预报")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint)  # 设置窗口无边框并保持在底层
        layout = QVBoxLayout()

        self.current_weather_layout = QHBoxLayout()
        self.current_weather_icon_label = QLabel("", self)
        self.current_weather_icon_label.setFixedSize(100, 100)
        self.current_weather_layout.addWidget(self.current_weather_icon_label)

        self.current_temp_label = QLabel("", self)
        self.current_temp_label.setFont(QFont("Arial", 18))
        self.current_weather_layout.addWidget(self.current_temp_label)

        layout.addLayout(self.current_weather_layout)
        self.forecast_layout = QHBoxLayout()
        layout.addLayout(self.forecast_layout)

        self.setLayout(layout)
        self.resize(300, 200)
        self.show()

        self.mouseDoubleClickEvent = self.open_location_dialog
        self.start_weather_thread()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.start_weather_thread)
        self.timer.start(300000)  # 更新时间间隔为5*60*1000毫秒

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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()

    def start_weather_thread(self):
        self.weather_thread = WeatherThread(self.api_key, self.latitude, self.longitude)
        self.weather_thread.weather_data_fetched.connect(self.display_weather)
        self.weather_thread.start()

    def display_weather(self, weather_data):
        if weather_data is None:
            return

        try:
            current_weather = weather_data['list'][0]
            current_temp = current_weather['main'].get('temp', -999)
            humidity = current_weather['main'].get('humidity', -999)
            wind_speed = current_weather['wind'].get('speed', -999)
            weather_icon = current_weather['weather'][0].get('icon', '01d')
            weather_desc = current_weather['weather'][0].get('main', '')

            if -100 <= current_temp <= 900:
                current_temp_str = f"{current_temp:.0f}°C"
            else:
                current_temp_str = 'N/A'
            self.current_temp_label.setText(f"{current_temp_str} | 湿度: {humidity}% | 风速: {wind_speed} m/s")

            icon_url = f"http://openweathermap.org/img/wn/{weather_icon}@2x.png"
            weather_icon_pixmap = QPixmap()
            weather_icon_pixmap.loadFromData(requests.get(icon_url).content)
            self.current_weather_icon_label.setPixmap(weather_icon_pixmap.scaled(100, 100, Qt.KeepAspectRatio))

            self.update_background()

            future_5_days_data = weather_data['list']
            daily_weather = {}

            for day_weather in future_5_days_data:
                date_time = day_weather['dt_txt']
                date = date_time.split()[0]
                time = date_time.split()[1]
                weather_desc = day_weather['weather'][0].get('main', 'N/A')
                weather_icon = day_weather['weather'][0].get('icon', '01d')
                max_temp = day_weather['main'].get('temp_max', -999)
                min_temp = day_weather['main'].get('temp_min', -999)

                if date in daily_weather:
                    daily_weather[date]['max_temp'] = max(max_temp, daily_weather[date]['max_temp'])
                    daily_weather[date]['min_temp'] = min(min_temp, daily_weather[date]['min_temp'])
                else:
                    daily_weather[date] = {'weather': weather_desc, 'icon': weather_icon, 'max_temp': max_temp,
                                           'min_temp': min_temp}

            for i in reversed(range(self.forecast_layout.count())):
                self.forecast_layout.itemAt(i).widget().setParent(None)

            for date, weather_info in daily_weather.items():
                forecast_widget = QWidget()
                forecast_layout = QVBoxLayout()

                display_date = '-'.join(date.split('-')[1:])
                date_label = QLabel(display_date, self)
                date_label.setFont(QFont("Arial", 12))
                date_label.setAlignment(Qt.AlignCenter)
                forecast_layout.addWidget(date_label)

                weather_icon_label = QLabel(self)
                icon_url = f"http://openweathermap.org/img/wn/{weather_info['icon']}@2x.png"
                weather_icon_pixmap = QPixmap()
                weather_icon_pixmap.loadFromData(requests.get(icon_url).content)
                weather_icon_label.setPixmap(weather_icon_pixmap.scaled(75, 75, Qt.KeepAspectRatio))
                weather_icon_label.setAlignment(Qt.AlignCenter)
                forecast_layout.addWidget(weather_icon_label)

                temp_label = QLabel(f"{weather_info['max_temp']:.0f}°C\n{weather_info['min_temp']:.0f}°C", self)
                temp_label.setFont(QFont("Arial", 12))
                temp_label.setAlignment(Qt.AlignCenter)
                forecast_layout.addWidget(temp_label)

                forecast_widget.setLayout(forecast_layout)
                self.forecast_layout.addWidget(forecast_widget)

            self.adjustSize()

        except Exception as e:
            print("Error:", e)

    def update_background(self):
        current_hour = datetime.now().hour
        if 6 <= current_hour < 18:  # 白天时间段
            self.setStyleSheet("background-color: lightblue; color: black;")
        else:  # 晚上时间段
            self.setStyleSheet("background-color: darkblue; color: white;")


class LocationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置位置")
        self.setWindowFlags(Qt.Dialog)
        self.init_ui()

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

    def check_coordinate_validity(self, coordinate):
        try:
            float(coordinate)
            return True
        except ValueError:
            return False

    def save_location(self):
        latitude = self.latitude_input.text()
        longitude = self.longitude_input.text()

        if not (self.check_coordinate_validity(latitude) and self.check_coordinate_validity(longitude)):
            QMessageBox.warning(self, "错误", "请输入有效的纬度和经度。")
            return

        latitude = float(latitude)
        longitude = float(longitude)

        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            with open("data/[天气坐标]location.txt", "w") as file:
                file.write(f"{latitude},{longitude}")
            self.parent().latitude = latitude
            self.parent().longitude = longitude
            self.parent().start_weather_thread()
            self.close()
        else:
            QMessageBox.warning(self, "错误", "请输入有效范围内的纬度和经度。")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    weather_app = WeatherApp()
    sys.exit(app.exec_())
