import requests
from bs4 import BeautifulSoup
import re
import json
import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from datetime import datetime


class WallpaperFetcher(QThread):
    """壁纸获取线程"""
    finished_signal = pyqtSignal(bool, str, str, str, str)  # 成功状态, 图片路径, 标题, 版权, 故事

    def __init__(self, parent=None):
        super().__init__(parent)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }

    def run(self):
        try:
            # 站点信息
            base_url = "https://peapix.com"
            cn_list_url = "https://peapix.com/bing/cn/"

            # 第一步：获取中文列表页，找到最新（当天）壁纸详情链接
            resp = requests.get(cn_list_url, headers=self.headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # peapix 的列表页是纯文本链接，href 如 /bing/54371
            # 找第一个匹配 /bing/数字 的 a 标签（最新的一条）
            detail_a = soup.find("a", href=re.compile(r"^/bing/\d+$"))
            if not detail_a:
                self.finished_signal.emit(False, "", "", "", "")
                return

            detail_path = detail_a["href"]
            detail_url = base_url + detail_path
            title_cn = detail_a.get_text(strip=True).split(',')[0]

            # 第二步：访问详情页，提取完整中文小故事
            detail_resp = requests.get(detail_url, headers=self.headers, timeout=15)
            detail_resp.raise_for_status()
            detail_soup = BeautifulSoup(detail_resp.text, "html.parser")

            # 标题确认（h1 或类似）
            h1 = detail_soup.find("h1")
            title = h1.get_text(strip=True) if h1 else title_cn

            # 完整中文小故事：拼接所有 <p> 标签文本
            paragraphs = detail_soup.find_all("p")
            story = "\n".join(
                p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True) and not p.find("strong"))
            if not story:
                story = "未找到完整中文小故事"

            # 第三步：用微软官方API获取中国版（zh-CN）当天图片信息，并构建4K URL
            api_url = "https://cn.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=zh-CN"
            api_resp = requests.get(api_url, headers=self.headers).json()
            image_info = api_resp["images"][0]

            urlbase = image_info["urlbase"]
            copyright_short = image_info["copyright"]

            # 优先构建4K UHD URL
            uhd_url = f"https://cn.bing.com{urlbase}_UHD.jpg"

            # 检查4K是否可用
            head = requests.head(uhd_url, headers=self.headers, allow_redirects=True)
            if head.status_code != 200 or int(head.headers.get('Content-Length', 0)) < 100000:
                uhd_url = f"https://cn.bing.com{urlbase}_1920x1080.jpg"

            # 下载图片
            img_data = requests.get(uhd_url, headers=self.headers).content
            today = datetime.now().strftime("%Y-%m-%d")
            filename = f"./data/download/bing_cn_{today}.jpg"

            # 确保下载目录存在
            os.makedirs("./data/download", exist_ok=True)

            with open(filename, "wb") as f:
                f.write(img_data)

            self.finished_signal.emit(True, filename, title, copyright_short, story)
        except Exception as e:
            print(f"获取壁纸失败: {e}")
            self.finished_signal.emit(False, "", "", "", "")


