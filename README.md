# Education Clock v3.12

> [!NOTE]
>
> 软件具有-桌面时钟 -课程表 -天气预报 -自动新闻联播 -定时关机 -消息通知栏 -随机点名-噪声超标预警等功能

![-Education Clock.png](https://s2.loli.net/2024/12/08/K8Dedr6xpkSvyPa.png)

# 信息

版本：v3.10

时间：2025年3月2日

协议：GPLv3

GitHub仓库: https://github.com/Return-Log/Education-Clock

有建议与问题请提交Issues: https://github.com/Return-Log/Education-Clock/issues

# 功能说明

> [!WARNING]
>
> 设置信息存储在./data下，修改设置会自动保存，操作不可逆，请注意进行数据备份

## 课程表

### 显示课程表

到达设定时间后对应课程加粗并使用高亮边框

主界面可以选择显示其它时间课程表以适应调休

### 更改课程表

> [!WARNING]
>
> 修改项后务必点击表格空白处以保存，直接关闭窗口可能会导致数据丢失

#### 插入课程表

对应日期为空时，点插入行按钮会自动添加一行

不为空时需选择一行，点击插入按钮会在选中行下方插入一行

#### 删除课程表

选中要删除的行点击删除按钮即可删除

#### 更改课程表

双击需更改的单元格即可进行更改

日期须符合HH:MM格式

## 倒计时

### 设置

事件最多4个字符，也不要设置过长的倒计时(大于9999天)，否则会导致窗口显示超出范围

## 天气预报

使用和风天气的格点天气服务

API可在和风天气开发平台自行注册获得

> [!CAUTION]
>
> 注意经纬度不要填反

## 通知栏

### 信息显示规则

- 以时间倒序显示近7天数据

- 最新消息以弹幕形式在屏幕上滚动

- 支持markdown格式

- 当过滤群组名字包含“管理组”关键字时，对应群组信息头用黄色显示

> [!WARNING]
>
> 通知栏信息编码为base64加密存储，只能在设置界面更改

### 本地公告板设置

公告板现支持md格式解析，图片解析，视频、文档等文件保存与快速打开

#### 按设置界面提示填写远程数据库信息

#### 过滤设置

- 可选机器人名称，发件人昵称，群聊名字进行过滤
- 有多个过滤项时使用逗号分隔
- 过滤项间彼此互不干扰

### 服务端设置

#### 数据库设置

数据库中构建如下表

```sql
CREATE TABLE IF NOT EXISTS `messages` (
    `id` INT AUTO_INCREMENT PRIMARY KEY, -- 自增主键
    `robot_name` VARCHAR(255) NOT NULL, -- 机器人名称
    `sender_name` VARCHAR(255) NOT NULL, -- 发送者名称
    `message_content` TEXT NOT NULL, -- 消息内容
    `timestamp` DATETIME NOT NULL, -- 时间戳
    `conversationTitle` VARCHAR(255) NOT NULL -- 群聊标题
);
```

> [!IMPORTANT]
>
> 记得放行 3306 MySQL服务默认端口

#### 添加数据

##### 本质

可以使用你自己的程序执行如下语句进行插入

```sql
INSERT INTO `messages` (`robot_name`, `sender_name`, `message_content`, `timestamp`, `conversationTitle`) VALUES
('机器人名字', '发送者名称', '展示的消息内容', '时间戳(2024-11-04 15:00:04)', '群聊名称');
```

##### 使用钉钉机器人

###### 在钉钉中创建机器人

> 需自建一个组织，机器人每月有3000次调用限制

开放平台传送门: https://open-dev.dingtalk.com/fe/app?hash=%23%2Fcorp%2Frobot#/corp/robot

在自建组织中创建一个机器人应用，将应用凭证中三个项记下来

对应机器人开发管理中添加服务器出口IP(调用钉钉服务端API时的合法IP列表)和消息接收地址(用于接收POST过来的消息)

###### 服务器配置

python版本: 3.10.14 使用flask框架

./dingtalk-service/app.py 为服务端需运行软件

将app.py中以下部分改为你自己的配置信息

```python
"""以省略上方代码"""

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

"""中间部分已省略"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10240, debug=True)  # 改为自己的端口
```

宝塔面板项目管理：

- 启动方式uwsgi
- 通讯协议wsgi
- 这里添加可外网访问的端口(提示冲突就更换一个)
- 添加可外网访问的域名

###### 使用机器人

在自建组织下添加一个内部群，添加上自定义机器人，@机器人 即可发送信息，一切顺利话此时数据库中已有这条信息

## 自动关机

一天中多个关机时间使用逗号分隔

到达时间会弹出确认倒计时窗口，点取消即可终止关机

## 新闻联播

到达7:30会自动使用默认浏览器访问央视网，根据是否有声音播放模拟鼠标双击进行全屏操作，到达7:30自动关闭浏览器窗口

模块默认为关闭状态

## 随机点名

双击悬浮小猫按钮即可打开窗口，点击窗口中任意位置即可开始点名

添加名字直接将excel表中整列名字复制粘贴即可(记得删掉表头和没用的换行符)

## 噪音检测



------

Copyright © 2024-2025  Log  All rights reserved.

