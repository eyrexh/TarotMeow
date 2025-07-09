document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const introOverlay = document.getElementById('intro-overlay');
    const beginBtn = document.getElementById('begin-btn');
    const chatContainer = document.querySelector('.chat-container');
    const messageList = document.getElementById('message-list');
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');

    // --- Event Listeners ---

    // Start Chat
    beginBtn.addEventListener('click', () => {
        introOverlay.style.opacity = '0';
        setTimeout(() => {
            introOverlay.style.display = 'none';
            chatContainer.style.display = 'flex';
            chatContainer.style.opacity = '1';
            addTarotMessage("Welcome, My human friend! I am TarotMeow, ready to reveal the secrets of the cards. What would you like to ask?");
        }, 500); // Match CSS transition duration
    });

    // --- Event Listeners ---
    function handleSendMessage() {
        const question = messageInput.value.trim();
        if (question) {
            addUserMessage(question);
            getTarotReading(question);
            messageInput.value = '';
        }
    }

    sendBtn.addEventListener('click', handleSendMessage);

    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault(); // Stop default 'Enter' behavior (like form submission)
            handleSendMessage();
        }
    });

    // --- Functions ---

    function addUserMessage(message) {
        appendMessage(message, 'user');
    }

    function addTarotMessage(message, useTypingEffect = false) {
        // Convert markdown bold and italics to HTML
        const formattedMessage = marked.parse(message);

        if (useTypingEffect) {
            const messageElement = appendMessage('', 'tarot');
            const bubble = messageElement.querySelector('.tarot-bubble');
            typeMessage(bubble, formattedMessage);
        } else {
            appendMessage(formattedMessage, 'tarot');
        }
    }

    function appendMessage(content, sender, bubbleType = 'text') {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', sender);

        if (sender === 'tarot') {
            const mascot = document.createElement('img');
            mascot.src = '/static/images/wizard-cat.png';
            mascot.alt = 'TarotMeow Mascot';
            mascot.className = 'tarot-mascot';
            messageElement.appendChild(mascot);

            const bubble = document.createElement('div');
            bubble.className = 'tarot-bubble';
            if (bubbleType === 'card') {
                bubble.classList.add('card-bubble');
                messageElement.classList.add('card-message');
            }

            if (typeof content === 'string') {
                bubble.innerHTML = content;
            } else {
                bubble.appendChild(content);
            }
            messageElement.appendChild(bubble);
        } else { // user
            messageElement.textContent = content;
        }
        
        messageList.appendChild(messageElement);
        messageList.scrollTop = messageList.scrollHeight;
        return messageElement;
    }

    function showTypingIndicator() {
        const typingIndicator = document.createElement('div');
        typingIndicator.id = 'typing-indicator';
        typingIndicator.classList.add('message', 'tarot');
        
        const mascot = document.createElement('img');
        mascot.src = '/static/images/wizard-cat.png';
        mascot.alt = 'TarotMeow Mascot';
        mascot.className = 'tarot-mascot';
        typingIndicator.appendChild(mascot);

        const bubble = document.createElement('div');
        bubble.className = 'tarot-bubble';
        bubble.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
        typingIndicator.appendChild(bubble);

        messageList.appendChild(typingIndicator);
        messageList.scrollTop = messageList.scrollHeight;
    }

    function removeTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    function displayCards(cards, container, reading) {
        container.innerHTML = ''; // Clear previous cards
        const displayOrder = ['past', 'present', 'future'];
        let flippedCount = 0;

        const revealBtn = document.createElement('button');
        revealBtn.id = 'reveal-reading-btn';
        revealBtn.textContent = 'See Card Reading';
        revealBtn.style.display = 'none'; // Hide it initially
        container.parentNode.insertBefore(revealBtn, container.nextSibling);

        revealBtn.addEventListener('click', () => {
            addTarotMessage(reading, true); // Use typing effect for the main reading
            revealBtn.style.display = 'none'; // Hide button after click
        }, { once: true });

        displayOrder.forEach(position => {
            const cardData = cards[position];
            if (!cardData) return; // Failsafe

            const cardContainer = document.createElement('div');
            cardContainer.className = 'card-container';

            const cardFlipper = document.createElement('div');
            cardFlipper.className = 'card-flipper';

            // Card Front
            const cardFront = document.createElement('div');
            cardFront.className = 'card-face card-front';
            const img = document.createElement('img');
            img.src = cardData.img;
            img.alt = cardData.name;
            if (cardData.orientation === 'Reversed') {
                img.classList.add('reversed');
            }
            cardFront.appendChild(img);

            // Card Back
            const cardBack = document.createElement('div');
            cardBack.className = 'card-face card-back';
            const backImg = document.createElement('img');
            backImg.src = '/static/images/card_back.jpg';
            backImg.alt = 'Card Back';
            cardBack.appendChild(backImg);

            const positionLabel = document.createElement('p');
            positionLabel.textContent = position.charAt(0).toUpperCase() + position.slice(1);

            const nameLabel = document.createElement('span');
            let cardName = cardData.name;
            if (cardData.orientation === 'Reversed') {
                cardName += ' (Reversed)';
            }
            nameLabel.textContent = cardName;

            cardFlipper.appendChild(cardBack);
            cardFlipper.appendChild(cardFront);
            cardContainer.appendChild(cardFlipper);
            cardContainer.appendChild(positionLabel);
            cardContainer.appendChild(nameLabel);

            container.appendChild(cardContainer);

            cardFlipper.addEventListener('click', () => {
                if (!cardFlipper.classList.contains('flipped')) {
                    cardFlipper.classList.add('flipped');
                    flippedCount++;
                    if (flippedCount === 3) {
                        revealBtn.style.display = 'block';
                    }
                }
            }, { once: true });
        });
    }

    async function getTarotReading(question) {
        // Add a message to focus the user's energy
        addTarotMessage("Hold your question in your mind... Breathe... The cards are listening.", true);
        await new Promise(resolve => setTimeout(resolve, 2500)); // Pause for reflection

        const readingPromise = fetch('/get_reading', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question }),
        });

        const animationContainer = document.createElement('div');
        animationContainer.className = 'shuffle-animation-container';
        const animationMessage = appendMessage(animationContainer, 'tarot', 'card');

        animationContainer.innerHTML = '<div class="shuffling-card"></div>';
        await new Promise(resolve => setTimeout(resolve, 1200));

        animationContainer.innerHTML = `
            <div class="shuffling-card" style="animation: deal-past 0.5s forwards;"></div>
            <div class="shuffling-card" style="animation: deal-present 0.5s forwards;"></div>
            <div class="shuffling-card" style="animation: deal-future 0.5s forwards;"></div>
        `;
        await new Promise(resolve => setTimeout(resolve, 600));

        try {
            const response = await readingPromise;
            if (!response.ok) {
                animationMessage.remove();
                throw new Error('The cards are shy... please try again.');
            }
            const data = await response.json();

            // The reading is now passed to displayCards, which handles the reveal
            animationContainer.className = 'card-display-container';
            displayCards(data.cards, animationContainer, data.reading);

        } catch (error) {
            const animationBubble = document.querySelector('.shuffle-animation-container');
            if (animationBubble) animationBubble.closest('.message').remove();
            addTarotMessage(error.message || 'An error occurred. Please try again.');
        }
    }

    function scrollToBottom() {
        messageList.scrollTop = messageList.scrollHeight;
    }

    // --- Initial Setup ---
    beginBtn.textContent = "Begin";
    document.querySelector('#intro-content h1').textContent = "TarotMeow";
    document.querySelector('#intro-content p').textContent = "Get a tarot reading from the mystical cat.";
    messageInput.placeholder = "Type your question...";
});