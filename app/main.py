import os
import random
from flask import Flask, render_template, request, jsonify, url_for, session
from dotenv import load_dotenv
import google.generativeai as genai
import threading
import queue

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.urandom(24) # Needed for session management

# --- Tarot Card Data ---
TAROT_CARDS = [
    {"name": "The Fool", "img": "m00.jpg"}, {"name": "The Magician", "img": "m01.jpg"},
    {"name": "The High Priestess", "img": "m02.jpg"}, {"name": "The Empress", "img": "m03.jpg"},
    {"name": "The Emperor", "img": "m04.jpg"}, {"name": "The Hierophant", "img": "m05.jpg"},
    {"name": "The Lovers", "img": "m06.jpg"}, {"name": "The Chariot", "img": "m07.jpg"},
    {"name": "Strength", "img": "m08.jpg"}, {"name": "The Hermit", "img": "m09.jpg"},
    {"name": "Wheel of Fortune", "img": "m10.jpg"}, {"name": "Justice", "img": "m11.jpg"},
    {"name": "The Hanged Man", "img": "m12.jpg"}, {"name": "Death", "img": "m13.jpg"},
    {"name": "Temperance", "img": "m14.jpg"}, {"name": "The Devil", "img": "m15.jpg"},
    {"name": "The Tower", "img": "m16.jpg"}, {"name": "The Star", "img": "m17.jpg"},
    {"name": "The Moon", "img": "m18.jpg"}, {"name": "The Sun", "img": "m19.jpg"},
    {"name": "Judgement", "img": "m20.jpg"}, {"name": "The World", "img": "m21.jpg"},
    {"name": "Ace of Wands", "img": "w01.jpg"}, {"name": "Two of Wands", "img": "w02.jpg"},
    {"name": "Three of Wands", "img": "w03.jpg"}, {"name": "Four of Wands", "img": "w04.jpg"},
    {"name": "Five of Wands", "img": "w05.jpg"}, {"name": "Six of Wands", "img": "w06.jpg"},
    {"name": "Seven of Wands", "img": "w07.jpg"}, {"name": "Eight of Wands", "img": "w08.jpg"},
    {"name": "Nine of Wands", "img": "w09.jpg"}, {"name": "Ten of Wands", "img": "w10.jpg"},
    {"name": "Page of Wands", "img": "w11.jpg"}, {"name": "Knight of Wands", "img": "w12.jpg"},
    {"name": "Queen of Wands", "img": "w13.jpg"}, {"name": "King of Wands", "img": "w14.jpg"},
    {"name": "Ace of Cups", "img": "c01.jpg"}, {"name": "Two of Cups", "img": "c02.jpg"},
    {"name": "Three of Cups", "img": "c03.jpg"}, {"name": "Four of Cups", "img": "c04.jpg"},
    {"name": "Five of Cups", "img": "c05.jpg"}, {"name": "Six of Cups", "img": "c06.jpg"},
    {"name": "Seven of Cups", "img": "c07.jpg"}, {"name": "Eight of Cups", "img": "c08.jpg"},
    {"name": "Nine of Cups", "img": "c09.jpg"}, {"name": "Ten of Cups", "img": "c10.jpg"},
    {"name": "Page of Cups", "img": "c11.jpg"}, {"name": "Knight of Cups", "img": "c12.jpg"},
    {"name": "Queen of Cups", "img": "c13.jpg"}, {"name": "King of Cups", "img": "c14.jpg"},
    {"name": "Ace of Swords", "img": "s01.jpg"}, {"name": "Two of Swords", "img": "s02.jpg"},
    {"name": "Three of Swords", "img": "s03.jpg"}, {"name": "Four of Swords", "img": "s04.jpg"},
    {"name": "Five of Swords", "img": "s05.jpg"}, {"name": "Six of Swords", "img": "s06.jpg"},
    {"name": "Seven of Swords", "img": "s07.jpg"}, {"name": "Eight of Swords", "img": "s08.jpg"},
    {"name": "Nine of Swords", "img": "s09.jpg"}, {"name": "Ten of Swords", "img": "s10.jpg"},
    {"name": "Page of Swords", "img": "s11.jpg"}, {"name": "Knight of Swords", "img": "s12.jpg"},
    {"name": "Queen of Swords", "img": "s13.jpg"}, {"name": "King of Swords", "img": "s14.jpg"},
    {"name": "Ace of Pentacles", "img": "p01.jpg"}, {"name": "Two of Pentacles", "img": "p02.jpg"},
    {"name": "Three of Pentacles", "img": "p03.jpg"}, {"name": "Four of Pentacles", "img": "p04.jpg"},
    {"name": "Five of Pentacles", "img": "p05.jpg"}, {"name": "Six of Pentacles", "img": "p06.jpg"},
    {"name": "Seven of Pentacles", "img": "p07.jpg"}, {"name": "Eight of Pentacles", "img": "p08.jpg"},
    {"name": "Nine of Pentacles", "img": "p09.jpg"}, {"name": "Ten of Pentacles", "img": "p10.jpg"},
    {"name": "Page of Pentacles", "img": "p11.jpg"}, {"name": "Knight of Pentacles", "img": "p12.jpg"},
    {"name": "Queen of Pentacles", "img": "p13.jpg"}, {"name": "King of Pentacles", "img": "p14.jpg"},
]

