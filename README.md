# SuperWx - WeChat自动化工具

<p align="center">
  <img src="https://img.shields.io/badge/Version-40.1.1-blue.svg" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Platform-Windows10+-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/WeChat-4.1.8+-green.svg" alt="WeChat">
</p>

SuperWx 是一个适用于微信 4.1.8+ 客户端的 Python 自动化库，兼容官方 wxauto/wxautox4 API，提供消息发送、文件传输、消息监听等功能。

## 重要声明

<font color='red'>**目前需要自行适配**</font>

## 特性

- **API 兼容**：兼容官方 wxauto WeChat / Chat / Message 类接口
- **后台优先**：默认后台操作，不抢鼠标、不抢前台焦点
- **安全设计**：高风险方法默认 dry_run，需显式 allow_foreground 才执行
- **消息监听**：支持多会话消息监听与回调

## 📁 项目结构

```text
.
├── wxauto4/              # 核心库代码
│   ├── wx.py             # WeChat / Chat 主类
│   ├── msgs/             # Message 类型系统
│   ├── ui/               # UI 自动化层
│   │   └── driver.py     # 后台优先操作驱动
│   ├── moment.py         # 朋友圈功能
│   └── param.py          # 参数配置
├── local_tests/          # 本地测试脚本（不提交）
├── examples/             # 示例脚本
├── README.md
└── pyproject.toml
```


## 🚀 快速开始

```python
from wxauto4 import WeChat

# 创建微信实例
wx = WeChat()

# 发送消息
wx.SendMsg('你好，世界！', '好友昵称')

# 发送文件
wx.SendFiles(r'C:\path\to\file.txt', '好友昵称')

# 获取消息
messages = wx.GetAllMessage()
for msg in messages:
    print(msg.content)
```


## API 兼容性

本项目兼容官方 wxauto / wxautox4 文档中的主要接口：

| 类 | 方法数 | 兼容率 |
|---|---|---|
| WeChat | 25+ | 100% |
| Chat | 13 | 100% |
| Message | 78+ (含类型类) | 100% |

