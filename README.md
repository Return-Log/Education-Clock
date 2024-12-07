# Education Clock v3.5 简介

> [!NOTE]
>
> 软件具有-桌面时钟 -课程表 -天气预报 -自动新闻联播 -定时关机 -消息通知栏 -随机点名等功能

![Snipaste_2024-10-27_14-46-12.png](https://s2.loli.net/2024/10/27/wC2fM1sVGmhSt6z.png)

# 信息

版本：v3.6

时间：2024年12月7日

协议：GPL-v3.0

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

## 通知栏

### 信息显示规则

- 以时间倒序显示近7天数据

- 支持markdown格式

- 当过滤群组名字包含“管理组”关键字时，对应群组信息头用黄色显示

> [!WARNING]
>
> 通知栏信息编码为base64加密存储，只能在设置界面更改

### 本地公告板设置

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

#### 添加数据

##### 本质

可以使用你自己的程序执行如下语句进行插入

```sql
INSERT INTO `messages` (`robot_name`, `sender_name`, `message_content`, `timestamp`, `conversationTitle`) VALUES
('机器人名字', '发送者名称', '展示的消息内容', '时间戳(2024-11-04 15:00:04)', '群聊名称');
```

##### 使用钉钉机器人

./dingtalk-service/app.py 为服务端需运行软件



------

Copyright © 2024  Log  All rights reserved.

