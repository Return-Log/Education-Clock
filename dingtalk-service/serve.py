from flask import Flask, request, jsonify
import hashlib
import hmac
import base64
import pymysql
import logging
import time
from typing import List, Dict
from alibabacloud_dingtalk.robot_1_0.client import Client as dingtalkrobot_1_0Client
from alibabacloud_dingtalk.oauth2_1_0.client import Client as dingtalkoauth2_1_0Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dingtalk.robot_1_0 import models as dingtalkrobot__1__0_models
from alibabacloud_dingtalk.oauth2_1_0 import models as dingtalkoauth2__1__0_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient
import json
import threading
import uuid
from datetime import datetime, timedelta
import secrets

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
# 生成一个安全的随机密钥
app.config['SECRET_KEY'] = secrets.token_hex(16)

# 解决跨域问题
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


# 数据库配置
db_config = {
    "host": "localhost",
    "user": "",
    "password": "",
    "database": ""
}

# 钉钉机器人配置（多个机器人）
robots = {
    "": {  # AppKey
        "agent_id": "",  # 在""中填写AgentId
        "app_secret": ""  # 在""中填写AppSecret
    }
    # 可以继续增加更多的机器人配置
}

# 缓存 access_token 的字典，格式: {robot_code: {"token": token, "expire_time": expire_time}}
access_token_cache: Dict[str, dict] = {}


# ==================== 工具函数 ====================

# 创建钉钉客户端
def create_dingtalk_client() -> dingtalkrobot_1_0Client:
    """使用默认配置初始化钉钉机器人客户端"""
    config = open_api_models.Config()
    config.protocol = 'https'
    config.region_id = 'central'
    return dingtalkrobot_1_0Client(config)


def create_oauth_client() -> dingtalkoauth2_1_0Client:
    """使用默认配置初始化钉钉 OAuth 客户端"""
    config = open_api_models.Config()
    config.protocol = 'https'
    config.region_id = 'central'
    return dingtalkoauth2_1_0Client(config)


