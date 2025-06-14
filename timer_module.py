import sys

from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6 import uic
from PyQt6.QtCore import QTimer, QUrl


class TimerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("./ui/timers.ui", self)

        # 默认倒计时模式
        self.radioButton_2.setChecked(True)
        self.widget.setEnabled(True)

        # 初始化变量
        self.is_running = False
        self.is_stopwatch_mode = False
        self.time_left = 0  # 秒数

        # 连接信号
        self.radioButton.toggled.connect(self.mode_changed)
        self.pushButton.clicked.connect(self.start_pause_timer)
        self.pushButton_2.clicked.connect(self.reset_timer)

        self.horizontalSlider.valueChanged.connect(self.update_lcd_from_sliders)
        self.horizontalSlider_2.valueChanged.connect(self.update_lcd_from_sliders)
        self.horizontalSlider_3.valueChanged.connect(self.update_lcd_from_sliders)

        # 初始化LCD显示
        self.update_lcd_from_sliders()

        # 设置定时器
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_time)

        # 加载提示音
        self.alert_sound = QSoundEffect(self)
        self.alert_sound.setSource(QUrl.fromLocalFile("./icon/warning.wav"))  # 放在项目目录下
        self.alert_sound.setVolume(1.0)  # 音量 0.0 ~ 1.0

    def mode_changed(self):
        # 判断模式变化
        self.is_stopwatch_mode = self.radioButton.isChecked()
        self.widget.setEnabled(not self.is_stopwatch_mode)

        self.timer.stop()
        self.is_running = False
        self.pushButton.setText("开始")

        if self.is_stopwatch_mode:
            self.time_left = 0
        else:
            self.time_left = self.get_slider_time()

        self.update_lcd_display()

    def get_slider_time(self):
        h = self.horizontalSlider.value()
        m = self.horizontalSlider_2.value()
        s = self.horizontalSlider_3.value()
        return h * 3600 + m * 60 + s

    def update_lcd_from_sliders(self):
        if not self.is_stopwatch_mode:
            h = self.horizontalSlider.value()
            m = self.horizontalSlider_2.value()
            s = self.horizontalSlider_3.value()
            self.time_left = h * 3600 + m * 60 + s
            self.update_lcd_display()

    def update_lcd_display(self):
        h = self.time_left // 3600
        m = (self.time_left % 3600) // 60
        s = self.time_left % 60

        self.lcdNumber.display(f"{h:02d}")
        self.lcdNumber_2.display(f"{m:02d}")
        self.lcdNumber_3.display(f"{s:02d}")

    def start_pause_timer(self):
        if self.is_running:
            self.timer.stop()
            self.pushButton.setText("开始")
        else:
            if not self.is_stopwatch_mode:
                self.time_left = self.get_slider_time()
            self.timer.start()
            self.pushButton.setText("暂停")
        self.is_running = not self.is_running

    def reset_timer(self):
        self.timer.stop()
        self.is_running = False
        self.pushButton.setText("开始")
        if self.is_stopwatch_mode:
            self.time_left = 0
        else:
            self.time_left = self.get_slider_time()
        self.update_lcd_display()

    def update_time(self):
        if self.is_stopwatch_mode:
            self.time_left += 1
        else:
            if self.time_left > 0:
                if 1 <= self.time_left <= 4:
                    self.alert_sound.play()
                self.time_left -= 1
            else:
                self.timer.stop()
                self.is_running = False
                self.pushButton.setText("开始")
        self.update_lcd_display()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TimerApp()
    window.show()
    sys.exit(app.exec())
