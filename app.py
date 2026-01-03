import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

# --- 自定義常用康熙筆畫字典 ---
# 提示：如果用戶輸入的字不在這裡面，程式會報錯。
# 實務上建議將此表擴充，或使用更完整的 JSON 檔。
STROKE_DICT = {
    "李": 7, "王": 4, "張": 11, "劉": 15, "陳": 16, "楊": 13, "趙": 14, "黃": 12, "周": 8, "吳": 7,
    "徐": 10, "孫": 10, "馬": 10, "朱": 6, "胡": 11, "郭": 15, "何": 7, "高": 10, "林": 8, "鄭": 19,
    "歐": 15, "陽": 17, "大": 3, "同": 6, "小": 3, "美": 9, "雅": 12, "修": 10, "志": 7, "明": 8
    # 您可以繼續在此增加常用的字...
}

def get_stroke_count(char):
    """取得康熙筆畫，若字典找不到，暫時回傳一般筆畫(len)作為備案"""
    return STROKE_DICT.get(char, 10) # 找不到就預設10畫，或您可以自行擴充字典

def get_element(number):
    last_digit = int(str(number)[-1])
    map_dict = {1:'木', 2:'木', 3:'火', 4:'火', 5:'土', 6:'土', 7:'金', 8:'金', 9:'水', 0:'水'}
    return map_dict.get(last_digit, '未知')

def get_nayin(year):
    nayins = ["海中金","海中金","爐中火","爐中火","大林木","大林木","路旁土","路旁土","劍鋒金","劍鋒金",
              "山頭火","山頭火","澗下水","澗下水","城頭土","城頭土","白蠟金","白蠟金","楊柳木","楊柳木",
              "泉中水","泉中水","屋上土","屋上土","霹靂火","霹靂火","松柏木","松柏木","長流水","長流水",
              "沙中金","沙中金","山下火","山下火","平地木","平地木","壁上土","壁上土","金箔金","金箔金",
              "覆燈火","覆燈火","天河水","天河水","大驛土","大驛土","釵釧金","釵釧金","桑柘木","桑柘木",
              "大溪水","大溪水","沙中土","沙中土","天上火","天上火","石榴木","石榴木","大海水","大海水"]
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
            
            # 判斷姓與名
            # 簡易判斷：前兩個字是否在複姓清單
            compound_list = ["歐陽", "司馬", "諸葛"] # 可自行增加
            if full_name[:2] in compound_list:
                surname, name = full_name[:2], full_name[2:]
            else:
                surname, name = full_name[:1], full_name[1:]

            s_strokes = [get_stroke_count(c) for c in surname]
            n_strokes = [get_stroke_count(c) for c in name]
            
            # 計算四格 (您的邏輯)
            tian = sum(s_strokes) if len(surname)>1 else s_strokes[0]+1
            ren = s_strokes[-1] + n_strokes[0]
            di = (n_strokes[0]+1) if len(name)==1 else sum(n_strokes[:2])
            wai = 2 if len(name)==1 else n_strokes[-1]+1

            reply = (f"【{full_name}】格局\n出生納音：{get_nayin(birth_year)}\n"
                     f"----------------\n天格：{tian} ({get_element(tian)})\n"
                     f"人格：{ren} ({get_element(ren)})\n"
                     f"地格：{di} ({get_element(di)})\n"
                     f"外格：{wai} ({get_element(wai)})")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        except:
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
