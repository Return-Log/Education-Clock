import json
import requests
import base64
import re
import markdown2  # 新增依赖

from PyQt6.QtWidgets import QTextBrowser, QWidget, QVBoxLayout
from PyQt6.QtCore import QThread, QObject, pyqtSignal, QTimer


class ImagePreloadWorker(QObject):
    images_processed = pyqtSignal(str)  # 输出 HTML 字符串
    error_occurred = pyqtSignal(str)

    def __init__(self, markdown_text):
        super().__init__()
        self.markdown_text = markdown_text

    def run(self):
        try:
            image_pattern = r'!\[(.*?)\]\((.*?)\)'
            matches = re.findall(image_pattern, self.markdown_text)
            processed_text = self.markdown_text

            for alt, url in matches:
                try:
                    response = requests.get(url, timeout=5)
                    response.raise_for_status()
                    image_data = response.content
                    mime_type = response.headers.get('content-type', 'image/jpeg')
                    base64_str = f"data:{mime_type};base64,{base64.b64encode(image_data).decode('utf-8')}"

                    # 插入 HTML 图片标签，并保留 Markdown 换行结构
                    img_tag = f"![{alt}]({base64_str})"  # 保持原格式，让 markdown2 处理
                    processed_text = processed_text.replace(f"![{alt}]({url})", img_tag)

                except Exception as e:
                    processed_text = processed_text.replace(
                        f"![{alt}]({url})",
                        f'[图片加载失败: {str(e)}]'
                    )

            # 在图片替换完成后，再将 Markdown 转为 HTML
            html_content = markdown2.markdown(processed_text)

            self.images_processed.emit(html_content)

        except Exception as e:
            self.error_occurred.emit(f"图片预加载失败: {str(e)}")


class APIWorker(QObject):
    data_fetched = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, url, template):
        super().__init__()
        self.url = url
        self.template = template

    def run(self):
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            data = response.json().get("data", [])
            if not isinstance(data, list):
                data = [data]

            output = ""
            for item in data:
                if not isinstance(item, dict):
                    continue  # 跳过非字典类型的数据项
                line = self.template
                for key, value in item.items():
                    placeholder = "{" + key + "}"
                    line = line.replace(placeholder, str(value))
                output += line + "\n"

            self.data_fetched.emit(output)
        except Exception as e:
            self.error_occurred.emit(f"API 请求失败: {str(e)}")


