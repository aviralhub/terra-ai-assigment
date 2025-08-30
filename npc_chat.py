import json
import time
from datetime import datetime
from collections import defaultdict, deque
from dotenv import load_dotenv
import google.generativeai as genai
import os

# Load API key from .env
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Function to decide NPC mood based on player's message
def update_mood(text, current_mood):
    text_lower = text.lower()
    if any(word in text_lower for word in ["help", "thanks", "thank you", "appreciate"]):
        return "friendly"
    elif any(word in text_lower for word in ["useless", "stupid", "hate", "noob"]):
        return "angry"
    return current_mood

# Function to generate NPC reply with retry on quota error
def get_npc_reply(player_id, text, state, mood):
    prompt = f"""
    You are an NPC in a fantasy RPG.
    Mood: {mood}
    Player's last messages: {list(state)}
    Current player message: "{text}"
    Reply in 1-2 short sentences as an NPC.
    """
    model = genai.GenerativeModel("gemini-1.5-flash")
    attempt = 0

    while True:
        try:
            response = model.generate_content(prompt)
            reply = response.text.strip()

            # Save prompt + reply to ai_prompts.txt
            with open("ai_prompts.txt", "a", encoding="utf-8") as f:
                f.write("PROMPT:\n" + prompt + "\n")
                f.write("REPLY:\n" + reply + "\n")
                f.write("="*60 + "\n")

            return reply

        except Exception as e:
            error_message = str(e).lower()
            if "quota" in error_message or "429" in error_message or "exceeded" in error_message:
                attempt += 1
                wait_time = 2 ** attempt  # exponential backoff: 2,4,8,16...
                print(f"[Rate limit hit] Waiting {wait_time} sec before retry...")
                time.sleep(wait_time)
                continue
            else:
                print(f"[NPC model error] {e}, retrying in 2 sec...")
                time.sleep(2)
                continue

# Main game loop
def run_game():
    with open("players.json", "r") as f:
        messages = json.load(f)

    # Sort messages by timestamp
    messages.sort(key=lambda x: datetime.fromisoformat(x["timestamp"]))

    # Track per-player state and mood
    states = defaultdict(lambda: deque(maxlen=3))
    moods = defaultdict(lambda: "neutral")

    for msg in messages:
        pid = msg["player_id"]
        text = msg["text"]
        ts = msg["timestamp"]

        # Update state
        states[pid].append(text)

        # Update mood
        moods[pid] = update_mood(text, moods[pid])

        # Get NPC reply
        reply = get_npc_reply(pid, text, states[pid], moods[pid])

        # Console log
        print("=" * 40)
        print(f"Player {pid} at {ts}")
        print(f"Message: {text}")
        print(f"NPC Reply: {reply}")
        print(f"Conversation state: {list(states[pid])}")
        print(f"NPC Mood: {moods[pid]}")

        # Save full log to logs.txt
        with open("logs.txt", "a", encoding="utf-8") as f:
            f.write(f"Player {pid} at {ts}\n")
            f.write(f"Message: {text}\n")
            f.write(f"NPC Reply: {reply}\n")
            f.write(f"Conversation state: {list(states[pid])}\n")
            f.write(f"NPC Mood: {moods[pid]}\n")
            f.write("="*60 + "\n")

if __name__ == "__main__":
    run_game()
