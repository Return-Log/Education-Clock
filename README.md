# Education Clock

> [!NOTE]
>
> 软件具有-桌面时钟 -课程表 -天气预报 -自动新闻联播 -定时关机 -消息通知栏 -随机点名 -新闻看板 -定时消息等功能

![-Education Clock.png](https://s2.loli.net/2024/12/08/K8Dedr6xpkSvyPa.png)

# 信息

协议：GPLv3

GitHub仓库: https://github.com/Return-Log/Education-Clock

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

#### 按设置界面提示填写API信息

#### 过滤设置

- 可选发件人昵称，群聊名字进行过滤
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

开放平台: https://open-dev.dingtalk.com/fe/app?hash=%23%2Fcorp%2Frobot#/corp/robot

在自建组织中创建一个机器人应用，将应用凭证中三个项记下来

对应机器人开发管理中添加服务器出口IP，和消息接收地址

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
    "": {  # ""中填写AppKey
        "agent_id": "",  # AgentId
        "app_secret": ""  # AppSecret
    }
    # 可以继续增加更多的机器人配置
}

"""中间部分已省略"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=20000, debug=True)  # 改为自己的端口
```

宝塔面板网站管理：

添加一个python项目

![PixPin_2025-04-20_10-25-45.png](https://s2.loli.net/2025/04/20/3dPy5cEkjXCWBZD.png)

![PixPin_2025-04-20_10-27-26.png](https://s2.loli.net/2025/04/20/iDwXfLAESkouZtv.png)

![PixPin_2025-04-20_10-28-39.png](https://s2.loli.net/2025/04/20/7duRjbvg84sPqSY.png)

![PixPin_2025-04-20_10-30-40.png](https://s2.loli.net/2025/04/20/X8vfqKjzDPacN65.png)

```
所需的库，装最新版即可
flask  # 用于创建 Web 应用程序
pymysql  # 用于连接和操作 MySQL 数据库
alibabacloud-dingtalk  # 用于调用钉钉的 API
alibabacloud-tea-openapi  # 钉钉 SDK 依赖的 Alibaba Cloud TEA OpenAPI 库
alibabacloud-tea-util  # 钉钉 SDK 依赖的 TEA 工具库
```

最后重启项目

###### 使用机器人

在自建组织下添加一个内部群，添加上自定义机器人，@机器人 即可发送信息，一切顺利话此时数据库中已有这条信息

## 自动关机

一天中多个关机时间使用逗号分隔

到达时间会弹出确认倒计时窗口，点取消即可终止关机

## 新闻联播

到达7:30会自动使用默认浏览器访问央视网，根据是否有声音播放模拟鼠标双击进行全屏操作，到达7:30自动关闭浏览器窗口

模块默认为关闭状态

## 悬浮球

点击小猫悬浮球可打开工具栏，目前有随机点名、通知消息本地发送功能

## API调用（新闻看板）

显示效果

![PixPin_2025-05-11_01-17-31.png](https://s2.loli.net/2025/05/11/1xKqRodS5mn2u9c.png)

### 设置

![PixPin_2025-05-11_01-18-49.png](https://s2.loli.net/2025/05/11/asMZ7bqpWf295V6.png)

目前只能解析新闻类API（需要显示的项都在"data"下）

使用md格式，API中的内容显示需加{}，如上图所示

## 计时器

从悬浮窗启动

具有秒表和倒计时功能

![PixPin_2025-06-15_12-46-07.png](https://s2.loli.net/2025/06/15/ktYLZg6Q1hNWcl5.png)

## 计划消息

可设置定时消息和循环消息，定时消息中设置为Sunday等可实现每周显示

---

![.png](https://s2.loli.net/2025/06/15/bBKPC7ATZ5UFpRf.png)

------

Copyright © 2024-2025  Log  All rights reserved.

