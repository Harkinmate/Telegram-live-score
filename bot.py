import os
import requests
import time
from telegram import Bot

# ---------------- CONFIGURATION ----------------
API_TOKEN = os.environ.get("API_TOKEN")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
CHECK_INTERVAL = 60  # seconds

# Validate tokens
if not all([API_TOKEN, TELEGRAM_TOKEN, CHANNEL_ID]):
    raise ValueError("One or more required environment variables are missing.")

bot = Bot(token=TELEGRAM_TOKEN)
posted_updates = {}  # Track posted events per match

# ---------------- HELPER FUNCTIONS ----------------
def get_live_matches():
    url = "https://api.football-data.org/v4/matches?status=LIVE"
    headers = {"X-Auth-Token": API_TOKEN}
    response = requests.get(url, headers=headers)
    data = response.json()
    return data.get("matches", [])

def format_goal_message(match, goal):
    home = match["homeTeam"]["name"]
    away = match["awayTeam"]["name"]
    score = f"{match['score']['fullTime']['home']} - {match['score']['fullTime']['away']}"
    msg = f"⚽ GOAL! {goal['team']}\n"
    msg += f"Player: {goal['player']}\n"
    if goal['assist']:
        msg += f"Assist: {goal['assist']}\n"
    msg += f"Time: {goal['time']}'\n"
    msg += f"Score: {home} {score} {away}"
    return msg

def parse_goals(match):
    goals = []
    for event in match.get("goals", []):
        if event.get("type") == "GOAL":
            goals.append({
                "player": event.get("scorer", {}).get("name"),
                "team": event.get("team", {}).get("name"),
                "time": event.get("minute"),
                "assist": event.get("assist", {}).get("name")
            })
    return goals

def format_status_message(match):
    status = match.get("status")
    home = match["homeTeam"]["name"]
    away = match["awayTeam"]["name"]

    if status == "LIVE":
        return f"🟢 Match Live:\n{home} vs {away}"
    elif status == "PAUSED":
        return f"⏸️ Halftime:\n{home} vs {away}"
    elif status == "IN_PLAY_EXTRA_TIME":
        return f"⏱️ Extra Time:\n{home} vs {away}"
    elif status == "FINISHED":
        fulltime_score = f"{match['score']['fullTime']['home']} - {match['score']['fullTime']['away']}"
        return f"🏁 Fulltime:\n{home} {fulltime_score} {away}"
    return None

# ---------------- MAIN LOOP ----------------
while True:
    try:
        matches = get_live_matches()
        for match in matches:
            match_id = match["id"]
            if match_id not in posted_updates:
                posted_updates[match_id] = {"goals": [], "status": []}

            # Post goals
            goals = parse_goals(match)
            for g in goals:
                if g not in posted_updates[match_id]["goals"]:
                    msg = format_goal_message(match, g)
                    bot.send_message(chat_id=CHANNEL_ID, text=msg)
                    posted_updates[match_id]["goals"].append(g)

            # Post match status updates
            status_msg = format_status_message(match)
            if status_msg and status_msg not in posted_updates[match_id]["status"]:
                bot.send_message(chat_id=CHANNEL_ID, text=status_msg)
                posted_updates[match_id]["status"].append(status_msg)

    except Exception as e:
        print("Error:", e)

    time.sleep(CHECK_INTERVAL)
