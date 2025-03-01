import requests
import sqlite3
import argparse
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime

# Chatwork API情報
API_TOKEN = "3b778fed91c8a38e17802a0180aca"
ROOM_ID = "377337322"
CHATWORK_API_URL = f"https://api.chatwork.com/v2/rooms/{ROOM_ID}/messages"

# SQLiteデータベース設定
DB_PATH = "schedule.db"

# メッセージを送信する関数（toall対応）
def send_chatwork_message(message, to_all=False):
    headers = {"X-ChatWorkToken": API_TOKEN}
    if to_all:
        message = "[toall] " + message  # [toall] をメッセージの先頭に追加
    data = {"body": message}
    response = requests.post(CHATWORK_API_URL, headers=headers, data=data)
    return response.status_code

# スケジュールされたメッセージを送信（単発 & 毎月）
def check_and_send_messages():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    today_time = datetime.now().strftime("%d %H:%M")  # 毎月のスケジュール用 (DD HH:MM)

    # 単発スケジュールの送信
    cursor.execute("SELECT id, message, to_all FROM schedule WHERE send_time = ?", (now,))
    messages = cursor.fetchall()
    for message_id, message, to_all in messages:
        send_chatwork_message(message, bool(to_all))
        cursor.execute("DELETE FROM schedule WHERE id = ?", (message_id,))
        conn.commit()

    # 毎月スケジュールの送信
    cursor.execute("SELECT id, message, to_all FROM monthly_schedule WHERE send_time = ?", (today_time,))
    monthly_messages = cursor.fetchall()
    for message_id, message, to_all in monthly_messages:
        send_chatwork_message(message, bool(to_all))

    conn.close()

# スケジュール登録（単発）
def add_schedule(message, send_time, to_all=False):
    if to_all:
        message = "[toall] " + message
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO schedule (message, send_time, to_all) VALUES (?, ?, ?)", (message, send_time, int(to_all)))
    conn.commit()
    conn.close()
    print(f"✅ スケジュール登録完了！[{send_time}] {message}")

# 毎月のスケジュール登録
def add_monthly_schedule(message, send_time, to_all=False):
    if to_all:
        message = "[toall] " + message
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO monthly_schedule (message, send_time, to_all) VALUES (?, ?, ?)", (message, send_time, int(to_all)))
    conn.commit()
    conn.close()
    print(f"✅ 毎月スケジュール登録完了！[{send_time}] {message}")

# スケジュール一覧表示
def list_schedules():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 単発スケジュール表示
    cursor.execute("SELECT id, message, send_time, to_all FROM schedule ORDER BY send_time ASC")
    schedules = cursor.fetchall()

    # 毎月スケジュール表示
    cursor.execute("SELECT id, message, send_time, to_all FROM monthly_schedule ORDER BY send_time ASC")
    monthly_schedules = cursor.fetchall()

    conn.close()

    if schedules or monthly_schedules:
        print("\n📌 **スケジュール一覧:**")
        for s in schedules:
            tag = "[toall] " if s[3] else ""
            print(f"【単発】ID: {s[0]} | 時間: {s[2]} | メッセージ: {tag}{s[1]}")
        for ms in monthly_schedules:
            tag = "[toall] " if ms[3] else ""
            print(f"【毎月】ID: {ms[0]} | 時間: {ms[2]} | メッセージ: {tag}{ms[1]}")
    else:
        print("⚠️ 登録されたスケジュールはありません。")

# スケジュール削除
def delete_schedule(schedule_id, is_monthly=False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    table = "monthly_schedule" if is_monthly else "schedule"
    cursor.execute(f"DELETE FROM {table} WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()
    print(f"🗑️ スケジュール ID {schedule_id} を削除しました。")

# データベースの初期化
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT,
    send_time TEXT,
    to_all INTEGER DEFAULT 0
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS monthly_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT,
    send_time TEXT,
    to_all INTEGER DEFAULT 0
)
""")
conn.commit()
conn.close()

# コマンドライン引数の処理
parser = argparse.ArgumentParser(description="Chatwork スケジュール管理ツール")
parser.add_argument("--add", nargs=3, metavar=("message", "send_time", "to_all"), help="スケジュールを追加 (to_all: 1で全員通知)")
parser.add_argument("--add-monthly", nargs=3, metavar=("message", "send_time", "to_all"), help="毎月スケジュールを追加 (to_all: 1で全員通知)")
parser.add_argument("--list", action="store_true", help="スケジュール一覧を表示")
parser.add_argument("--delete", metavar="schedule_id", type=int, help="単発スケジュールを削除")
parser.add_argument("--delete-monthly", metavar="schedule_id", type=int, help="毎月スケジュールを削除")

args = parser.parse_args()

if args.add:
    add_schedule(args.add[0], args.add[1], bool(int(args.add[2])))
elif args.add_monthly:
    add_monthly_schedule(args.add_monthly[0], args.add_monthly[1], bool(int(args.add_monthly[2])))
elif args.list:
    list_schedules()
elif args.delete:
    delete_schedule(args.delete)
elif args.delete_monthly:
    delete_schedule(args.delete_monthly, is_monthly=True)
else:
    # スケジューラーの実行
    scheduler = BlockingScheduler()
    scheduler.add_job(check_and_send_messages, "interval", minutes=1)
    print("⏳ スケジューラーが開始されました。1分ごとにスケジュールを確認します。")
    scheduler.start()
