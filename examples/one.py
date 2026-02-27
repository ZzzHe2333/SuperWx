from wxauto4 import WeChat

# 初始化微信实例
wx = WeChat()

# 发送消息
wx.SendMsg("123", who="让九")
print('==' * 30)
# 获取当前聊天窗口消息
msgs = wx.GetAllMessage()
print(msgs)
print('==' * 30)
try:
    for msg in msgs:
        
        print('==' * 30)
        print(f"{msg.sender}: {msg.content}")
except:
    print("---")
finally:
    print("ok")