class APIDisplayModule:
    def __init__(self, main_window):
        self.main_window = main_window
        self.tab_widget = main_window.findChild(QWidget, "tabWidget")
        self.tabs_info = {}  # 存储每个 tab 的状态 {name: {browser, api_thread, ...}}

        if not self.tab_widget:
            raise ValueError("找不到 tabWidget，请检查 UI 文件")

        QTimer.singleShot(0, self.late_init)

    def late_init(self):
        config_path = "data/api_config.json"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                raw_data = f.read()
                if not raw_data.strip():
                    raise ValueError("配置文件为空")
                self.api_configs = json.loads(raw_data)
        except FileNotFoundError:
            error_tab = QWidget()
            layout = QVBoxLayout()
            browser = QTextBrowser()
            browser.setMarkdown("**错误**: 找不到配置文件，请确认 'data/api_config.json' 是否存在。")
            layout.addWidget(browser)
            error_tab.setLayout(layout)
            self.tab_widget.addTab(error_tab, "错误")
            return
        except json.JSONDecodeError as je:
            error_tab = QWidget()
            layout = QVBoxLayout()
            browser = QTextBrowser()
            browser.setMarkdown(f"**错误**: 配置文件格式错误（JSON 解析失败） - {str(je)}")
            layout.addWidget(browser)
            error_tab.setLayout(layout)
            self.tab_widget.addTab(error_tab, "错误")
            return
        except Exception as e:
            error_tab = QWidget()
            layout = QVBoxLayout()
            browser = QTextBrowser()
            browser.setMarkdown(f"**错误**: 无法加载配置 - {str(e)}")
            layout.addWidget(browser)
            error_tab.setLayout(layout)
            self.tab_widget.addTab(error_tab, "错误")
            return

        for config in self.api_configs:
            # 检查每个配置项是否为字典类型
            if not isinstance(config, dict):
                continue
            self.create_api_tab(config)

    def create_api_tab(self, config):
        name = config.get("name", "Unnamed Tab")
        url = config.get("url")
        template = config.get("template", "")
        refresh_time_str = config.get("refresh_time", "1440")

        if not url or not template:
            tab = QWidget()
            layout = QVBoxLayout()
            browser = QTextBrowser()
            browser.setMarkdown(f"**错误**: 缺少 URL 或模板 - {name}")
            layout.addWidget(browser)
            tab.setLayout(layout)
            self.tab_widget.addTab(tab, name)
            return

        try:
            refresh_time = int(refresh_time_str) * 1000
        except (TypeError, ValueError):
            refresh_time = 1440 * 1000  # 默认值

        # 创建标签页
        tab = QWidget()
        layout = QVBoxLayout()
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml("<p><strong>加载中...</strong><br>正在获取数据和图片，请稍候。</p>")
        layout.addWidget(browser)
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, name)

        # 存储当前 tab 的信息
        self.tabs_info[name] = {
            "browser": browser,
            "url": url,
            "template": template,
            "timer": QTimer(),
        }

        # 设置定时器
        tab_info = self.tabs_info[name]
        tab_info["timer"].setInterval(refresh_time)
        tab_info["timer"].timeout.connect(lambda n=name: self.start_api_thread(n, url, template))

        # 启动 API 线程（首次加载）
        self.start_api_thread(name, url, template)

        # 开始定时刷新
        tab_info["timer"].start()

    def start_api_thread(self, name, url, template):
        tab_info = self.tabs_info.get(name)
        if not tab_info:
            return

        # 清理之前的线程（如果存在）
        if "api_thread" in tab_info:
            tab_info["api_thread"].quit()
            tab_info["api_thread"].wait()
            del tab_info["api_thread"]
        if "api_worker" in tab_info:
            del tab_info["api_worker"]

        # 创建新的线程与工作者
        api_thread = QThread()
        api_worker = APIWorker(url, template)
        api_worker.moveToThread(api_thread)

        # 绑定信号
        api_thread.started.connect(api_worker.run)
        api_worker.data_fetched.connect(lambda result, n=name: self.on_data_fetched(n, result))
        api_worker.error_occurred.connect(lambda err, n=name: self.on_error(n, err))

        # 存储线程对象
        tab_info["api_thread"] = api_thread
        tab_info["api_worker"] = api_worker

        # 启动线程
        api_thread.start()

    def on_data_fetched(self, name, markdown_output):
        tab_info = self.tabs_info.get(name)
        if not tab_info:
            return

        # 停止 API 线程
        tab_info["api_thread"].quit()
        tab_info["api_thread"].wait()

        # 开始图片预加载
        image_thread = QThread()
        image_worker = ImagePreloadWorker(markdown_output)
        image_worker.moveToThread(image_thread)

        # 绑定信号
        image_thread.started.connect(image_worker.run)
        image_worker.images_processed.connect(lambda result, n=name: self.on_images_processed(n, result))
        image_worker.error_occurred.connect(lambda err, n=name: self.on_error(n, err))

        # 存储线程对象
        tab_info["image_thread"] = image_thread
        tab_info["image_worker"] = image_worker

        # 启动图片线程
        image_thread.start()

    def on_images_processed(self, name, html_content):
        tab_info = self.tabs_info.get(name)
        if not tab_info:
            return

        tab_info["image_thread"].quit()
        tab_info["image_thread"].wait()

        full_html = f"""
        <style>
            img {{
                display: block;
                width: 100%;
                max-width: 100%;
                height: auto;
                margin: 10px auto;
            }}
            body {{
                font-family: sans-serif;
                font-size: 18px;
                line-height: 1.6;
                padding: 10px;
            }}
        </style>
        <div class="content">
            {html_content}
        </div>
        """

        tab_info["browser"].setHtml(full_html)

    def on_error(self, name, message):
        tab_info = self.tabs_info.get(name)
        if tab_info and tab_info["browser"]:
            tab_info["browser"].setHtml(f"<p style='color:red;'><strong>错误</strong>: {message}</p>")

    def update(self):
        """重新初始化模块：清除现有内容并重新加载 API 配置"""
        self.clear_all_tabs()
        self.late_init()

    def clear_all_tabs(self):
        """清理所有由本模块创建的 tab 和线程资源"""
        for name, info in list(self.tabs_info.items()):
            # 停止定时器
            if "timer" in info:
                info["timer"].stop()

            # 清理 API 线程
            if "api_thread" in info:
                info["api_thread"].quit()
                info["api_thread"].wait()
                del info["api_thread"]
            if "api_worker" in info:
                del info["api_worker"]

            # 清理图片线程
            if "image_thread" in info:
                info["image_thread"].quit()
                info["image_thread"].wait()
                del info["image_thread"]
            if "image_worker" in info:
                del info["image_worker"]

        tab_count = self.tab_widget.count()
        print(f"当前共有 {tab_count} 个标签页，将删除除第一个外的所有标签页。")
        for i in range(tab_count - 1, 0, -1):  # 倒序删除
            tab = self.tab_widget.widget(i)
            tab_name = self.tab_widget.tabText(i)
            print(f"正在删除标签页: {tab_name}")
            if tab:
                tab.deleteLater()
            self.tab_widget.removeTab(i)

        # 清空状态字典
        self.tabs_info.clear()

