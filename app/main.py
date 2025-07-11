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

@app.route('/get_reading', methods=['POST'])
def get_reading():
    data = request.get_json()
    question = data.get('question')

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

    # 1. Draw three cards and determine their orientation
    drawn_cards_info = []
    sampled_cards = random.sample(TAROT_CARDS, 3)
    for card in sampled_cards:
        orientation = random.choice(['Upright', 'Reversed'])
        drawn_cards_info.append({**card, 'orientation': orientation})

    past_card, present_card, future_card = drawn_cards_info[0], drawn_cards_info[1], drawn_cards_info[2]

    # 2. **RAG Step**: Retrieve detailed meanings from the knowledge base
    def get_card_meaning(card_info):
        card_name = card_info['name']
        orientation = card_info['orientation'].lower()
        # Fallback to the card name if not found in the knowledge base
        knowledge = TAROT_KNOWLEDGE_BASE.get(card_name, {})
        return knowledge.get('meanings', {}).get(orientation, "No specific meaning found.")

    past_meaning = get_card_meaning(past_card)
    present_meaning = get_card_meaning(present_card)
    future_meaning = get_card_meaning(future_card)

    # 3. Create the augmented prompt for Gemini
    language_name = LANGUAGES.get(g.locale, 'English')
    translations = g.translations

    # Translate card names and orientation for the prompt and response
    past_card_name = translations['card_names'].get(past_card['name'], past_card['name'])
    present_card_name = translations['card_names'].get(present_card['name'], present_card['name'])
    future_card_name = translations['card_names'].get(future_card['name'], future_card['name'])

    past_orientation = translations.get(past_card['orientation'].lower(), past_card['orientation'])
    present_orientation = translations.get(present_card['orientation'].lower(), present_card['orientation'])
    future_orientation = translations.get(future_card['orientation'].lower(), future_card['orientation'])

    prompt = (
        f"You are {translations['aiName']}, a kind, cute, and professional tarot-reading cat. "
        f"You MUST use the provided context to interpret the cards. Do not use your own general knowledge of tarot.\n\n"
        f"Here is the user's conversation history:\n"
        f"---BEGIN CONVERSATION HISTORY---\n{history_string}---END CONVERSATION HISTORY---\n\n"
        f"The user's NEW question is: '{question}'\n\n"
        f"You have drawn three cards. Here is the relevant knowledge for each card:\n"
        f"---BEGIN TAROT KNOWLEDGE---\n"
        f"1. {translations['past']}: {past_card_name} ({past_orientation})\n"
        f"   - Meaning: {past_meaning}\n"
        f"2. {translations['present']}: {present_card_name} ({present_orientation})\n"
        f"   - Meaning: {present_meaning}\n"
        f"3. {translations['future']}: {future_card_name} ({future_orientation})\n"
        f"   - Meaning: {future_meaning}\n"
        f"---END TAROT KNOWLEDGE---\n\n"
        f"INSTRUCTIONS:\n"
        f"1. Give a nice, friendly, and comforting greeting.\n"
        f"2. Provide a gentle, comforting, and insightful interpretation based ONLY on the meanings provided above.\n"
        f"3. Directly relate your interpretation to the user's question: '{question}'.\n"
        f"4. Analyze the conversation history. If no history is provided, treat it as a fresh start, but don't mention it. If the new question is a follow-up, connect your new reading to the previous ones.\n"
        f"5. Structure your response with clear, bold headings for each card.\n"
        f"6. Provide a comprehensive and smart summary at the end, don't repeat the above paragraphs.\n"
        f"7. Respond entirely in {language_name} using Markdown format."
    )

    # 4. Get reading from Gemini using the fastest API key
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

    # 5. Prepare response
    response_data = {
        'reading': reading,
        'cards': {
            'past': {'name': past_card_name, 'img': url_for('static', filename=f'images/{past_card["img"]}'), 'orientation': past_orientation},
            'present': {'name': present_card_name, 'img': url_for('static', filename=f'images/{present_card["img"]}'), 'orientation': present_orientation},
            'future': {'name': future_card_name, 'img': url_for('static', filename=f'images/{future_card["img"]}'), 'orientation': future_orientation}
        }
    }
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True)
