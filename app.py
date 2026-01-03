import os
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

# --- 讀取康熙筆畫 JSON ---
# 檔案內容格式：{"李":7, "王":4, ...}
KANGXI_JSON_PATH = os.path.join(os.path.dirname(__file__), "kangxi_total_strokes_kv.json")
with open(KANGXI_JSON_PATH, "r", encoding="utf-8") as f:
    STROKE_DICT = json.load(f)

def get_stroke_count(char):
    """從 JSON 字典取得康熙筆畫，找不到則回傳 10 畫備用"""
    return STROKE_DICT.get(char, 10)

def get_element(number):
    last_digit = int(str(number)[-1])
    map_dict = {1:'木', 2:'木', 3:'火', 4:'火', 5:'土', 6:'土', 7:'金', 8:'金', 9:'水', 0:'水'}
    return map_dict.get(last_digit, '未知')

def get_nayin(year):
    nayins = [
        "海中金","海中金","爐中火","爐中火","大林木","大林木","路旁土","路旁土","劍鋒金","劍鋒金",
        "山頭火","山頭火","澗下水","澗下水","城頭土","城頭土","白蠟金","白蠟金","楊柳木","楊柳木",
        "泉中水","泉中水","屋上土","屋上土","霹靂火","霹靂火","松柏木","松柏木","長流水","長流水",
        "沙中金","沙中金","山下火","山下火","平地木","平地木","壁上土","壁上土","金箔金","金箔金",
        "覆燈火","覆燈火","天河水","天河水","大驛土","大驛土","釵釧金","釵釧金","桑柘木","桑柘木",
        "大溪水","大溪水","沙中土","沙中土","天上火","天上火","石榴木","石榴木","大海水","大海水"
    ]
    try:
        idx = (int(year) - 1924) % 60
        return nayins[idx]
    except:
        return "未知"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    if " " in msg:
        try:
            parts = msg.split()
            full_name = parts[0]
            birth_year = parts[1]
            
            # 判斷姓與名（支援複姓）
            compound_list = ["歐陽", "司馬", "諸葛"]  # 可自行增加
            if full_name[:2] in compound_list:
                surname, name = full_name[:2], full_name[2:]
            else:
                surname, name = full_name[:1], full_name[1:]

            # 依每個字查康熙筆畫
            s_strokes = [get_stroke_count(c) for c in surname]
            n_strokes = [get_stroke_count(c) for c in name]
            
            # 四格計算
            tian = sum(s_strokes) if len(surname) > 1 else s_strokes[0] + 1
            ren = s_strokes[-1] + n_strokes[0]
            di = (n_strokes[0] + 1) if len(name) == 1 else sum(n_strokes[:2])
            wai = 2 if len(name) == 1 else n_strokes[-1] + 1

            reply = (
                f"【{full_name}】格局\n"
                f"出生納音：{get_nayin(birth_year)}\n"
                f"----------------\n"
                f"天格：{tian} ({get_element(tian)})\n"
                f"人格：{ren} ({get_element(ren)})\n"
                f"地格：{di} ({get_element(di)})\n"
                f"外格：{wai} ({get_element(wai)})"
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        except Exception:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="格式錯誤，請輸入：姓名 1990"))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

if __name__ == "__main__":
    app.run()
