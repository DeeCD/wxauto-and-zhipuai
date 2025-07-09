from wxauto import WeChat
import zhipuai
import time
import hashlib
import re
import win32gui
from typing import List, Dict

# ​******************** 配置区域 ​********************
API_KEY = "1734b4fcea4d4a7fbb330d67034cee3c.KSsMmYEDAMSNElHt"
TARGET_CHATS = ["文件传输助手", "指定群聊"]
REPLY_MODE = "全部回复"  # 可选："全部回复" 或 "@回复"
MODEL_NAME = "glm-z1-flash"  # 必须包含日期后缀[1](@ref)
# ​************************************************

class ZhipuAIClient:
    def __init__(self, api_key: str):
        self.client = zhipuai.ZhipuAI(api_key=api_key)
    
    def generate_reply(self, prompt: str) -> str:
        """生成AI回复（带错误重试机制）"""
        for retry in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    top_p=0.8
                )
                return response.choices[0].message.content
            except zhipuai.APIConnectionError as e:
                print(f"⚠️ 网络异常({retry+1}/3): {str(e)}")
                time.sleep(2 ** retry)
            except zhipuai.APIError as e:
                error_message = str(e.message)
                try:
                    # 尝试将错误信息编码为UTF-8，避免ASCII编码问题
                    print(f"⛔ API错误: {e.code}-{error_message.encode('utf-8', errors='replace').decode('utf-8')}")
                except:
                    print(f"⛔ API错误: {e.code}-{error_message}")
                return None
        return None

def is_text_message(msg):
    content = msg.get('content', '')
    # 过滤掉图片、文件等非文本消息
    if not isinstance(content, str):
        return False
    if content.startswith('[') and content.endswith(']'):
        return False
    return True

msg_cache = set()

# 兼容性初始化（保留原有逻辑）
try:
    wx = WeChat()
except ValueError as e:
    if "not enough values to unpack" in str(e):
        print("⚠️ 检测到 wxauto 库版本兼容性问题，尝试使用替代方法初始化...")
        import comtypes.client
        import win32gui
        wx = WeChat.__new__(WeChat)
        wx.root = None
        hwnd = win32gui.FindWindow(None, "微信")
        if hwnd == 0:
            hwnd = win32gui.FindWindow(None, "WeChat")
        if hwnd == 0:
            raise Exception("未找到微信窗口，请确保微信已登录并处于前台")
        wx.root = hwnd
        print(f"✅ 已手动初始化微信窗口，句柄: {hwnd}")
    else:
        raise

# 启动时缓存历史消息id
try:
    init_messages = wx.GetAllMessage()
    if not isinstance(init_messages, list):
        init_messages = [init_messages]
    for msg in init_messages:
        if not isinstance(msg, dict):
            if hasattr(msg, '__dict__'):
                msg = msg.__dict__
            else:
                continue
        msg_id = msg.get('id')
        if msg_id:
            msg_cache.add(msg_id)
    print(f"[DEBUG] 启动时已缓存历史消息数: {len(msg_cache)}")
except Exception as e:
    print(f"[DEBUG] 启动时缓存历史消息失败: {e}")


def handle_message(msg):
    print(f"[DEBUG] 收到消息对象: {msg}")
    # 兼容消息对象不是dict的情况
    if not isinstance(msg, dict):
        if hasattr(msg, '__dict__'):
            msg = msg.__dict__
        else:
            print("[DEBUG] 消息对象无法转为字典，跳过")
            return
    # 判断是否为文本消息
    if not is_text_message(msg):
        print(f"[DEBUG] 非文本消息，跳过 content={msg.get('content')}")
        return
    content = msg.get('content', '')
    # 优化 chat_name 获取逻辑
    chat_name = msg.get('chat_name') or msg.get('sender') or msg.get('receiver') or ''
    msg_id = msg.get('id')
    if not msg_id:
        print("[DEBUG] 消息无id，跳过")
        return
    if msg_id in msg_cache:
        print(f"[DEBUG] 已处理过的消息，跳过 id={msg_id}")
        return
    msg_cache.add(msg_id)
    if not content.strip():
        print("[DEBUG] 空内容消息，跳过")
        return
    print(f"📩 收到消息: {content}")
    print(f"[DEBUG] REPLY_MODE: {REPLY_MODE}, bot_name: {bot_name}, content: {content}")
    # 触发条件判断
    if REPLY_MODE == "全部回复" or (REPLY_MODE == "@回复" and f"@{bot_name}" in content):
        print("[DEBUG] 进入回复分支，准备调用AI接口...")
        reply = ai.generate_reply(content)
        print(f"[DEBUG] AI回复内容: {reply}")
        if reply:
            try:
                # 自动适配不同 wxauto 版本的发送方式
                print(f"[DEBUG] 仅调用 SendMsg: {reply}")
                wx.SendMsg(reply)
                print(f"✅ 已发送: {reply[:50]}...")
            except Exception as e:
                print(f"❌ 发送失败: {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            print("[DEBUG] AI回复内容为空，不发送")
    else:
        print("[DEBUG] 未进入回复分支，不回复")

# 获取机器人昵称
try:
    bot_name = wx.GetSelfName()
except Exception:
    bot_name = "AI助手"

ai = ZhipuAIClient(API_KEY)

# 添加监听聊天对象
for chat in TARGET_CHATS:
    try:
        wx.AddListenChat(chat, callback=handle_message)
        print(f"🔗 成功绑定: {chat}")
    except Exception as e:
        print(f"❌ 绑定失败 [{chat}]: {str(e)}")

print(f"⚠️ 请保持微信窗口在前台！\n🚀 开始监控：{TARGET_CHATS}")

while True:
    try:
        messages = wx.GetAllMessage()
        if not messages:
            continue
        if not isinstance(messages, list):
            messages = [messages]
        # 只处理最新一条消息
        msg = messages[-1]
        # 兼容消息对象不是dict的情况
        if not isinstance(msg, dict):
            if hasattr(msg, '__dict__'):
                msg = msg.__dict__
            else:
                continue
        # 跳过自己发的消息
        if msg.get('sender') == 'self' or msg.get('sender_remark') == 'self':
            continue
        handle_message(msg)
        time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n🛑 程序已手动终止")
        break
    except Exception as e:
        print(f"❌ 运行异常: {str(e)}")
        time.sleep(3)
