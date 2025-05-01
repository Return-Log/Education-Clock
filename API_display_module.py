import sys
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                            QWidget, QTextEdit, QTextBrowser, QLineEdit,
                            QPushButton, QLabel)
from PyQt6.QtCore import Qt

class NewsDisplayApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("News Display")
        self.setGeometry(100, 100, 800, 600)

        # Sample JSON data
        self.data = [
            {
                "title": "约旦专栏作家：中国外交坚持和平、理性，具有战略定力",
                "time": "2025-02-23 16:49:37",
                "url": "https://news.cctv.com/2025/02/23/ARTISpTAxMypj7oEmVym2Mkf250223.shtml",
                "poster": "https://p2.img.cctvpic.com/photoworkspace/2025/02/23/2025022316162255921.jpg",
                "description": "约旦专栏作家法里斯·哈巴什奈近日在当地主流媒体《宪章报》发表文章，强调中国外交坚持和平、理性，具有战略定力。",
                "keywords": "约旦 定力 专栏作家 宪章报 外交政策 联合国"
            },
            {
                "title": "俄副外长：俄美代表第二轮会谈将在利雅得举行",
                "time": "2025-02-23 16:07:57",
                "url": "https://news.cctv.com/2025/02/23/ARTIT58svDwybTe1mXiPTxls250223.shtml",
                "poster": "https://p2.img.cctvpic.com/photoworkspace/2025/02/23/2025022316072814743.jpg",
                "description": "总台记者获悉，俄罗斯外交部副部长里亚布科夫当地时间23日向俄罗斯《消息报》透露，俄罗斯和美国将在沙特首都利雅得举行下一次关于乌克兰问题的会谈，将由各部门司局长级官员出席，而非副部长级别官员出席。",
                "keywords": "会谈 利雅得 俄美"
            },
            {
                "title": "中国驻旧金山总领馆提醒：中国公民谨防换汇诈骗",
                "time": "2025-02-22 07:25:07",
                "url": "https://news.cctv.com/2025/02/22/ARTImuA66iAXhQAFw2XsDOvS250222.shtml",
                "poster": "https://p5.img.cctvpic.com/photoworkspace/2025/02/22/2025022211021193492.png",
                "description": "近期，中国驻旧金山总领事馆接到多名中国公民求助，反映遭遇换汇诈骗。",
                "keywords": "换汇 中国公民 诈骗分子"
            }
        ]

        # Initialize UI
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Filter input
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter (keywords):")
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Enter keywords to filter title or description")
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_input)
        layout.addLayout(filter_layout)

        # Template input
        template_label = QLabel("Markdown Template:")
        layout.addWidget(template_label)
        self.template_input = QTextEdit()
        self.template_input.setPlaceholderText(
            "Enter Markdown template, e.g:\n# {title}\n![Poster]({poster})\n[Read More]({url})\nAvailable fields: {title}, {time}, {url}, {poster}, {description}, {keywords}"
        )
        self.template_input.setText(
            "# {title}\n*Posted on {time}*\n\n![Poster]({poster})\n\n{description}\n\n[Read More]({url})\n\n**Keywords**: {keywords}\n\n---"
        )
        layout.addWidget(self.template_input)

        # Buttons
        button_layout = QHBoxLayout()
        apply_button = QPushButton("Apply Template")
        apply_button.clicked.connect(self.apply_template)
        clear_button = QPushButton("Clear Output")
        clear_button.clicked.connect(self.clear_output)
        button_layout.addWidget(apply_button)
        button_layout.addWidget(clear_button)
        layout.addLayout(button_layout)

        # Output display
        output_label = QLabel("Output:")
        layout.addWidget(output_label)
        self.output_browser = QTextBrowser()
        self.output_browser.setOpenExternalLinks(True)
        layout.addWidget(self.output_browser)

    def apply_template(self):
        template = self.template_input.toPlainText()
        filter_text = self.filter_input.text().strip().lower()

        # Filter data
        filtered_data = self.data
        if filter_text:
            filtered_data = [
                item for item in self.data
                if (filter_text in item["title"].lower() or
                    filter_text in item["description"].lower())
            ]

        # Generate Markdown output
        markdown_output = ""
        for item in filtered_data:
            # Replace placeholders with actual values
            item_output = template
            for key in item:
                placeholder = "{" + key + "}"
                value = str(item[key]).replace("\n", " ")  # Prevent Markdown breaking
                item_output = item_output.replace(placeholder, value)
            markdown_output += item_output + "\n"

        # Display in browser
        self.output_browser.setMarkdown(markdown_output)

    def clear_output(self):
        self.output_browser.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NewsDisplayApp()
    window.show()
    sys.exit(app.exec())