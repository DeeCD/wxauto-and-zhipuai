# diagnose.py
import psutil
import wxauto
import zhipuai
import win32gui
import re

# 从 wechat_ai_glm.py 导入 API_KEY
from wechat_ai_glm import API_KEY, MODEL_NAME

def check_wechat_process():
    """检查微信进程状态"""
    for proc in psutil.process_iter(['name']):
        if 'WeChat.exe' in proc.info['name']:
            return True
    return False

def check_wechat_window():
    """检查微信窗口状态"""
    try:
        titles = []
        def win_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if "微信" in title or "WeChat" in title:
                    titles.append(title)
            return True
        
        win32gui.EnumWindows(win_callback, None)
        return len(titles) > 0
    except Exception as e:
        print(f"窗口检测异常: {str(e)}")
        return False

def check_api_connection():
    """检查API连通性"""
    try:
        client = zhipuai.ZhipuAI(api_key=API_KEY)
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role":"user","content":"测试"}],
             max_tokens=50
         )
        return resp.choices[0].message.content
    except Exception as e:
        # 尝试将错误信息编码为UTF-8，避免ASCII编码问题
        error_message = str(e)
        try:
            return error_message.encode('utf-8', errors='replace').decode('utf-8')
        except:
            return error_message

if __name__ == "__main__":
    print("微信进程状态:", "运行中" if check_wechat_process() else "未启动")
    print("微信窗口状态:", "已就绪" if check_wechat_window() else "不可用")
    
    api_test = check_api_connection()
    print("API连通性测试:", "成功" if "测试" in api_test else f"失败: {api_test}")