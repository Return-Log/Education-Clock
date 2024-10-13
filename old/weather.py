import sys
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, QPoint, QSettings, QThread, pyqtSignal, QUrl, QSize
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QDialog, QLineEdit, QMessageBox, QPushButton, QMainWindow, QStatusBar, QLineEdit
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest
import requests


class WeatherThread(QThread):
    weather_data_fetched = pyqtSignal(dict)

    def __init__(self, api_key, latitude, longitude):
        super().__init__()
        self.api_key = api_key
        self.latitude = latitude
        self.longitude = longitude

    def run(self):
        """运行线程获取天气数据"""
        try:
            url = f"http://api.openweathermap.org/data/2.5/forecast?lat={self.latitude}&lon={self.longitude}&appid={self.api_key}&units=metric"
            response = requests.get(url)
            data = response.json()
            self.weather_data_fetched.emit(data)
        except Exception as e:
            self.weather_data_fetched.emit({"error": str(e)})


class WeatherApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api_key = self.load_api_key()
        self.latitude, self.longitude = self.load_location()
        self.init_ui()
        self.restore_settings()
        self.network_manager = QNetworkAccessManager(self)

    def load_api_key(self):
        """从文件加载API密钥"""
        with open("data/[天气服务API]OpenWeather-API.txt", "r") as file:
            return file.read().strip()

    def load_location(self):
        """从文件加载地理位置"""
        with open("data/[天气坐标]location.txt", "r") as file:
            location = file.read().strip()
            latitude, longitude = location.split(',')
            return float(latitude), float(longitude)

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("天气预报")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnBottomHint)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

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

        # 添加状态栏显示报错信息
        self.error_line = QLineEdit(self)
        self.error_line.setReadOnly(True)
        layout.addWidget(self.error_line)

        self.setCentralWidget(central_widget)
        self.resize(300, 200)
        self.show()

        self.mouseDoubleClickEvent = self.open_location_dialog
        self.start_weather_thread()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.start_weather_thread)
        self.timer.start(600000)  # 更新间隔：10 分钟

    def open_location_dialog(self, event):
        """打开位置设置对话框"""
        location_dialog = LocationDialog(self)
        location_dialog.exec()

    def closeEvent(self, event):
        """关闭窗口时保存设置"""
        self.save_settings()
        event.accept()

    def save_settings(self):
        """保存窗口位置和大小设置"""
        settings = QSettings("CloudReturn", "WeatherApp")
        settings.setValue("geometry", self.saveGeometry())

    def restore_settings(self):
        """恢复窗口位置和大小设置"""
        settings = QSettings("CloudReturn", "WeatherApp")
        if settings.contains("geometry"):
            self.restoreGeometry(settings.value("geometry"))

    def mousePressEvent(self, event):
        """处理窗口拖动事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.oldPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        """处理窗口拖动时的移动事件"""
        delta = QPoint(event.globalPosition().toPoint() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPosition().toPoint()

    def start_weather_thread(self):
        """启动天气数据获取线程"""
        self.weather_thread = WeatherThread(self.api_key, self.latitude, self.longitude)
        self.weather_thread.weather_data_fetched.connect(self.display_weather)
        self.weather_thread.start()

    def display_weather(self, weather_data):
        """显示当前天气和未来5天的天气预报"""
        if 'error' in weather_data:
            self.error_line.setText(f"Error: {weather_data['error']}")
            return

        try:
            # 显示当前天气
            current_weather = weather_data['list'][0]
            current_temp = current_weather['main'].get('temp', -999)
            humidity = current_weather['main'].get('humidity', -999)
            wind_speed = current_weather['wind'].get('speed', -999)
            weather_icon = current_weather['weather'][0].get('icon', '01d')

            current_temp_str = f"{current_temp:.0f}°C" if -100 <= current_temp <= 900 else 'N/A'
            self.current_temp_label.setText(f"{current_temp_str} | 湿度: {humidity}% | 风速: {wind_speed} m/s")

            icon_url = f"http://openweathermap.org/img/wn/{weather_icon}@2x.png"
            self.load_icon(icon_url, self.current_weather_icon_label, QSize(100, 100))

            # 显示未来5天的天气预报
            future_5_days_data = weather_data['list']
            daily_weather = {}

            # 提取5天的天气数据
            for day_weather in future_5_days_data:
                date_time = day_weather['dt_txt']
                date = date_time.split()[0]
                weather_desc = day_weather['weather'][0].get('main', 'N/A')
                weather_icon = day_weather['weather'][0].get('icon', '01d')
                max_temp = day_weather['main'].get('temp_max', -999)
                min_temp = day_weather['main'].get('temp_min', -999)

                if date in daily_weather:
                    daily_weather[date]['max_temp'] = max(max_temp, daily_weather[date]['max_temp'])
                    daily_weather[date]['min_temp'] = min(min_temp, daily_weather[date]['min_temp'])
                else:
                    daily_weather[date] = {
                        'weather': weather_desc,
                        'icon': weather_icon,
                        'max_temp': max_temp,
                        'min_temp': min_temp
                    }

            # 清除之前的天气预报
            for i in reversed(range(self.forecast_layout.count())):
                self.forecast_layout.itemAt(i).widget().setParent(None)

            # 显示未来5天的天气预报
            for date, weather_info in daily_weather.items():
                forecast_widget = QWidget()
                forecast_layout = QVBoxLayout()

                display_date = '-'.join(date.split('-')[1:])
                date_label = QLabel(display_date, self)
                date_label.setFont(QFont("Arial", 12))
                date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                forecast_layout.addWidget(date_label)

                weather_icon_label = QLabel(self)
                icon_url = f"http://openweathermap.org/img/wn/{weather_info['icon']}@2x.png"
                self.load_icon(icon_url, weather_icon_label, QSize(75, 75))

                weather_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                forecast_layout.addWidget(weather_icon_label)

                temp_label = QLabel(f"{weather_info['max_temp']:.0f}°C\n{weather_info['min_temp']:.0f}°C", self)
                temp_label.setFont(QFont("Arial", 12))
                temp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                forecast_layout.addWidget(temp_label)

                forecast_widget.setLayout(forecast_layout)
                self.forecast_layout.addWidget(forecast_widget)

            # 更新背景和错误信息
            self.update_background()
            self.error_line.setText("")

        except Exception as e:
            self.error_line.setText(f"解析天气数据时出错: {e}")

    def load_icon(self, url, label, size):
        """加载天气图标"""
        request = QNetworkRequest(QUrl(url))
        reply = self.network_manager.get(request)
        reply.finished.connect(lambda: self.on_icon_loaded(reply, label, size))

    def on_icon_loaded(self, reply, label, size):
        """图标加载完成时的回调函数"""
        if reply.error():
            self.error_line.setText(f"加载图标时出错: {reply.errorString()}")
            return
        pixmap = QPixmap()
        pixmap.loadFromData(reply.readAll())
        label.setPixmap(pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio))

    def update_background(self):
        """根据时间更新背景颜色"""
        current_hour = datetime.now().hour
        if 6 <= current_hour < 18:
            self.setStyleSheet("background-color: lightblue; color: black;")
        else:
            self.setStyleSheet("background-color: darkblue; color: white;")


class LocationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置位置")
        self.setWindowFlags(Qt.WindowType.Dialog)
        self.init_ui()

    def init_ui(self):
        """初始化位置设置对话框的UI"""
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
        """检查坐标的有效性"""
        try:
            float(coordinate)
            return True
        except ValueError:
            return False

    def save_location(self):
        """保存用户输入的经纬度信息"""
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
    sys.exit(app.exec())
