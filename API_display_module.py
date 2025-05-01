import json
import requests
import base64
import re
from PyQt6.QtWidgets import QTextBrowser, QWidget, QVBoxLayout
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QTextDocument
from datetime import datetime

class APIWorker(QObject):
    """Worker class to handle API requests in a separate thread"""
    data_fetched = pyqtSignal(str, str)  # Signal for successful data fetch (name, markdown_output)
    error_occurred = pyqtSignal(str, str)  # Signal for errors (name, error_message)

    def fetch_data(self, name, url, template):
        """Fetch data from the API and process it"""
        try:
            # Perform GET request
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Extract the 'data' field from the response
            filtered_data = data.get('data', [])
            if not isinstance(filtered_data, list):
                filtered_data = [filtered_data] if filtered_data else []

            if not filtered_data:
                self.error_occurred.emit(name, "**错误**: API 返回的数据为空\n\n将会在下次刷新时重试。")
                return

            # Process data and generate Markdown output
            markdown_output = ""
            for item in filtered_data:
                item_output = template
                for key in item:
                    placeholder = "{" + key + "}"
                    value = str(item[key]).replace("\n", " ")  # Prevent Markdown breaking
                    item_output = item_output.replace(placeholder, value)

                # Handle images in the template
                item_output = self.process_images(item_output)
                markdown_output += item_output + "\n"

            # Emit successful data
            self.data_fetched.emit(name, markdown_output)

        except requests.RequestException as e:
            # Emit error
            self.error_occurred.emit(name, f"**错误**: 无法获取数据 - {str(e)}\n\n将会在下次刷新时重试。")
        except (ValueError, KeyError) as e:
            # Handle JSON parsing or key errors
            self.error_occurred.emit(name, f"**错误**: 数据解析失败 - {str(e)}\n\n将会在下次刷新时重试。")

    def process_images(self, text):
        """Process Markdown image links and embed as base64"""
        # Find all Markdown image links: ![alt](url)
        image_pattern = r'!\[(.*?)\]\((.*?)\)'
        matches = re.findall(image_pattern, text)

        for alt, url in matches:
            try:
                # Download the image
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                image_data = response.content

                # Convert to base64
                base64_image = base64.b64encode(image_data).decode('utf-8')
                mime_type = response.headers.get('content-type', 'image/jpeg')
                base64_string = f"data:{mime_type};base64,{base64_image}"

                # Replace original image link with base64 data
                original_image = f"![{alt}]({url})"
                new_image = f"![{alt}]({base64_string})"
                text = text.replace(original_image, new_image)

            except requests.RequestException as e:
                # If image download fails, replace with error message
                text = text.replace(f"![{alt}]({url})", f"[无法加载图片: {url} - {str(e)}]")

        return text

class APIDisplayModule:
    def __init__(self, main_window):
        self.main_window = main_window
        self.tab_widget = main_window.findChild(QWidget, "tabWidget")
        if self.tab_widget is None:
            # Create a fallback tab to display the error
            self.create_error_tab("找不到 tabWidget，请检查 UI 文件")
            return

        self.api_configs = self.load_api_config()
        self.tabs = {}
        self.threads = {}  # Store threads and workers

        # Initialize tabs for each API configuration
        for config in self.api_configs:
            self.create_tab(config)

    def load_api_config(self):
        """Load API configurations from data/api_config.data"""
        try:
            with open('data/api_config.json', 'r', encoding='utf-8') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            # Create a fallback tab to display the error
            self.create_error_tab(f"无法加载 API 配置文件: {str(e)}")
            return []

    def create_error_tab(self, error_message):
        """Create a tab to display an error message"""
        tab = QWidget()
        layout = QVBoxLayout()
        output_browser = QTextBrowser()
        output_browser.setMarkdown(f"**错误**: {error_message}")
        layout.addWidget(output_browser)
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "错误")

    def create_tab(self, config):
        """Create a tab for the given API configuration"""
        name = config.get('name', 'Unnamed API')
        url = config.get('url', '')
        template = config.get('template', '')
        refresh_time = int(config.get('refresh_time', '60')) * 1000  # Convert to milliseconds

        if not url or not template:
            # Create a tab to display the configuration error
            tab = QWidget()
            layout = QVBoxLayout()
            output_browser = QTextBrowser()
            output_browser.setMarkdown(f"**错误**: API 配置错误 - {name}: URL 或模板缺失")
            layout.addWidget(output_browser)
            tab.setLayout(layout)
            self.tab_widget.addTab(tab, name)
            return

        # Create a new tab widget
        tab = QWidget()
        layout = QVBoxLayout()
        output_browser = QTextBrowser()
        output_browser.setOpenExternalLinks(True)  # Allow clicking links
        layout.addWidget(output_browser)
        tab.setLayout(layout)

        # Add tab to tabWidget
        tab_index = self.tab_widget.addTab(tab, name)
        self.tabs[name] = {
            'browser': output_browser,
            'url': url,
            'template': template,
            'timer': QTimer(),
            'last_error': None
        }

        # Set up worker and thread
        thread = QThread()
        worker = APIWorker()
        worker.moveToThread(thread)
        self.threads[name] = {'thread': thread, 'worker': worker}

        # Connect signals
        worker.data_fetched.connect(self.on_data_fetched)
        worker.error_occurred.connect(self.on_error_occurred)
        self.tabs[name]['timer'].timeout.connect(lambda: self.refresh_data(name))

        # Start the thread
        thread.start()

        # Set up timer for refreshing data
        self.tabs[name]['timer'].start(refresh_time)

        # Initial data fetch
        self.refresh_data(name)

    def refresh_data(self, name):
        """Trigger data fetch in the worker thread"""
        config = self.tabs.get(name)
        if not config:
            return

        worker = self.threads[name]['worker']
        url = config['url']
        template = config['template']

        # Call fetch_data in the worker thread
        worker.fetch_data(name, url, template)

    def on_data_fetched(self, name, markdown_output):
        """Handle successful data fetch"""
        config = self.tabs.get(name)
        if config:
            config['browser'].setMarkdown(markdown_output)
            config['last_error'] = None

    def on_error_occurred(self, name, error_message):
        """Handle error during data fetch"""
        config = self.tabs.get(name)
        if config:
            config['browser'].setMarkdown(error_message)
            config['last_error'] = error_message

    def __del__(self):
        """Clean up threads on destruction"""
        for name, thread_data in self.threads.items():
            thread = thread_data['thread']
            if thread.isRunning():
                thread.quit()
                thread.wait()