class WallpaperModule(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.wallpaper_data = {}
        self.wallpaper_fetcher = None
        self.load_wallpaper_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 使用单个文本浏览器显示所有内容
        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(False)  # 禁用外部链接
        self.content_browser.setStyleSheet("""
            QTextBrowser {
                border: none;
                font-size: 14px;
                line-height: 1.5;
            }
        """)
        layout.addWidget(self.content_browser)

    def load_wallpaper_data(self):
        try:
            with open('./data/wallpaper.json', 'r', encoding='utf-8') as f:
                self.wallpaper_data = json.load(f)
        except FileNotFoundError:
            self.wallpaper_data = {
                "获取每日一图": "True",
                "设置为壁纸": "True",
                "最新获取": {
                    "日期": "",
                    "图片名": "",
                    "描述": ""
                }
            }

    def save_wallpaper_data(self):
        with open('./data/wallpaper.json', 'w', encoding='utf-8') as f:
            json.dump(self.wallpaper_data, f, ensure_ascii=False, indent=2)

    def fetch_wallpaper_async(self):
        """异步获取壁纸"""
        # 检查是否需要更新（如果不是同一天）
        today = datetime.now().strftime("%Y-%m-%d")
        latest_data = self.wallpaper_data.get("最新获取", {})

        if latest_data.get("日期") == today:
            # 如果是同一天，直接使用本地数据
            image_filename = latest_data.get("图片名", "")

            # 处理不同版本的数据结构
            if "简短描述" in latest_data and "完整描述" in latest_data:
                # 新数据结构
                short_desc = latest_data.get("简短描述", "")
                full_desc = latest_data.get("完整描述", "")
            else:
                # 旧数据结构兼容
                desc = latest_data.get("描述", "")
                lines = desc.split('\n') if desc else []
                short_desc = lines[0] if lines else ""
                full_desc = desc

            # 检查本地文件是否存在
            if os.path.exists(image_filename):
                # 直接显示本地数据
                self.display_wallpaper(image_filename, "今日壁纸", short_desc, full_desc)

                # 如果需要设置为壁纸
                if self.wallpaper_data.get("设置为壁纸") == "True":
                    self.set_as_wallpaper(image_filename)
                return
            else:
                # 本地文件不存在，需要重新获取
                pass

        # 创建并启动壁纸获取线程
        if self.wallpaper_fetcher is None or not self.wallpaper_fetcher.isRunning():
            self.wallpaper_fetcher = WallpaperFetcher(self)
            self.wallpaper_fetcher.finished_signal.connect(self.on_wallpaper_fetched)
            self.wallpaper_fetcher.start()

    def on_wallpaper_fetched(self, success, image_path, title, short_description, full_story):
        """壁纸获取完成回调"""
        if success:
            # 更新数据
            today = datetime.now().strftime("%Y-%m-%d")
            self.wallpaper_data["最新获取"] = {
                "日期": today,
                "图片名": image_path,
                "简短描述": short_description,
                "完整描述": full_story
            }
            self.save_wallpaper_data()

            # 显示壁纸信息
            self.display_wallpaper(image_path, title, short_description, full_story)

            # 如果需要设置为壁纸
            if self.wallpaper_data.get("设置为壁纸") == "True":
                self.set_as_wallpaper(image_path)
        else:
            # 获取失败，尝试显示本地已有的壁纸
            latest_data = self.wallpaper_data.get("最新获取", {})
            image_filename = latest_data.get("图片名", "")
            short_desc = latest_data.get("简短描述", "")
            full_desc = latest_data.get("完整描述", "")

            if os.path.exists(image_filename):
                self.display_wallpaper(image_filename, "今日壁纸", short_desc, full_desc)
            else:
                self.display_wallpaper("", "今日壁纸", "暂无壁纸", "")

    def display_wallpaper(self, image_path="", title="今日壁纸", short_description="", full_story=""):
        html_content = ""

        if os.path.exists(image_path) and image_path:
            # 构建HTML内容，包含图片和描述
            html_content = f"""
            <div style="text-align: center;">
                <img src="{os.path.abspath(image_path)}" style="max-width: 100%; height: auto; border-radius: 8px;" />
            </div>
            <div style="margin-top: 15px;">
                <p style="margin: 15px 0;"><strong>{short_description}</strong></p>
                <div style="margin-top: 15px;">
                    <p style="margin: 10px 0; line-height: 1;">{full_story.replace(chr(10), '<br>')}</p>
                </div>
            </div>
            """
        else:
            # 显示无壁纸信息
            html_content = """
            <div style="text-align: center; padding: 40px 0;">
                <p style="font-size: 16px;">暂无壁纸</p>
            </div>
            """

        self.content_browser.setHtml(html_content)

    def set_as_wallpaper(self, image_path):
        try:
            import ctypes
            ctypes.windll.user32.SystemParametersInfoW(20, 0, os.path.abspath(image_path), 3)
        except Exception as e:
            print(f"设置壁纸失败: {e}")