import pymysql
import time
from datetime import datetime, timedelta
from PyQt6.QtCore import pyqtSignal, QObject, QTimer
from PyQt6.QtWidgets import QTableWidgetItem, QTableWidget, QLabel, QToolTip
import json
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler()])

class RankingSignals(QObject):
    data_updated = pyqtSignal(list)
    club_ranking_updated = pyqtSignal(list)
    individual_ranking_updated = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

class RankingModule:
    def __init__(self, parent):
        self.parent = parent
        self.config = self.load_config()
        self.signals = RankingSignals()
        self.running = False

        self.signals.data_updated.connect(self.update_table)
        self.signals.club_ranking_updated.connect(self.update_club_labels)
        self.signals.individual_ranking_updated.connect(self.update_individual_labels)
        self.signals.error_occurred.connect(self.show_error)

        if self.config:
            try:
                self.fetch_and_process_data()
                self.start_fetching()
            except Exception as e:
                self.signals.error_occurred.emit(f"初始化失败: {str(e)}")
        else:
            self.signals.error_occurred.emit("无法加载配置文件")

    def load_config(self):
        config_path = './data/score_db_config.json'
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    required_fields = ['host', 'user', 'password', 'database', 'port', 'table_name']
                    if all(field in config for field in required_fields):
                        return config
                    else:
                        missing = [f for f in required_fields if f not in config]
                        self.signals.error_occurred.emit(f"配置文件缺少字段: {', '.join(missing)}")
                        return None
            else:
                self.signals.error_occurred.emit("配置文件不存在")
                return None
        except Exception as e:
            self.signals.error_occurred.emit(f"加载配置文件失败: {str(e)}")
            return None

    def start_fetching(self):
        self.running = True
        self.timer = QTimer()
        self.timer.timeout.connect(self.fetch_and_process_data)
        self.timer.start(600000)

    def stop(self):
        self.running = False
        if hasattr(self, 'timer'):
            self.timer.stop()

    def get_week_range(self):
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        return start_of_week.replace(hour=0, minute=0, second=0), end_of_week.replace(hour=23, minute=59, second=59)

    def fetch_and_process_data(self):
        try:
            db_config = {
                'host': self.config['host'],
                'user': self.config['user'],
                'password': self.config['password'],
                'database': self.config['database'],
                'port': int(self.config['port'])
            }
            logging.info(f"尝试连接数据库: {db_config}")
            with pymysql.connect(
                **db_config,
                cursorclass=pymysql.cursors.DictCursor
            ) as conn:
                with conn.cursor() as cursor:
                    start_date, end_date = self.get_week_range()
                    logging.info(f"查询时间范围: {start_date} - {end_date}")
                    query = f"""
                        SELECT * FROM `{self.config['table_name']}` 
                        WHERE `record-time` BETWEEN %s AND %s
                        ORDER BY `record-time` DESC
                    """
                    cursor.execute(query, (start_date, end_date))
                    data = cursor.fetchall()
                    logging.info(f"查询到 {len(data)} 条记录")

                    self.signals.data_updated.emit(data)

                    club_scores = {}
                    for row in data:
                        club = row['club']
                        mark = row['mark']
                        if mark is not None:
                            club_scores[club] = club_scores.get(club, 0) + float(mark)
                        else:
                            logging.warning(f"记录 {row['id']} 的 mark 为空，跳过俱乐部排名计算")
                    club_ranking = sorted(club_scores.items(), key=lambda x: x[1], reverse=True)
                    self.signals.club_ranking_updated.emit(club_ranking)

                    individual_scores = {}
                    for row in data:
                        name = row['name']
                        mark = row['mark']
                        if mark is not None:
                            individual_scores[name] = individual_scores.get(name, 0) + float(mark)
                        else:
                            logging.warning(f"记录 {row['id']} 的 mark 为空，跳过个人排名计算")
                    individual_ranking = sorted(individual_scores.items(), key=lambda x: x[1], reverse=True)
                    self.signals.individual_ranking_updated.emit(individual_ranking)

        except pymysql.MySQLError as e:
            self.signals.error_occurred.emit(f"数据库错误: {str(e)}")
        except Exception as e:
            self.signals.error_occurred.emit(f"数据处理错误: {str(e)}")

    def update_table(self, data):
        table = self.parent.findChild(QTableWidget, "tableWidget")
        if not table:
            logging.error("找不到 tableWidget，请检查 UI 文件")
            self.signals.error_occurred.emit("找不到 tableWidget")
            return

        logging.info(f"更新表格数据，行数: {len(data)}")
        table.setRowCount(len(data))
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels(['ID', '上传时间', '记录时间', '俱乐部', '姓名', '分数', '备注', '操作员'])

        try:
            table.cellClicked.disconnect()
        except Exception:
            pass
        table.cellClicked.connect(self.show_tooltip_on_click)

        for row_idx, row_data in enumerate(data):
            items = [
                str(row_data.get('id', '')),
                str(row_data.get('upload-time', '')),
                str(row_data.get('record-time', '')),
                row_data.get('club', ''),
                row_data.get('name', ''),
                str(row_data.get('mark', '0')),
                row_data.get('note', '') or '',
                row_data.get('operator', '') or ''
            ]
            for col_idx, item in enumerate(items):
                table_item = QTableWidgetItem(item)
                table_item.setToolTip(item)
                table.setItem(row_idx, col_idx, table_item)

    def show_tooltip_on_click(self, row, column):
        table = self.parent.findChild(QTableWidget, "tableWidget")
        if table:
            item = table.item(row, column)
            if item:
                text = item.toolTip()
                if text:
                    cell_rect = table.visualItemRect(item)
                    pos = table.viewport().mapToGlobal(cell_rect.topLeft())
                    QToolTip.showText(pos, text, table)
                    logging.info(f"点击显示工具提示: {text}")

    def update_club_labels(self, ranking):
        labels = [
            self.parent.findChild(QLabel, "label_8"),
            self.parent.findChild(QLabel, "label_9"),
            self.parent.findChild(QLabel, "label_10")
        ]
        for i, label in enumerate(labels):
            if not label:
                self.signals.error_occurred.emit(f"找不到 label_{8 + i}")
                continue
            if i < len(ranking):
                club, score = ranking[i]
                label.setText(f"{club}: {score}")
            else:
                label.setText("待补位")

    def update_individual_labels(self, ranking):
        labels = [
            self.parent.findChild(QLabel, "label_11"),
            self.parent.findChild(QLabel, "label_12"),
            self.parent.findChild(QLabel, "label_13")
        ]
        for i, label in enumerate(labels):
            if not label:
                self.signals.error_occurred.emit(f"找不到 label_{11 + i}")
                continue
            if i < len(ranking):
                name, score = ranking[i]
                label.setText(f"{name}: {score}")
            else:
                label.setText("待补位")

    def show_error(self, message):
        table = self.parent.findChild(QTableWidget, "tableWidget")
        if table:
            logging.info(f"显示错误信息: {message}")
            table.clear()
            table.setRowCount(1)
            table.setColumnCount(1)
            table.setHorizontalHeaderLabels(["错误信息"])
            try:
                table.cellClicked.disconnect()
            except Exception:
                pass
            table.cellClicked.connect(self.show_tooltip_on_click)
            table_item = QTableWidgetItem(message)
            table_item.setToolTip(message)
            table.setItem(0, 0, table_item)
        else:
            logging.error("无法显示错误，因为 tableWidget 未找到")