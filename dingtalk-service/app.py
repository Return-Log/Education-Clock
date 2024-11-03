from flask import Flask, request, jsonify
import hashlib
import hmac
import base64
import pymysql
import json
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# 数据库配置
db_config = {
    "host": "localhost",
    "user": "",
    "password": "",
    "database": ""
}

# 钉钉机器人配置
robots = {
    "29464001": {
        "agent_id": "",
        "app_key": "",
        "app_secret": ""
    }
}

def get_db_connection():
    try:
        connection = pymysql.connect(
            host=db_config["host"],
            user=db_config["user"],
            password=db_config["password"],
            database=db_config["database"],
            cursorclass=pymysql.cursors.DictCursor
        )
        logging.info("Database connection successful")  # 打印数据库连接成功的日志
        return connection
    except Exception as e:
        logging.error(f"Database connection error: {e}")  # 打印数据库连接失败的错误信息
        return None

def verify_signature(app_secret, timestamp, sign):
    string_to_sign = f'{timestamp}\n{app_secret}'
    hmac_code = hmac.new(app_secret.encode('utf-8'), string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    expected_sign = base64.b64encode(hmac_code).decode('utf-8')
    logging.debug(f"Expected Sign: {expected_sign}, Received Sign: {sign}")  # 调试签名
    if expected_sign != sign:
        logging.error("Signature verification failed")  # 调试签名验证失败
    return expected_sign == sign

@app.route('/', methods=['POST'])
def root_webhook():
    logging.info("Received request at root path")
    return receive_message('29464001')

@app.route('/webhook/<robot_name>', methods=['POST'])
def receive_message(robot_name):
    logging.info(f"Received request for robot: {robot_name}")  # 打印收到请求的日志

    if robot_name not in robots:
        logging.error("Invalid robot name")
        return jsonify({"error": "机器人名称无效"}), 400

    robot_info = robots[robot_name]
    app_secret = robot_info["app_secret"]

    timestamp = request.headers.get("timestamp")
    sign = request.headers.get("sign")

    if not verify_signature(app_secret, timestamp, sign):
        logging.error("Signature verification failed")
        return jsonify({"error": "签名验证失败"}), 403

    data = request.json
    logging.debug(f"Received data: {data}")  # 打印接收到的数据

    # 解析消息内容
    msgtype = data.get("msgtype")
    text_content = data.get("text", {}).get("content")
    sender_name = data.get("senderNick", "unknown_sender")
    conversationTitle = data.get("conversationTitle", "unknown_title")

    if not text_content:
        logging.error("Message content is empty")
        return jsonify({"error": "消息内容为空"}), 400

    connection = get_db_connection()
    if connection is None:
        logging.error("Database connection failed")
        return jsonify({"error": "数据库连接失败"}), 500

    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO messages (robot_name, conversationTitle, sender_name, message_content) VALUES (%s, %s, %s, %s)"
            values = (robot_name, conversationTitle, sender_name, text_content)
            cursor.execute(sql, values)
            logging.info("Data inserted successfully")  # 打印插入成功的日志
        connection.commit()
    except Exception as e:
        logging.error(f"Error inserting data: {e}")  # 打印插入失败的错误信息
        connection.rollback()
    finally:
        connection.close()

    return jsonify({"status": "消息已接收并存储"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10086, debug=True)