import asyncio
import json
import time
import logging
import random
import requests
from fastapi import FastAPI, WebSocket
from spellchecker import SpellChecker
from dotenv import load_dotenv
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("twitch-spellchecker")
app = FastAPI()
load_dotenv(dotenv_path="/.env")
TMI_HOST = "irc.chat.twitch.tv"
TMI_PORT = 6667
OAUTH_TOKEN = "SCHMOOPIIE"
NICK = f"justinfan{random.randint(100000, 999999)}"

spell = SpellChecker()

# det här funkar inte, du måste skapa en twitch app och få en client id och oauth token och det orkar jag inte
#def get_bttv_whitelist(twitch_user: str) -> set:
#    headers = {
#        'Client-ID': os.getenv("CLIENT_ID"),
#        'Authorization': f"Bearer {os.getenv('OAUTH_TOKEN')}"
#    }
#    try:
#        response = requests.get(f"https://api.twitch.tv/helix/users?login={twitch_user}", headers=headers)
#        response.raise_for_status()
#        twitchUSERID = response.json()['data'][0]['id']
#        logger.info(f"Fetched Twitch user ID for user {twitch_user}: {twitchUSERID}")
#    except requests.exceptions.RequestException as e:
#        logger.error(f"Error fetching Twitch user ID: {e}")
#        return set()
#    
#    try:
#        url = f"https://api.betterttv.net/3/cached/users/twitch/{twitchUSERID}"
#        response = requests.get(url)
#        response.raise_for_status()
#        data = response.json()
#        whitelist = {emote["code"] for emote in data.get("channelEmotes", []) + data.get("sharedEmotes", [])}
#        logger.info(f"Fetched BTTV whitelist for user {twitchUSERID}: {whitelist}")
#        return whitelist
#    except requests.exceptions.RequestException as e:
#        logger.error(f"Error fetching BTTV whitelist: {e}")
#        return set()


def check_spelling(text: str) -> dict:
    words = text.split()
    words_to_check = [word.lower() for word in words if word.lower()] #not in whitelist]
    words_to_check = list(set(words_to_check))
    misspelled = spell.unknown(words_to_check)
    logger.info(f"Misspelled words: {misspelled}")
    return {word: spell.correction(word) for word in misspelled}

async def connect_to_channel(channel: str, update_callback):
    #whitelist = get_bttv_whitelist(channel)
    logger.info(f"Connecting to channel: {channel}")
    reader, writer = await asyncio.open_connection(TMI_HOST, TMI_PORT)
    writer.write(f"PASS {OAUTH_TOKEN}\r\n".encode())
    writer.write(f"NICK {NICK}\r\n".encode())
    writer.write(f"JOIN #{channel}\r\n".encode())
    await writer.drain()
    mistakes = 0
    start_time = time.monotonic()

    try:
            while True:
                line = await reader.readline()
                if not line:
                    logger.warning(f"Connection closed by Twitch for channel: {channel}")
                    break
                decoded = line.decode(errors="ignore").strip()
                if "PRIVMSG" in decoded:
                    try:
                        msg = decoded.split(":", 2)[2]
                        msg = msg.split(" ", 1)[1] if " " in msg else msg
                    except IndexError:
                        continue
                    corrections = check_spelling(msg)
                    num_mistakes = len(corrections)
                    mistakes += num_mistakes
                    elapsed = time.monotonic() - start_time
                    rate = mistakes / (elapsed / 60) if elapsed > 0 else 0
                    logger.info(
                        f"[{channel}] Message: {msg} | Total Mistakes: {mistakes} | Rate: {rate:.2f}/min | Corrections: {corrections}"
                    )
                    await update_callback(channel, mistakes, rate)
    except Exception as e:
        logger.error(f"[{channel}] Error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()
        logger.info(f"Disconnected from channel: {channel}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    logger.info("New WebSocket connection established")
    await websocket.accept()
    channels = {}
    stats = {}

    async def update_callback(channel: str, mistakes: int, rate: float):
        stats[channel] = {"mistakes": mistakes, "misspelled_per_min": round(rate, 2)}
        logger.info(f"Sending update: {stats}")
        await websocket.send_text(json.dumps(stats))

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if "add_channel" in message:
                channel = message["add_channel"].lower()
                if channel not in channels:
                    logger.info(f"Adding channel: {channel}")
                    channels[channel] = asyncio.create_task(connect_to_channel(channel, update_callback))
            elif "remove_channel" in message:
                channel = message["remove_channel"].lower()
                if channel in channels:
                    logger.info(f"Removing channel: {channel}")
                    channels[channel].cancel()
                    del channels[channel]
                    if channel in stats:
                        del stats[channel]
                    await websocket.send_text(json.dumps(stats))
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info("WebSocket connection closed")
