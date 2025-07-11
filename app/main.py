import os
import random
import json
from flask import Flask, render_template, request, jsonify, url_for, session, g
from flask_babel import Babel, gettext
from dotenv import load_dotenv
import google.generativeai as genai
import threading
import queue

# Load environment variables from .env file
load_dotenv()

# --- App Configuration ---
LANGUAGES = {
    'en': 'English',
    'zh_Hans': '简体中文'
}

app = Flask(__name__, template_folder='../templates', static_folder='../static')
def get_locale():
    # 1. Get language from session
    lang = session.get('language')
    if lang in LANGUAGES:
        return lang
    # 2. Otherwise try to guess the language from the user accept
    # header the browser transmits.
    return request.accept_languages.best_match(list(LANGUAGES.keys()))

def load_translations(lang):
    translation_path = os.path.join(os.path.dirname(__file__), '..', 'translations', f"{lang}.json")
    try:
        with open(translation_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback to English if a translation is missing
        fallback_path = os.path.join(os.path.dirname(__file__), '..', 'translations', 'en.json')
        with open(fallback_path, 'r', encoding='utf-8') as f:
            return json.load(f)

babel = Babel(app, locale_selector=get_locale)

@app.before_request
def before_request():
    g.locale = str(get_locale())
    g.translations = load_translations(g.locale)

app.secret_key = os.urandom(24) # Needed for session management

# --- Tarot Card Data ---
def load_tarot_knowledge():
    """Loads the tarot card knowledge base from the JSON file."""
    knowledge_path = os.path.join(os.path.dirname(__file__), 'tarot_knowledge.json')
    try:
        with open(knowledge_path, 'r', encoding='utf-8') as f:
            tarot_data = json.load(f)
            # Create a dictionary for easy lookup by card name
            tarot_knowledge_base = {card['name']: card for card in tarot_data}
            print("Successfully loaded tarot knowledge base.")
            return tarot_data, tarot_knowledge_base
    except FileNotFoundError:
        print(f"CRITICAL ERROR: tarot_knowledge.json not found at {knowledge_path}")
        return [], {} # Return empty structures if file is not found
    except json.JSONDecodeError:
        print(f"CRITICAL ERROR: Could not decode tarot_knowledge.json.")
        return [], {}

# Load the knowledge base when the app starts
TAROT_CARDS, TAROT_KNOWLEDGE_BASE = load_tarot_knowledge()


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
    session['language'] = g.locale
    return render_template('index.html', languages=LANGUAGES, translations=g.translations)

@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in LANGUAGES:
        session['language'] = lang
    return jsonify({'status': 'success', 'language': lang})

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    question = data.get('question')
    mode = data.get('mode', 'tarot') # Default to 'tarot' if mode not provided

    if not question:
        return jsonify({'error': 'Question is required.'}), 400
    
    if not TAROT_CARDS:
         return jsonify({'error': 'Tarot knowledge base is not loaded. Check server logs.'}), 500

    # --- Conversation History ---
    if 'history' not in session:
        session['history'] = []

    history_string = ""
    for entry in session['history']:
        history_string += f"Previous Question: {entry['question']}\nPrevious Reading: {entry['reading']}\n\n"

    if mode == 'tarot':
        # --- TAROT MODE: Draw new cards and perform a full reading ---
        drawn_cards_info = []
        sampled_cards = random.sample(TAROT_CARDS, 3)
        for card in sampled_cards:
            orientation = random.choice(['Upright', 'Reversed'])
            drawn_cards_info.append({**card, 'orientation': orientation})

        session['last_cards'] = drawn_cards_info  # Save cards to session
        session.modified = True

        prompt = create_tarot_prompt(question, drawn_cards_info, history_string)
        reading, error = get_gemini_reading(prompt)

        if error:
            return jsonify({'error': error}), 500

        # Prepare card data for the frontend
        past_card, present_card, future_card = drawn_cards_info[0], drawn_cards_info[1], drawn_cards_info[2]
        response_cards = {
            'past': format_card_for_response(past_card),
            'present': format_card_for_response(present_card),
            'future': format_card_for_response(future_card)
        }

    else: # mode == 'chat'
        # --- CHAT MODE: Use last drawn cards for a follow-up --- 
        last_cards = session.get('last_cards')
        if not last_cards:
            return jsonify({'reading': g.translations.get('noCardsDrawnError', 'You need to ask a tarot question first to draw some cards!')}), 200

        prompt = create_chat_prompt(question, last_cards, history_string)
        reading, error = get_gemini_reading(prompt)

        if error:
            return jsonify({'error': error}), 500
        
        response_cards = None # No new cards are sent in chat mode







    # --- Update History ---
    session['history'].append({'question': question, 'reading': reading})
    if len(session['history']) > 3: # Keep history to the last 3 interactions
        session['history'].pop(0)
    session.modified = True

    # --- Prepare and Send Response ---
    response_data = {
        'reading': reading,
        'cards': response_cards
    }
    return jsonify(response_data)

# --- Helper Functions for Prompt Generation ---

def get_card_meaning(card_info):
    card_name = card_info['name']
    orientation = card_info['orientation'].lower()
    knowledge = TAROT_KNOWLEDGE_BASE.get(card_name, {})
    return knowledge.get('meanings', {}).get(orientation, "No specific meaning found.")

def format_card_for_response(card_info):
    translations = g.translations
    card_name = translations['card_names'].get(card_info['name'], card_info['name'])
    orientation = translations.get(card_info['orientation'].lower(), card_info['orientation'])
    return {'name': card_name, 'img': url_for('static', filename=f'images/{card_info["img"]}'), 'orientation': orientation}

def create_tarot_prompt(question, drawn_cards, history):
    translations = g.translations
    language_name = LANGUAGES.get(g.locale, 'English')

    past_card, present_card, future_card = drawn_cards[0], drawn_cards[1], drawn_cards[2]
    past_meaning = get_card_meaning(past_card)
    present_meaning = get_card_meaning(present_card)
    future_meaning = get_card_meaning(future_card)

    past_card_fmt = format_card_for_response(past_card)
    present_card_fmt = format_card_for_response(present_card)
    future_card_fmt = format_card_for_response(future_card)

    return (
        f"You are {translations['aiName']}, a kind, cute, and professional tarot-reading cat. "
        f"You MUST use the provided context to interpret the cards. Do not use your own general knowledge of tarot.\n\n"
        f"Here is the user's conversation history:\n{history}\n"
        f"The user's NEW question is: '{question}'\n\n"
        f"You have drawn three cards. Here is the relevant knowledge for each card:\n"
        f"1. {translations['past']}: {past_card_fmt['name']} ({past_card_fmt['orientation']}) - Meaning: {past_meaning}\n"
        f"2. {translations['present']}: {present_card_fmt['name']} ({present_card_fmt['orientation']}) - Meaning: {present_meaning}\n"
        f"3. {translations['future']}: {future_card_fmt['name']} ({future_card_fmt['orientation']}) - Meaning: {future_meaning}\n\n"
        f"INSTRUCTIONS:\n"
        f"1. Give a nice, friendly, and comforting greeting. As a cat, you can add cat-like actions or sounds, but you MUST put them in square brackets.\n"
        f"2. Provide a gentle, comforting, and insightful interpretation based ONLY on the meanings provided.\n"
        f"3. Directly relate your interpretation to the user's question: '{question}'.\n"
        f"4. Structure your response with clear headings for each card position (Past, Present, Future) and the card name. These headings MUST be bold (e.g., `**{translations['past']}**`).\n"
        f"5. Provide a comprehensive and inspiring summary at the end.\n"
        f"6. Respond entirely in {language_name} using Markdown format."
    )

def create_chat_prompt(question, last_cards, history):
    translations = g.translations
    language_name = LANGUAGES.get(g.locale, 'English')

    card_details = []
    for card in last_cards:
        card_fmt = format_card_for_response(card)
        meaning = get_card_meaning(card)
        card_details.append(f"- {card_fmt['name']} ({card_fmt['orientation']}): {meaning}")
    card_knowledge = "\n".join(card_details)

    return (
        f"You are {translations['aiName']}, a kind, cute, and professional tarot-reading cat.\n"
        f"The user is asking a follow-up question about a previous tarot reading.\n\n"
        f"Here is the user's conversation history:\n{history}\n"
        f"The cards from the last reading were:\n{card_knowledge}\n\n"
        f"The user's NEW follow-up question is: '{question}'\n\n"
        f"INSTRUCTIONS:\n"
        f"1. Do NOT draw new cards. Your response must be based on the cards already drawn.\n"
        f"2. Provide a comforting, insightful, and concise answer to the follow-up question. As a cat, you can add cat-like actions or sounds, but you MUST put them in square brackets.\n"
        f"3. Directly connect your answer to the meanings of the cards from the previous reading.\n"
        f"4. Keep your response focused on the user's specific question.\n"
        f"5. Respond entirely in {language_name} using Markdown format."
    )

def get_gemini_reading(prompt):
    if not api_configured:
        return None, 'API not configured. Check .env file.'

    result_queue = queue.Queue()
    threads = []
    for key in api_keys:
        thread = threading.Thread(target=get_gemini_response, args=(key, prompt, result_queue))
        threads.append(thread)
        thread.start()

    try:
        result = result_queue.get(timeout=15)
        print(f"Fastest response from key ending in ...{result['key_used'][-4:]}")
        return result['text'], None
    except queue.Empty:
        print("All API keys failed or timed out.")
        return None, 'Could not get a response from the tarot spirits. Please try again.'
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None, str(e)

if __name__ == '__main__':
    app.run(debug=True)
