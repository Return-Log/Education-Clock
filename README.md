# 简介

**功能：**

-桌面时钟 -课程表 -天气预报 -自动新闻联播 -定时关机

![.png](https://s2.loli.net/2024/06/09/MPewgN6FvBSxKo2.png)

# 信息

版本：v0.7

时间：2024/6/9

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

双击倒计时打开设置窗口

倒计时显示格式“据<事件>还剩<数字>天”

~~拖动滑块进行窗口缩放~~

![Snipaste_2024-04-06_09-13-00.png](https://s2.loli.net/2024/04/06/tFi6ejuzHyE8OQ9.png)

## 三. 课程表

**到达预定时间段的课程高亮显示、不限课程数量**

### 更改课程表内容

在程序根目录data文件夹中 schedule.json5 文件中更改

![Snipaste_2024-04-06_09-10-33.png](https://s2.loli.net/2024/04/06/JR1aS6KWwbXPhgE.png)

## 四. 天气预报

**调用open weather API 实现当日天气及未来5天天气预报**

更换 API 在data文件夹下 OpenWeather-API.txt 更改

更换天气位置坐标双击天气预报窗口更改（文件存储在data文件夹下 location.txt 文件中，**需注意经纬度顺序**）

![edulocation.png](https://s2.loli.net/2024/05/19/nYFcgqUQ4OPikK6.png)

## 五. AutoCCTV

集成https://github.com/Return-Log/AutoCCTV项目，从托盘开启

## 六. 定时关机

时间设置位于data目录下closetime.json5文件中

可设置一周七天每天的多个关机时间

关机存在10秒倒计时确定是否关机

从托盘开启

***设置无法保存请用管理员模式运行后重试***

------

Copyright © 2024  Log  All rights reserved.

