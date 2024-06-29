# Education Clock v1.1 简介

**功能：**

-桌面时钟 -课程表 -天气预报 -自动新闻联播 -定时关机 -邮件公告板

![.png](https://s2.loli.net/2024/06/09/MPewgN6FvBSxKo2.png)

# 信息

版本：v1.1

时间：2024/6/30

协议：GPLv3

# 功能设置

## 一. 单独控制模块开关，调整设置

**可以单独控制模块是否启动**

启动后自动隐藏入托盘，点击托盘图标即可进行更改

**点击自动打开data文件夹**

可更改课程表，关机时间等信息

![data.png](https://s2.loli.net/2024/06/09/Hs2y4kuegvYpJRV.png)

## 二. 时钟

**显示星期、时间、日期、考试倒计时**

### 更改倒计时信息~~、及窗口缩放~~方法

1. 双击倒计时打开设置窗口

倒计时显示格式“据<事件>还剩<数字>天”

~~拖动滑块进行窗口缩放~~

2. 直接通data文件夹下 [倒计时设置]time.txt 更改

![Snipaste_2024-04-06_09-13-00.png](https://s2.loli.net/2024/04/06/tFi6ejuzHyE8OQ9.png)

## 三. 课程表

**到达预定时间段的课程高亮显示、不限课程数量**

### 更改课程表内容

在程序根目录data文件夹中 [课程表]schedule.json5 文件中更改

![Snipaste_2024-04-06_09-10-33.png](https://s2.loli.net/2024/04/06/JR1aS6KWwbXPhgE.png)

## 四. 天气预报

**调用open weather API 实现当日天气及未来5天天气预报**

1. 更换 API 在data文件夹下 [天气服务API]OpenWeather-API.txt 更改

2. 更换天气位置坐标**双击**天气预报窗口更改（文件存储在data文件夹下 [天气坐标]location.txt 文件中，**需注意经纬度顺序**）

![edulocation.png](https://s2.loli.net/2024/05/19/nYFcgqUQ4OPikK6.png)

## 五. 自动播放新闻联播

**7：00自动默认浏览器开启新闻联播并全屏播放，7：30自动关闭**

集成https://github.com/Return-Log/AutoCCTV项目

## 六. 定时关机

1. 时间设置位于data目录下 [关机时间]closetime.json5 文件中

2. 可设置一周七天每天的多个关机时间

3. 关机存在10秒倒计时确定是否关机

## 七. 邮件公告板

1. 标题包含“通知”推送到通知栏，标题包含“通报”推送到通报栏，标题含有“呼叫”或“广播”推送到广播栏并语音播报详细内容，推送成功会返回一封邮件
2. 右下角拖动可调整窗口大小
3. 邮箱需使用outlook
4. 初次使用须在data下 [邮箱地址和密码]email_credentials.json 改为自己邮箱地址和密码

![Snipaste_2024-06-30_00-55-23.png](https://s2.loli.net/2024/06/30/5YOchCqTKRFBG8D.png)

***设置无法保存请用管理员模式运行后重试***

------

Copyright © 2024  Log  All rights reserved.

