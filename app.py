import os
import json
import re
import logging
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, FlexSendMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

# 設定日誌，讓我們能在 Render Log 看到具體錯誤
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- 環境變數 ---
CHANNEL_ACCESS_TOKEN = os.environ.get('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('CHANNEL_SECRET')

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# --- 資料載入 ---
KANGXI_JSON_PATH = os.path.join(os.path.dirname(__file__), "kangxi_total_strokes_kv.json")
try:
    with open(KANGXI_JSON_PATH, "r", encoding="utf-8") as f:
        STROKE_DICT = json.load(f)
except Exception as e:
    logger.error(f"無法讀取字典檔: {e}")
    STROKE_DICT = {}

DOUBLE_SURNAME_LIST = ["張簡", "歐陽", "司馬", "諸葛", "司徒", "上官", "皇甫", "范姜"]

def get_stroke_count(char):
    return STROKE_DICT.get(char, 10)

def get_element(number):
    try:
        last_digit = int(str(number)[-1])
        return {1:'木', 2:'木', 3:'火', 4:'火', 5:'土', 6:'土', 7:'金', 8:'金', 9:'水', 0:'水'}.get(last_digit, '未知')
    except: return '?'

def get_nayin_simple(year):
    nayins = ["海中金","爐中火","大林木","路旁土","劍鋒金","山頭火","澗下水","城頭土","白蠟金","楊柳木",
              "泉中水","屋上土","霹靂火","松柏木","長流水","沙中金","山下火","平地木","壁上土","金箔金",
              "覆燈火","天河水","大驛土","釵釧金","桑柘木","大溪水","沙中土","天上火","石榴木","大海水"]
    try:
        y = int(year)
        if y < 1924: return None
        return nayins[((y - 1924) % 60) // 2][-1] 
    except: return None

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    logger.info(f"收到訊息: {msg}")
    
    # 支援格式: 姓名+年份 (如: 羅卓尹宏 1990)
    match = re.match(r"([^\d\+\s\-]+)[\+\s\-]*(\d*)", msg)
    if not match: return

    full_name = match.group(1)
    birth_year = match.group(2)

    try:
        # 姓名切割邏輯優化
        if (len(full_name) >= 3 and full_name[:2] in DOUBLE_SURNAME_LIST) or len(full_name) == 4:
            surname, name = full_name[:2], full_name[2:]
        else:
            surname, name = full_name[:1], full_name[1:]

        s_strk = [get_stroke_count(c) for c in surname]
        n_strk = [get_stroke_count(c) for c in name] if name else [10]
        
        tian = (sum(s_strk) if len(surname) > 1 else s_strk[0] + 1)
        ren = (s_strk[-1] + n_strk[0])
        di = ((n_strk[0] + 1) if len(n_strk) == 1 else sum(n_strk[:2]))
        wai = (2 if len(n_strk) == 1 else n_strk[-1] + (1 if len(surname) == 1 else s_strk[0]))
        zong = sum(s_strk) + sum(n_strk)
        n_res = get_nayin_simple(birth_year)

        # 背景與樣式
        BACKGROUND_URL = "https://raw.githubusercontent.com/Leo1421/line-name-bot/main/background.jpg?v=99"
        
        name_contents = []
        for char in full_name:
            name_contents.append({
                "type": "box", "layout": "horizontal", "contents": [
                    {"type": "text", "text": char, "weight": "bold", "size": "3xl", "flex": 3, "align": "end", "color": "#4a4a4a"},
                    {"type": "text", "text": f"{get_stroke_count(char)}", "size": "sm", "flex": 2, "color": "#7a7a7a", "gravity": "center"}
                ]
            })

        flex = {
            "type": "bubble", "size": "giga",
            "body": {
                "type": "box", "layout": "vertical", "paddingAll": "0px",
                "contents": [
                    {"type": "image", "url": BACKGROUND_URL, "size": "full", "aspectMode": "fill", "position": "absolute"},
                    {
                        "type": "box", "layout": "vertical", 
                        "paddingTop": "45px", "paddingBottom": "65px", "paddingStart": "20px", "paddingEnd": "20px",
                        "contents": [
                            {"type": "text", "text": " — 婉 穎 命 光 所 — ", "weight": "bold", "color": "#6d6d6d", "size": "sm", "align": "center"},
                            {"type": "box", "layout": "horizontal", "margin": "xxl", "contents": [
                                {"type": "box", "layout": "vertical", "flex": 18, "justifyContent": "center", "contents": [
                                    {"type": "text", "text": "外格", "size": "xs", "color": "#8e8e8e", "align": "center"},
                                    {"type": "text", "text": get_element(wai), "weight": "bold", "size": "xl", "align": "center"}
                                ]},
                                {"type": "box", "layout": "vertical", "flex": 34, "spacing": "sm", "contents": name_contents},
                                {"type": "box", "layout": "vertical", "flex": 24, "spacing": "md", "contents": [
                                    {"type": "text", "text": f"天 {get_element(tian)}", "weight": "bold", "size": "xl", "align": "center"},
                                    {"type": "text", "text": f"人 {get_element(ren)}", "weight": "bold", "size": "xl", "align": "center"},
                                    {"type": "text", "text": f"地 {get_element(di)}", "weight": "bold", "size": "xl", "align": "center"}
                                ]},
                                {"type": "box", "layout": "vertical", "flex": 24, "justifyContent": "center", "contents": [
                                    {"type": "text", "text": "出生年", "size": "xs", "color": "#8e8e8e", "align": "center"},
                                    {"type": "text", "text": f"{birth_year if birth_year else '--'}", "size": "sm", "align": "center"},
                                    {"type": "text", "text": f"{n_res if n_res else '--'}", "weight": "bold", "size": "xl", "align": "center"}
                                ]}
                            ]},
                            {"type": "separator", "margin": "xxl", "color": "#00000000"},
                            {"type": "box", "layout": "vertical", "contents": [
                                {"type": "text", "text": "總格", "size": "xs", "color": "#8e8e8e", "align": "center"},
                                {"type": "text", "text": get_element(zong), "weight": "bold", "size": "xl", "align": "center"}
                            ]}
                        ]
                    }
                ]
            }
        }
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="姓名鑑定結果", contents=flex))
    except Exception as e:
        logger.error(f"處理訊息時出錯: {e}")

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("簽章無效，請檢查 CHANNEL_SECRET 和 CHANNEL_ACCESS_TOKEN 是否正確設定")
        abort(400)
    except Exception as e:
        logger.error(f"Callback 發生未知錯誤: {e}")
        abort(400)
    return 'OK'

if __name__ == "__main__":
    app.run()
