# TarotMeow 😺🔮

**Step into a world of digital mysticism with TarotMeow, your personal AI cat tarot reader!**

Have a question for the universe? Let our wise and witty feline guide draw the cards for you and unveil the secrets of the past, present, and future. Whether you seek deep insights or a playful chat, TarotMeow is here to provide a comforting and enchanting experience.

## ✨ [**Visit the Live App!**](https://tarotmeow.onrender.com) ✨

---

<!-- Placeholder: Replace with a real screenshot URL -->

## Features

* **AI-Powered Tarot Readings:** Get a three-card (Past, Present, Future) reading for any question you have.
* **Context-Aware Conversations:** Ask follow-up questions! TarotMeow remembers your previous reading and provides continuous, relevant insights.
* **Cute Cat Personality:** Our AI guide communicates with adorable cat emojis (😺, 🐾, 😻) for a fun and friendly chat.
* **Bilingual Support:** Fully localized for both English and Simplified Chinese (简体中文).
* **Sleek, Animated UI:** Enjoy a beautiful, mystical interface with smooth card-flipping animations.
* **Markdown Support:** AI responses are beautifully formatted with bold titles and structured text for easy reading.

## How It Works: The Tech Stack

TarotMeow is built with a modern web stack, combining a powerful Python backend with a dynamic frontend.

* **Backend:**
  * **Framework:** [Flask](https://flask.palletsprojects.com/)
  * **AI:** [Google Gemini API](https://ai.google.dev/)
  * **Localization:** [Flask-Babel](https://python-babel.github.io/flask-babel/)
  * **Server:** [Gunicorn](https://gunicorn.org/) for production

* **Frontend:**
  * HTML5, CSS3, Vanilla JavaScript
  * [Marked.js](https://marked.js.org/) for rendering Markdown in the browser.

## Local Development Setup

Want to run TarotMeow on your own machine? Follow these steps:

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/eyrexh/TarotMeow.git
   cd TarotMeow
   ```

2. **Set up a Virtual Environment (Recommended):**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Create Your Environment File:**

   Create a file named `.env` in the root directory and add your Gemini API key. You can have multiple keys.

   ```dotenv
   GEMINI_API_KEY_1="YOUR_API_KEY_HERE"
   GEMINI_API_KEY_2="ANOTHER_API_KEY_HERE"
   FLASK_SECRET_KEY="ANY_RANDOM_STRONG_SECRET_KEY"
   ```

5. **Run the Application:**

   ```bash
   python3 app/main.py
   ```

   The app will be running at `http://127.0.0.1:5000`.

## Deployment

This application is deployed on [Render](https://render.com/). The `Procfile` instructs Render to use `gunicorn` to run the Flask application. Environment variables (like the API keys) are configured securely in the Render dashboard.

Auto-deployment is enabled, so any push to the `main` branch will automatically trigger a new build and update the live site.

---

Enjoy your journey into the mystical world of TarotMeow! 🐾