详见 [官方文档](https://docs.wxauto.org)

## 安全设计

高风险操作默认不执行，需显式授权：

```python
# 默认 dry_run，返回计划而非执行
result = wx.AddNewFriend('张三')
# → WxResponse.success({dry_run: True, method: 'WeChat.AddNewFriend', ...})

# 显式允许前台操作
result = wx.AddNewFriend('张三', allow_foreground=True)
```

**风险分级：**
- **LOW**：只读操作（GetSession, IsOnline, GetMyInfo）
- **MEDIUM**：可能切换页面（ChatWith, GetHistoryMessage）
- **HIGH**：影响社交关系（AddNewFriend, CreateGroup, PublishMoment）

## 文档

### 1. 获取微信实例

```python
from wxauto4 import WeChat

# 创建微信主窗口实例
wx = WeChat()

# 带参数初始化
wx = WeChat(nickname='微信', debug=True, resize=True)
```

### 2. 发送消息 - SendMsg

```python
# 基础消息发送
wx.SendMsg('Hello!', '目标用户')

# 后台发送（默认，不抢鼠标）
wx.SendMsg('Hello!', '目标用户')

# 允许前台发送（会激活窗口）
wx.SendMsg('Hello!', '目标用户', allow_foreground=True)
```

**参数说明：**
- `msg` (str): 消息内容
- `who` (str, optional): 发送对象，不指定则发送给当前聊天对象
- `clear` (bool, optional): 发送后是否清空编辑框，默认 True
- `at` (Union[str, List[str]], optional): @对象，支持字符串或列表
- `exact` (bool, optional): 是否精确匹配用户名，默认 False
- `allow_foreground` (bool, optional): 是否允许前台操作，默认 False

### 3. 发送文件 - SendFiles

```python
# 发送单个文件
wx.SendFiles(r'C:\path\to\file.txt', '目标用户')

# 发送多个文件
files = [
    r'C:\path\to\file1.txt',
    r'C:\path\to\file2.jpg',
    r'C:\path\to\file3.pdf'
]
wx.SendFiles(files, '目标用户')

# 向当前聊天窗口发送文件
wx.SendFiles(r'C:\path\to\file.txt')
```

**参数说明：**
- `filepath` (str|list): 文件的绝对路径，支持单个文件或文件列表
- `who` (str, optional): 发送对象，不指定则发送给当前聊天对象
- `exact` (bool, optional): 是否精确匹配用户名，默认 False

### 4. 获取消息 - GetAllMessage

```python
# 获取当前聊天窗口的所有消息
all_messages = wx.GetAllMessage()
```

**返回值：**
- `List[Message]`: 消息列表，每个消息对象包含发送者、内容、时间、类型等信息

### 5. 监听消息 - AddListenChat

```python
def on_message(msg, chat):
    """消息回调函数"""
    print(f'收到来自 {chat} 的消息: {msg.content}', flush=True)
    
    # 自动回复
    if msg.content == 'hello':
        chat.SendMsg('Hello! 我是xxx')

# 添加消息监听
wx.AddListenChat('好友昵称', on_message)
```

**参数说明：**
- `who` (str|List[str]): 监听对象，支持单个或多个
- `callback` (Callable): 回调函数，接收 `(msg, chat)` 两个参数

### 6. 移除监听 - RemoveListenChat

```python
# 移除特定对象的监听
wx.RemoveListenChat('好友昵称')

# 停止所有监听
wx.StopListening()
```

### 7. 切换聊天窗口 - ChatWith

```python
# 切换到指定聊天窗口
wx.ChatWith('好友昵称')
```

**参数说明：**
- `who` (str): 要切换到的聊天对象
- `exact` (bool, optional): 是否精确匹配名称

### 8. 获取子窗口实例 - GetSubWindow

```python
# 获取指定聊天的子窗口
chat_window = wx.GetSubWindow('好友昵称')

# 通过子窗口发送消息（不会切换主窗口）
chat_window.SendMsg('这是通过子窗口发送的消息')

# 获取子窗口信息
info = chat_window.ChatInfo()
print(f'聊天对象: {info["chat_name"]}')

# 关闭子窗口
chat_window.Close()
```

### 9. 获取所有子窗口实例 - GetAllSubWindow

```python
# 获取所有打开的子窗口
all_windows = wx.GetAllSubWindow()

for window in all_windows:
    print(f'窗口: {window.who}')
    # 可以对每个窗口进行操作
    window.SendMsg('批量消息发送')
    
# 关闭所有子窗口
for window in all_windows:
    window.Close()
```

### 10. 停止监听 - StopListening

```python
# 停止所有消息监听
wx.StopListening()

# 程序结束前建议停止监听
try:
    wx.SendMsg('程序即将结束', '管理员')
finally:
    wx.StopListening()
```

### 11. 消息类型

消息对象支持多种类型，每种类型有对应的方法：

| 类型 | 类 | 特有方法 |
|---|---|---|
| 文本 | TextMessage | — |
| 图片 | ImageMessage | download(), ocr() |
| 视频 | VideoMessage | download() |
| 语音 | VoiceMessage | to_text() |
| 文件 | FileMessage | download() |
| 引用 | QuoteMessage | download_quote_image() |
| 链接 | LinkMessage | get_url() |
| 位置 | LocationMessage | — |
| 表情 | EmotionMessage | — |
| 合并转发 | MergeMessage | — |
| 名片 | PersonalCardMessage | add_friend() |
| 笔记 | NoteMessage | get_content(), save_files(), to_markdown() |

每种类型都有 Friend/Self 变体（如 FriendTextMessage, SelfTextMessage）。

---

**免责声明**: 本工具仅用于学习和研究目的，使用者应当遵守相关法律法规，作者不承担任何因使用本工具而产生的法律责任。