# 获取数据库连接
def get_db_connection():
    """连接到数据库并返回连接对象"""
    try:
        connection = pymysql.connect(
            host=db_config["host"],
            user=db_config["user"],
            password=db_config["password"],
            database=db_config["database"],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
        logging.info("数据库连接成功")
        return connection
    except Exception as e:
        logging.error(f"数据库连接错误: {e}")
        return None


# 获取 access_token
def get_access_token(robot_code: str) -> str:
    """根据 robotCode 获取 access_token，若缓存有效则返回缓存，否则重新请求"""
    if robot_code not in robots:
        logging.error(f"无效的 robotCode: {robot_code}")
        return ""

    app_key = robot_code  # robotCode 通常即为 AppKey
    app_secret = robots[robot_code]["app_secret"]

    # 检查缓存
    current_time = int(time.time() * 1000)  # 当前时间（毫秒）
    cached = access_token_cache.get(robot_code, {})
    if cached and cached.get("expire_time", 0) > current_time + 60000:  # 提前 1 分钟刷新
        logging.info(f"使用缓存的 access_token for {robot_code}")
        return cached["token"]

    # 请求新的 access_token
    client = create_oauth_client()
    request = dingtalkoauth2__1__0_models.GetAccessTokenRequest(
        app_key=app_key,
        app_secret=app_secret
    )
    try:
        response = client.get_access_token(request)
        access_token = response.body.access_token
        expires_in = response.body.expire_in * 1000  # 转换为毫秒
        expire_time = current_time + expires_in

        # 更新缓存
        access_token_cache[robot_code] = {
            "token": access_token,
            "expire_time": expire_time
        }
        logging.info(f"成功获取新的 access_token for {robot_code}, 有效期至: {expire_time}")
        return access_token
    except Exception as e:
        logging.error(f"获取 access_token 失败 for {robot_code}: {e}")
        return ""


# 验证签名
def verify_signature(app_secret, timestamp, sign):
    """验证请求的签名是否有效"""
    string_to_sign = f'{timestamp}\n{app_secret}'
    hmac_code = hmac.new(app_secret.encode('utf-8'), string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    expected_sign = base64.b64encode(hmac_code).decode('utf-8')
    logging.debug(f"预期签名: {expected_sign}, 收到签名: {sign}")
    return expected_sign == sign


# 将 downloadCode 转换为下载链接
def get_download_url(download_code: str, robot_code: str, access_token: str) -> str:
    """通过钉钉 API 将 downloadCode 转换为下载链接"""
    client = create_dingtalk_client()
    headers = dingtalkrobot__1__0_models.RobotMessageFileDownloadHeaders()
    headers.x_acs_dingtalk_access_token = access_token
    request = dingtalkrobot__1__0_models.RobotMessageFileDownloadRequest(
        download_code=download_code,
        robot_code=robot_code
    )
    try:
        response = client.robot_message_file_download_with_options(request, headers, util_models.RuntimeOptions())
        return response.body.download_url if hasattr(response.body, 'download_url') else "转换失败"
    except Exception as err:
        logging.error(f"获取下载链接失败: {err}")
        return f"获取下载链接失败: {err}"


# 处理消息内容
def process_message_content(data: dict, robot_code: str, access_token: str) -> str:
    """根据消息类型处理内容，返回适合存储的 text_content"""
    msgtype = data.get("msgtype")
    content = data.get("content", {})

    if msgtype == "text":
        return data.get("text", {}).get("content", "")
    elif msgtype == "richText":
        rich_text = content.get("richText", [])
        text_content = ""
        for item in rich_text:
            if "text" in item:
                text_content += item["text"] + " "
            elif "downloadCode" in item and item.get("type") == "picture":
                download_url = get_download_url(item["downloadCode"], robot_code, access_token)
                text_content += f"&[{download_url}]&"
        return text_content.strip()
    elif msgtype == "picture":
        download_code = content.get("downloadCode")
        if download_code:
            return f"&[{get_download_url(download_code, robot_code, access_token)}]&"
    elif msgtype == "audio":
        download_code = content.get("downloadCode")
        recognition = content.get("recognition", "")
        duration = content.get("duration", 0)
        if download_code:
            download_url = get_download_url(download_code, robot_code, access_token)
            return f"&[{download_url}]& 时长: {duration}ms, 识别内容: {recognition}"
    elif msgtype == "video":
        download_code = content.get("downloadCode")
        duration = content.get("duration", 0)
        video_type = content.get("videoType", "")
        if download_code:
            download_url = get_download_url(download_code, robot_code, access_token)
            return f"&[{download_url}]& 时长: {duration}ms, 类型: {video_type}"
    elif msgtype == "file":
        download_code = content.get("downloadCode")
        file_name = content.get("fileName", "")
        if download_code:
            download_url = get_download_url(download_code, robot_code, access_token)
            return f"&[{download_url}]& 文件名: {file_name}"
    return "未知消息类型"


# 获取近7天的消息
def get_recent_messages():
    """获取近7天的消息"""
    logging.info("开始查询近7天的消息")
    connection = get_db_connection()
    if connection is None:
        logging.error("数据库连接失败")
        return []

    try:
        with connection.cursor() as cursor:
            # 查询近7天的消息（使用 timestamp 字段）
            sql = """
                SELECT id, robot_name, conversationTitle, sender_name, message_content, timestamp
                FROM messages 
                WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                ORDER BY timestamp DESC
            """
            logging.debug(f"执行SQL查询: {sql}")
            cursor.execute(sql)
            rows = cursor.fetchall()
            logging.info(f"查询完成，找到 {len(rows)} 条消息")

            # 记录前几条消息作为示例
            for i, row in enumerate(rows[:3]):
                logging.debug(f"示例消息 {i + 1}: {row}")

            return rows
    except Exception as e:
        logging.error(f"查询消息错误: {e}", exc_info=True)
        return []
    finally:
        connection.close()


# 过滤消息数据
def filter_messages(rows, filter_conditions):
    """根据过滤条件过滤消息数据"""
    logging.info(f"开始过滤 {len(rows)} 条消息，过滤条件: {filter_conditions}")

    sender_names = filter_conditions.get("sender_names", [])
    conversation_titles = filter_conditions.get("conversation_titles", [])

    logging.info(f"发送者过滤条件: {sender_names}")
    logging.info(f"群聊标题过滤条件: {conversation_titles}")

    # 如果两个过滤条件都为空，则返回空列表
    if not sender_names and not conversation_titles:
        logging.info("两个过滤条件都为空，返回空列表")
        return []

    filtered_rows = []
    for i, row in enumerate(rows):
        try:
            sender_match = False
            title_match = False

            # 检查发送者匹配（如果发送者过滤条件为空，则视为匹配）
            if not sender_names:
                sender_match = True
            else:
                sender_match = row.get('sender_name', '') in sender_names

            # 检查群聊标题匹配（如果群聊标题过滤条件为空，则视为匹配）
            if not conversation_titles:
                title_match = True
            else:
                title_match = row.get('conversationTitle', '') in conversation_titles

            logging.debug(
                f"消息 {i + 1}: sender='{row.get('sender_name', '')}', title='{row.get('conversationTitle', '')}' "
                f"-> sender_match={sender_match}, title_match={title_match}")

            # 只要其中一个条件匹配就包含该消息（OR逻辑）
            if sender_match or title_match:
                filtered_rows.append(row)
        except Exception as e:
            logging.error(f"过滤消息时出错: {e}")
            # 出错时跳过该消息
            continue

    logging.info(f"过滤完成，{len(filtered_rows)}/{len(rows)} 条消息通过过滤")
    return filtered_rows


# ==================== 路由处理函数 ====================

@app.route('/', methods=['POST'])
def root_webhook():
    """处理钉钉机器人发送的 webhook 请求"""
    logging.info("收到根路径请求")

    # 获取请求数据并打印
    data = request.json
    logging.debug(f"收到数据: {data}")

    # 获取机器人代码 (robotCode) 对应的 app_key
    robot_code = data.get('robotCode', None)

    # 检查 robotCode 是否有效
    if not robot_code or robot_code not in robots:
        logging.error("无效的 robotCode")
        return jsonify({"error": "机器人名称无效"}), 400

    # 获取机器人配置信息
    robot_info = robots[robot_code]
    app_secret = robot_info["app_secret"]

    # 获取签名信息
    timestamp = request.headers.get("timestamp")
    sign = request.headers.get("sign")
    logging.debug(f"收到时间戳: {timestamp}, 签名: {sign}")

    # 验证签名
    if not verify_signature(app_secret, timestamp, sign):
        logging.error("签名验证失败")
        return jsonify({"error": "签名验证失败"}), 403

    # 获取 access_token
    access_token = get_access_token(robot_code)
    if not access_token:
        logging.error("无法获取 access_token")
        return jsonify({"error": "无法获取 access_token"}), 500

    # 处理消息内容
    text_content = process_message_content(data, robot_code, access_token)
    sender_name = data.get("senderNick", "unknown_sender")
    conversationTitle = data.get("conversationTitle", "unknown_title")

    if not text_content:
        logging.error("消息内容为空")
        return jsonify({"error": "消息内容为空"}), 400

    # 处理数据库操作
    connection = get_db_connection()
    if connection is None:
        logging.error("数据库连接失败")
        return jsonify({"error": "数据库连接失败"}), 500

    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO messages (robot_name, conversationTitle, sender_name, message_content) VALUES (%s, %s, %s, %s)"
            values = (robot_code, conversationTitle, sender_name, text_content)
            cursor.execute(sql, values)
            logging.info("数据插入成功")
        connection.commit()
    except Exception as e:
        logging.error(f"数据插入错误: {e}")
        connection.rollback()
    finally:
        connection.close()

    return jsonify({"status": "消息已接收并存储"}), 200


# API端点：获取消息
@app.route('/api/messages', methods=['GET'])
def get_messages():
    """获取符合过滤条件的消息"""
    try:
        # 获取过滤参数
        agent_id = request.args.get('agent_id')
        sender_names = request.args.get('sender_names')
        conversation_titles = request.args.get('conversation_titles')

        logging.info(f"收到消息请求 - Agent ID: {agent_id}")

        # 获取消息
        recent_messages = get_recent_messages()
        logging.info(f"从数据库获取到 {len(recent_messages)} 条消息（近7天）")

        # 如果指定了agent_id，则先根据robot_name过滤消息
        if agent_id:
            recent_messages = [msg for msg in recent_messages if msg.get('robot_name') == agent_id]
            logging.info(f"根据Agent ID ({agent_id}) 过滤后剩余 {len(recent_messages)} 条消息")

        # 构建过滤条件
        filter_conditions = {}
        if sender_names:
            filter_conditions["sender_names"] = sender_names.split(',')
            logging.info(f"发送者过滤: {filter_conditions['sender_names']}")
        if conversation_titles:
            filter_conditions["conversation_titles"] = conversation_titles.split(',')
            logging.info(f"群聊标题过滤: {filter_conditions['conversation_titles']}")

        # 如果有过滤条件，记录一些示例数据
        if recent_messages:
            logging.info(f"示例消息（前3条）:")
            for i, msg in enumerate(recent_messages[:3]):
                logging.info(
                    f"  消息 {i + 1}: sender='{msg.get('sender_name')}', title='{msg.get('conversationTitle')}', time='{msg.get('timestamp')}'")

        filtered_messages = filter_messages(recent_messages, filter_conditions)
        logging.info(f"过滤后剩余 {len(filtered_messages)} 条消息")

        # 如果过滤后没有消息，但原始有消息，记录过滤详情
        if len(filtered_messages) == 0 and len(recent_messages) > 0:
            logging.info("过滤条件导致所有消息被排除，检查过滤条件是否正确")
            logging.info(f"过滤条件: {filter_conditions}")

            # 显示一些实际数据供参考
            logging.info("实际数据示例:")
            for i, msg in enumerate(recent_messages[:5]):
                logging.info(
                    f"  实际消息 {i + 1}: sender='{msg.get('sender_name')}', title='{msg.get('conversationTitle')}'")

        response_data = {
            "type": "messages",
            "data": filtered_messages
        }

        logging.info(f"返回 {len(filtered_messages)} 条消息给客户端")
        return jsonify(response_data), 200
    except Exception as e:
        logging.error(f"获取消息失败: {e}", exc_info=True)
        return jsonify({"error": "获取消息失败", "details": str(e)}), 500


# 数据库诊断端点
@app.route('/diagnose', methods=['GET'])
def diagnose():
    """诊断数据库连接和数据状态"""
    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({"error": "数据库连接失败"}), 500

        with connection.cursor() as cursor:
            # 检查表结构
            cursor.execute("DESCRIBE messages")
            columns = cursor.fetchall()

            # 检查数据量
            cursor.execute("SELECT COUNT(*) as total FROM messages")
            total_count = cursor.fetchone()['total']

            # 检查最近7天的数据量
            cursor.execute("""
                SELECT COUNT(*) as recent_count 
                FROM messages 
                WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """)
            recent_count = cursor.fetchone()['recent_count']

            # 获取一些示例数据
            cursor.execute("""
                SELECT id, robot_name, conversationTitle, sender_name, timestamp
                FROM messages 
                ORDER BY timestamp DESC 
                LIMIT 3
            """)
            sample_data = cursor.fetchall()

        connection.close()

        return jsonify({
            "table_structure": columns,
            "total_messages": total_count,
            "recent_messages": recent_count,
            "sample_data": sample_data
        }), 200

    except Exception as e:
        logging.error(f"诊断错误: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# 健康检查端点
@app.route('/health')
def health_check():
    """健康检查端点"""
    return jsonify({"status": "healthy", "timestamp": time.time()}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=20000, debug=True, threaded=True)