# --- Gemini API Configuration ---
api_keys = [os.getenv(key) for key in os.environ if key.startswith("GEMINI_API_KEY_")]
api_keys = [key for key in api_keys if key]  # Filter out empty/None keys

api_configured = False
if not api_keys:
    print("No GEMINI_API_KEY_n variables found in .env file.")
else:
    print(f"Found {len(api_keys)} API key(s).")
    api_configured = True

def get_gemini_response(api_key, prompt, result_queue):
    """Configures Gemini and gets a response, putting it in the queue."""
    try:
        # Each thread needs its own configured instance of the API
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        # We only care about the first successful response
        if result_queue.empty():
            result_queue.put({'text': response.text, 'key_used': api_key})
    except Exception as e:
        # Log errors for debugging but don't stop other threads
        print(f"Error with API key ending in ...{api_key[-4:]}: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_reading', methods=['POST'])
def get_reading():
    data = request.get_json()
    question = data.get('question')

    if not question:
        return jsonify({'error': 'Question is required.'}), 400

    # --- Conversation History ---
    if 'history' not in session:
        session['history'] = []

    history_string = ""
    for entry in session['history']:
        history_string += f"Previous Question: {entry['question']}\nPrevious Reading: {entry['reading']}\n\n"

    # 1. Draw three cards and determine their orientation
    drawn_cards_info = []
    sampled_cards = random.sample(TAROT_CARDS, 3)
    for card in sampled_cards:
        orientation = random.choice(['Upright', 'Reversed'])
        drawn_cards_info.append({**card, 'orientation': orientation})

    past_card, present_card, future_card = drawn_cards_info[0], drawn_cards_info[1], drawn_cards_info[2]

    # 2. Create a prompt for Gemini, now with history
    prompt = (
        f"You are TarotMeow, a kind, cute, and professional tarot-reading cat. "
        f"You are in an ongoing conversation. Here is the recent history:\n"
        f"---BEGIN CONVERSATION HISTORY---\n{history_string}---END CONVERSATION HISTORY---\n\n"
        f"The user's NEW question is: '{question}'\n\n"
        f"You have drawn three new cards for them for this new question:\n"
        f"Past: {past_card['name']} ({past_card['orientation']})\n"
        f"Present: {present_card['name']} ({present_card['orientation']})\n"
        f"Future: {future_card['name']} ({future_card['orientation']})\n\n"
        f"Please provide a gentle, comforting, and insightful interpretation of these three cards. "
        f"IMPORTANT: Analyze the conversation history. If the new question is a follow-up, "
        f"your new reading should connect to and build upon the previous readings. "
        f"If the question is new, treat it as a fresh start.\n\n"
        f"Structure your response with clear headings for 'Past', 'Present', and 'Future'. "
        f"The headings MUST be bold. To make them bold, you MUST wrap them in double asterisks. "
        f"For example: **Past: {past_card['name']} ({past_card['orientation']})**\n\n"
        f"After each bold heading, provide your interpretation for that card. "
        f"Give a summary of the cards at the end of your response."
        f"Ensure your analysis is directly relevant to the user's question. "
        f"Respond in English Markdown format. Do not include cat-like actions (purring, meowing)."
    )

    # 3. Get reading from Gemini using the fastest API key
    if not api_configured:
        return jsonify({'error': 'API not configured. Check .env file.'}), 500

    result_queue = queue.Queue()
    threads = []

    for key in api_keys:
        thread = threading.Thread(target=get_gemini_response, args=(key, prompt, result_queue))
        threads.append(thread)
        thread.start()

    try:
        result = result_queue.get(timeout=15)
        print(f"Fastest response from key ending in ...{result['key_used'][-4:]}")
        reading = result['text']
    except queue.Empty:
        print("All API keys failed or timed out.")
        return jsonify({'error': 'Could not get a response from the tarot spirits. Please try again.'}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'error': str(e)}), 500

    # --- Update History ---
    session['history'].append({'question': question, 'reading': reading})
    if len(session['history']) > 2: # Keep history to the last 2 interactions
        session['history'].pop(0)
    session.modified = True

    # 4. Prepare response
    response_data = {
        'reading': reading,
        'cards': {
            'past': {'name': past_card['name'], 'img': url_for('static', filename=f'images/{past_card["img"]}'), 'orientation': past_card['orientation']},
            'present': {'name': present_card['name'], 'img': url_for('static', filename=f'images/{present_card["img"]}'), 'orientation': present_card['orientation']},
            'future': {'name': future_card['name'], 'img': url_for('static', filename=f'images/{future_card["img"]}'), 'orientation': future_card['orientation']}
        }
    }
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True)
