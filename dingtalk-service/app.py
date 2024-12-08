from flask import Flask, request, jsonify
import hashlib
import hmac
import base64
import pymysql
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# 数据库配置
db_config = {  # 数据库配置
    "host": "localhost",
    "user": "",
    "password": "",
    "database": ""
}

# 钉钉机器人配置（多个机器人）
robots = {  # 机器人应用凭证
    "": {  # AppKey
        "agent_id": "",  # AgentId
        "app_secret": ""  # AppSecret
    }
    # 可以继续增加更多的机器人配置
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
        logging.info("Database connection successful")
        return connection
    except Exception as e:
        logging.error(f"Database connection error: {e}")
        return None

def verify_signature(app_secret, timestamp, sign):
    string_to_sign = f'{timestamp}\n{app_secret}'
    hmac_code = hmac.new(app_secret.encode('utf-8'), string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    expected_sign = base64.b64encode(hmac_code).decode('utf-8')
    logging.debug(f"Expected Sign: {expected_sign}, Received Sign: {sign}")
    return expected_sign == sign

@app.route('/', methods=['POST'])
def root_webhook():
    logging.info("Received request at root path")

    # 获取请求数据并打印
    data = request.json
    logging.debug(f"Received data: {data}")

    # 获取机器人代码 (robotCode) 对应的 app_key
    robot_code = data.get('robotCode', None)

    # 检查 robotCode 是否有效，应该对应到 robots 中的 app_key
    if not robot_code or robot_code not in robots:
        logging.error("Invalid robotCode")
        return jsonify({"error": "机器人名称无效"}), 400

    # 获取机器人配置信息
    robot_info = robots[robot_code]
    app_secret = robot_info["app_secret"]

    # 获取签名信息
    timestamp = request.headers.get("timestamp")
    sign = request.headers.get("sign")
    logging.debug(f"Received timestamp: {timestamp}, sign: {sign}")

    # 验证签名
    if not verify_signature(app_secret, timestamp, sign):
        logging.error("Signature verification failed")
        return jsonify({"error": "签名验证失败"}), 403

    # 解析消息内容
    msgtype = data.get("msgtype")
    text_content = data.get("text", {}).get("content")
    sender_name = data.get("senderNick", "unknown_sender")
    conversationTitle = data.get("conversationTitle", "unknown_title")

    if not text_content:
        logging.error("Message content is empty")
        return jsonify({"error": "消息内容为空"}), 400

    # 处理数据库操作
    connection = get_db_connection()
    if connection is None:
        logging.error("Database connection failed")
        return jsonify({"error": "数据库连接失败"}), 500

    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO messages (robot_name, conversationTitle, sender_name, message_content) VALUES (%s, %s, %s, %s)"
            values = (robot_code, conversationTitle, sender_name, text_content)
            cursor.execute(sql, values)
            logging.info("Data inserted successfully")
        connection.commit()
    except Exception as e:
        logging.error(f"Error inserting data: {e}")
        connection.rollback()
    finally:
        connection.close()

    return jsonify({"status": "消息已接收并存储"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10240, debug=True)
