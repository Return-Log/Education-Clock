import random
import sys
import math
import logging
from PyQt6.QtWidgets import QDialog, QLabel, QApplication, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QFontDatabase, QPainter, QColor, QPen

# # 配置日志
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler("roll_call.log"),
#         logging.StreamHandler()
#     ]
# )


class NameSphere:
    """3D球体上的名字点"""

    def __init__(self, name, x, y, z):
        self.name = name
        self.x = x  # 3D坐标
        self.y = y
        self.z = z
        self.is_selected = False

    def get_3d_position(self, radius, rotation_x, rotation_y):
        """获取旋转后的3D坐标"""
        # 直接使用预计算的坐标
        x, y, z = self.x * radius, self.y * radius, self.z * radius

        # 绕Y轴旋转
        cos_y = math.cos(rotation_y)
        sin_y = math.sin(rotation_y)
        x_new = x * cos_y - z * sin_y
        z_new = x * sin_y + z * cos_y
        x, z = x_new, z_new

        # 绕X轴旋转
        cos_x = math.cos(rotation_x)
        sin_x = math.sin(rotation_x)
        y_new = y * cos_x - z * sin_x
        z_new = y * sin_x + z * cos_x
        y, z = y_new, z_new

        return x, y, z

    def project_to_2d(self, x, y, z, width, height, zoom):
        """将3D坐标投影到2D屏幕"""
        distance = 1000
        scale = distance / (distance + z) * zoom
        screen_x = width / 2 + x * scale
        screen_y = height / 2 - y * scale
        return screen_x, screen_y, scale


