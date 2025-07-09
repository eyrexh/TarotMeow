function typeMessage(element, message) {
    element.innerHTML = ''; // Clear the bubble first
    const cursor = document.createElement('span');
    cursor.className = 'typing-cursor';
    element.appendChild(cursor);

    // 1. Tokenize the message string into an array of characters, tags, and entities
    const tokens = [];
    for (let i = 0; i < message.length; ) {
        const char = message[i];
        if (char === '<') {
            const tagEnd = message.indexOf('>', i);
            if (tagEnd !== -1) {
                tokens.push(message.substring(i, tagEnd + 1));
                i = tagEnd + 1;
                continue;
            }
        }
        if (char === '&') {
            const entityEnd = message.indexOf(';', i);
            if (entityEnd !== -1) {
                const entity = message.substring(i, entityEnd + 1);
                // A simple check for valid-looking HTML entities
                if (entity.length > 2 && entity.length < 10) {
                    tokens.push(entity);
                    i = entityEnd + 1;
                    continue;
                }
            }
        }
        // It's a plain character
        tokens.push(message[i]);
        i++;
    }

    // 2. Type out the tokens one by one
    let tokenIndex = 0;
    function type() {
        if (tokenIndex < tokens.length) {
            const token = tokens[tokenIndex];
            // All tokens (tags, entities, and plain chars) can be safely inserted as HTML
            cursor.insertAdjacentHTML('beforebegin', token);
            tokenIndex++;
            setTimeout(type, 25); // Adjust typing speed here
        } else {
            cursor.remove(); // Remove cursor when typing is done
        }
    }

    type();
}