class AnimationWidget(QWidget):
    """3D球形动画控件"""
    animation_finished = pyqtSignal(str)

    def __init__(self, names, selected_name, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: white;")

        # 限制最大显示名字数量以保证性能，但可以处理更多名字
        self.max_display_names = 100  # 增加最大显示数量
        self.names = names
        self.selected_name = selected_name
        self.name_spheres = []

        # 动画参数
        self.rotation_y = 0
        self.rotation_x = 0
        self.zoom = 1.0
        self.phase = 0  # 0: 旋转阶段, 1: 拉近阶段, 2: 聚焦阶段, 3: 高亮阶段
        self.frame_count = 0
        self.target_theta = 0
        self.target_phi = 0
        self.initial_rotation_y = 0
        self.initial_rotation_x = 0
        self.target_rotation_y = 0
        self.target_rotation_x = 0
        self.adjusted_target_y = 0
        self.base_radius = 0

        # 初始化球体上的名字点
        self.init_sphere()

        # 动画定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)  # 约60fps

        logging.info(f"Animation started for {len(self.names)} names")

    def init_sphere(self):
        """在球体上均匀分布名字 - 使用直接坐标"""
        # 限制显示数量但处理所有名字
        display_indices = list(range(len(self.names)))
        if len(self.names) > self.max_display_names:
            # 确保选中的名字一定会显示
            selected_index = -1
            for i, name in enumerate(self.names):
                if name == self.selected_name or name.rstrip('*') == self.selected_name:
                    selected_index = i
                    break

            # 随机选择其他名字
            other_indices = [i for i in display_indices if i != selected_index]
            if selected_index != -1:
                if len(other_indices) > self.max_display_names - 1:
                    other_indices = random.sample(other_indices, self.max_display_names - 1)
                display_indices = [selected_index] + other_indices
            else:
                display_indices = random.sample(display_indices, self.max_display_names)

        # 使用斐波那契螺旋法在球面上分布点
        n = len(display_indices)
        golden_ratio = (1 + math.sqrt(5)) / 2
        self.selected_sphere = None

        for i, original_index in enumerate(display_indices):
            name = self.names[original_index]

            # 斐波那契螺旋分布
            theta = 2 * math.pi * i / golden_ratio
            phi = math.acos(1 - 2 * i / n) if n > 1 else math.pi / 2

            # 转换为笛卡尔坐标
            x = math.sin(phi) * math.cos(theta)
            y = math.sin(phi) * math.sin(theta)
            z = math.cos(phi)

            sphere = NameSphere(name, x, y, z)
            if name == self.selected_name or name.rstrip('*') == self.selected_name:
                sphere.is_selected = True
                self.selected_sphere = sphere
            self.name_spheres.append(sphere)

    def update_animation(self):
        """更新动画状态"""
        width = self.width()
        height = self.height()
        if width > 0 and height > 0:
            self.base_radius = min(width, height) * 0.3

        self.frame_count += 1

        if self.phase == 0:  # 初始阶段：小球形态 (0-30帧)
            progress = min(1.0, self.frame_count / 30.0)
            self.zoom = 0.1 + progress * 0.9
            self.base_radius = min(width, height) * 0.3 * self.zoom

            # 轻微随机旋转
            self.rotation_y += 0.03
            self.rotation_x += 0.02

            if self.frame_count > 30:
                self.phase = 1
                self.frame_count = 0

        elif self.phase == 1:  # 旋转到位阶段 (30-100帧)
            # 只在进入此阶段时计算目标位置
            if self.frame_count == 1:  # 刚进入此阶段
                # 如果有选中的球体，计算需要的旋转角度
                if self.selected_sphere:
                    p_x = self.selected_sphere.x
                    p_y = self.selected_sphere.y
                    p_z = self.selected_sphere.z
                    length = math.sqrt(p_x ** 2 + p_y ** 2 + p_z ** 2)
                    if length == 0:
                        self.target_rotation_y = 0
                        self.target_rotation_x = 0
                    else:
                        self.target_rotation_y = math.atan2(p_x, p_z)
                        z1 = math.sqrt(p_x ** 2 + p_z ** 2)
                        self.target_rotation_x = math.atan2(p_y, z1)

            progress = min(1.0, (self.frame_count - 1) / 70.0)
            eased_progress = 1 - math.pow(1 - progress, 2)

            # 渐进式旋转到目标角度
            if hasattr(self, 'target_rotation_y') and hasattr(self, 'target_rotation_x'):
                delta_y = self.target_rotation_y - self.rotation_y
                delta_x = self.target_rotation_x - self.rotation_x

                # 处理角度跨越问题 (确保最短路径旋转)
                if delta_y > math.pi:
                    delta_y -= 2 * math.pi
                elif delta_y < -math.pi:
                    delta_y += 2 * math.pi

                if delta_x > math.pi:
                    delta_x -= 2 * math.pi
                elif delta_x < -math.pi:
                    delta_x += 2 * math.pi

                self.rotation_y += delta_y * 0.1
                self.rotation_x += delta_x * 0.1

            # 同时放大
            self.zoom = 1.0 + eased_progress * 3.0  # 减小放大倍数
            self.base_radius = min(width, height) * 0.3 * self.zoom

            # 到达目标或时间到则进入下一阶段
            if (hasattr(self, 'target_rotation_y') and hasattr(self, 'target_rotation_x') and
                abs(delta_y) < 0.02 and abs(delta_x) < 0.02) or self.frame_count > 70:
                self.phase = 2
                self.frame_count = 0
                # 精确设置最终位置
                if hasattr(self, 'target_rotation_y') and hasattr(self, 'target_rotation_x'):
                    self.rotation_y = self.target_rotation_y
                    self.rotation_x = self.target_rotation_x

        elif self.phase == 2:  # 聚焦放大阶段 (100-160帧)
            progress = min(1.0, self.frame_count / 60.0)
            eased_progress = progress * progress

            # 大幅放大以聚焦到目标 - 减小最大放大倍数
            self.zoom = 4.0 + eased_progress * 4.0  # 从4倍放大到8倍
            self.base_radius = min(width, height) * 0.3 * self.zoom

            if self.frame_count > 60:
                self.phase = 3
                self.frame_count = 0

        elif self.phase == 3:  # 最终展示阶段 (160-220帧)
            self.zoom = 8.0
            self.base_radius = min(width, height) * 0.3 * self.zoom

            if self.frame_count > 60:
                self.timer.stop()
                self.animation_finished.emit(self.selected_name)

        self.update()

    def paintEvent(self, event):
        """绘制球体和名字"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        self.base_radius = min(width, height) * 0.3

        # 按Z轴排序(后面的先画)
        sorted_spheres = []
        for sphere in self.name_spheres:
            x, y, z = sphere.get_3d_position(self.base_radius, self.rotation_x, self.rotation_y)
            screen_x, screen_y, scale = sphere.project_to_2d(x, y, z, width, height, self.zoom)
            sorted_spheres.append((z, sphere, screen_x, screen_y, scale))

        sorted_spheres.sort(key=lambda item: item[0], reverse=True)

        # 绘制连接线(网格效果) - 优化性能
        if self.phase < 3 and len(sorted_spheres) > 0:
            pen = QPen(QColor(200, 200, 200), max(1, int(1 * (1 / self.zoom))))
            painter.setPen(pen)

            # 限制连线数量以提高性能
            visible_count = min(len(sorted_spheres), 50)
            for i in range(0, visible_count, 3):  # 减少连线密度
                if i + 2 < visible_count:
                    z1, s1, x1, y1, scale1 = sorted_spheres[i]
                    z2, s2, x2, y2, scale2 = sorted_spheres[i + 2]
                    if z1 > -self.base_radius and z2 > -self.base_radius:  # 只绘制可见的线
                        painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # 绘制名字 - 优化性能和显示效果
        displayed_count = 0
        max_displayed = 100  # 限制同时显示的名字数量

        for z, sphere, screen_x, screen_y, scale in sorted_spheres:
            if z < -self.base_radius * 2 or displayed_count > max_displayed:
                continue

            # 在拉近和聚焦阶段，只显示靠近中心的名字
            if self.phase >= 1:
                # 计算距离中心的距离
                center_distance = math.sqrt((screen_x - width / 2) ** 2 + (screen_y - height / 2) ** 2)
                max_distance = min(width, height) * 0.6 * (1 / self.zoom)
                if center_distance > max_distance and not sphere.is_selected:
                    continue

            # 设置字体和颜色
            if sphere.is_selected:
                if self.phase >= 2:  # 从聚焦阶段开始高亮
                    color = QColor(50, 60, 180)
                    font_size = int(20 * scale * min(self.zoom, 8.0) / 8.0)  # 限制最大字体
                else:
                    # 旋转和拉近阶段的选中名字
                    depth_factor = max(0.4, min(1.0, (z + self.base_radius * 2) / (self.base_radius * 4)))
                    gray = int(255 * depth_factor)
                    color = QColor(gray, gray, gray)
                    font_size = max(12, int(16 * scale))
            else:
                # 非选中名字
                if self.phase >= 1:
                    # 拉近和聚焦阶段降低非选中名字的可见度
                    depth_factor = max(0.2, min(1.0, (z + self.base_radius * 2) / (self.base_radius * 4)))
                    alpha = int(255 * depth_factor * (0.4 if self.phase == 1 else 0.15))
                    color = QColor(100, 100, 100, alpha)
                else:
                    # 旋转阶段正常显示
                    depth_factor = max(0.3, min(1.0, (z + self.base_radius * 2) / (self.base_radius * 4)))
                    gray = int(255 * depth_factor)
                    color = QColor(gray, gray, gray)
                font_size = max(8, int(12 * scale))

            font = QFont("Microsoft YaHei", font_size)
            painter.setFont(font)
            painter.setPen(color)

            # 显示名字(去掉星号)
            display_name = sphere.name.rstrip('*')
            # 限制名字长度避免渲染问题
            if len(display_name) > 8:
                display_name = display_name[:7] + ".."

            text_width = painter.fontMetrics().horizontalAdvance(display_name)
            text_height = painter.fontMetrics().height()

            painter.drawText(
                int(screen_x - text_width / 2),
                int(screen_y + text_height / 4),
                display_name
            )
            displayed_count += 1

            # 在选中的名字周围绘制圆圈(在拉近、聚焦和高亮阶段)
            if sphere.is_selected and self.phase >= 1:
                pen = QPen(QColor(50, 60, 180), max(2, int(3 * (self.zoom / 3))))
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                radius = max(text_width, text_height) * 0.7
                painter.drawEllipse(
                    QPointF(screen_x, screen_y),
                    radius, radius
                )


class RollCallDialog(QDialog):
    class RollCallSignals(QObject):
        closed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle('随机点名')
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setStyleSheet("background-color: white;")
        self.setFixedSize(800, 450)

        # 读取名字列表
        self.names = self.load_names()
        if not self.names:
            logging.error("No names loaded, dialog may not function correctly")

        # 初始化布局和控件
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # 名字标签(初始显示)
        self.name_label = QLabel("点击开始", self)
        preferred_font = "华文行楷"
        fallback_font = "微软雅黑"
        font = QFont(preferred_font, 140) if preferred_font in QFontDatabase.families() else QFont(fallback_font, 140,
                                                                                                   QFont.Weight.Bold)
        self.name_label.setFont(font)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet(f"""
            QLabel {{
                color: black;
                font-size: 140pt;
                font-family: {font.family()};
            }}
        """)
        self.layout.addWidget(self.name_label)

        # 动画控件(初始隐藏)
        self.animation_widget = None

        # 居中窗口
        screen = QApplication.primaryScreen().availableGeometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

        self.setMouseTracking(True)
        self.is_rolling = False
        self.animation_play = False
        self.signals = self.RollCallSignals()

        logging.info("RollCallDialog initialized")

    def load_names(self):
        try:
            with open('./data/name.txt', 'r', encoding='utf-8') as file:
                names = [line.strip() for line in file.readlines() if line.strip()]
            logging.info(f"Loaded {len(names)} names from name.txt")
            return names
        except FileNotFoundError:
            logging.error("name.txt not found")
            return []
        except Exception as e:
            logging.error(f"Error loading names: {e}")
            return []

    def save_names(self):
        try:
            with open('./data/name.txt', 'w', encoding='utf-8') as file:
                for name in self.names:
                    file.write(f"{name}\n")
            logging.info("Names saved successfully")
        except Exception as e:
            logging.error(f"Error saving names: {e}")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.is_rolling:
            if self.animation_play:
                self.animation_play = False
                self.animation_widget.deleteLater()

            self.start_roll_call()

    def start_roll_call(self):
        if not self.names:
            self.name_label.setText("没有可用的名字")
            logging.warning("No names available for roll call")
            return

        self.is_rolling = True

        self.name_label.hide()

        # 选择名字(保持原有逻辑)
        unmarked_names = [name for name in self.names if not name.endswith('*')]
        if not unmarked_names:
            self.names = [name.rstrip('*') for name in self.names]
            self.save_names()
            unmarked_names = self.names
            logging.info("All names were marked, resetting marks")

        selected_name = random.choice(unmarked_names)

        # if selected_name == "李明锐" and random.random() < 0.6:
        #     displayed_name = "李广泽"
        # elif selected_name == "张永瀚" and random.random() < 0.6:
        #     displayed_name = "焦威"
        # else:
        #     displayed_name = selected_name

        displayed_name = selected_name

        # 标记已显示的名字
        marked_name = selected_name if selected_name == displayed_name else selected_name
        marked = False
        for i, name in enumerate(self.names):
            if name == marked_name and not name.endswith('*') and not marked:
                self.names[i] = f"{name}*"
                marked = True
                break
        self.save_names()
        logging.info(f"Selected and marked name: {selected_name}, displaying: {displayed_name}")

        # 创建并显示动画
        self.animation_widget = AnimationWidget(self.names, displayed_name, self)
        self.animation_widget.setGeometry(0, 0, self.width(), self.height())
        self.animation_widget.animation_finished.connect(self.on_animation_finished)
        self.layout.addWidget(self.animation_widget)
        self.animation_widget.show()

    def on_animation_finished(self):
        """动画结束后显示最终结果"""
        if self.animation_widget:
            # self.animation_widget.hide()
            # self.animation_widget.deleteLater()
            self.animation_play = True
            # self.animation_widget = None

        # display_name = selected_name.rstrip('*')
        # self.name_label.setText(display_name)
        # self.name_label.show()
        self.is_rolling = False
        # logging.info(f"Roll call completed: {display_name}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        new_width = self.width()
        new_height = int(new_width * 9 / 16)
        self.setFixedSize(new_width, new_height)
        if self.animation_widget:
            self.animation_widget.setGeometry(0, 0, new_width, new_height)

    def closeEvent(self, event):
        self.save_names()
        if self.animation_widget:
            self.animation_widget.deleteLater()
        self.signals.closed.emit()
        super().closeEvent(event)
        logging.info("RollCallDialog closed")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = RollCallDialog()
    dialog.show()
    sys.exit(app.exec())