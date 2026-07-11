import './style.css';

document.addEventListener('DOMContentLoaded', () => {
  const chatMessages = document.getElementById('chat-messages');
  const chatForm = document.getElementById('chat-form');
  const messageInput = document.getElementById('message-input');
  const newChatBtn = document.getElementById('new-chat-btn');
  const welcomeMessage = document.getElementById('welcome-message');
  const speakBtn = document.getElementById('speak-btn');
  const speakingIndicator = document.getElementById('speaking-indicator');

  let isListening = false;
  let recognition = null;
  let synth = window.speechSynthesis;

  // Initialize Speech Recognition if supported
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      isListening = true;
      speakBtn.classList.add('active');
      speakingIndicator.classList.remove('hidden');
      messageInput.placeholder = "Listening...";
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      messageInput.value = transcript;
      handleSendMessage(transcript);
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error", event.error);
      stopListening();
    };

    recognition.onend = () => {
      stopListening();
    };
  } else {
    speakBtn.style.display = 'none';
    console.warn("Speech recognition not supported in this browser.");
  }

  function toggleListening() {
    if (isListening) {
      recognition.stop();
    } else {
      recognition.start();
    }
  }

  function stopListening() {
    isListening = false;
    speakBtn.classList.remove('active');
    speakingIndicator.classList.add('hidden');
    messageInput.placeholder = "Type a message or click the mic to speak...";
  }

  speakBtn.addEventListener('click', toggleListening);

  // Load chat history from localStorage
  const loadChat = () => {
    const history = JSON.parse(localStorage.getItem('divineChatHistory')) || [];
    if (history.length > 0) {
      if(welcomeMessage) welcomeMessage.style.display = 'none';
      history.forEach(msg => {
        appendMessage(msg.text, msg.sender, false);
      });
      scrollToBottom();
    }
  };

  const saveChat = (text, sender) => {
    const history = JSON.parse(localStorage.getItem('divineChatHistory')) || [];
    history.push({ text, sender });
    localStorage.setItem('divineChatHistory', JSON.stringify(history));
  };

  const clearChat = () => {
    localStorage.removeItem('divineChatHistory');
    chatMessages.innerHTML = `
      <div class="welcome-message" id="welcome-message">
        <h2>Hi, I'm Divine</h2>
        <p>Your personal AI assistant. How can I help you today?</p>
      </div>
    `;
    synth.cancel(); // Stop speaking if generating new chat
  };

  const appendMessage = (text, sender, animate = true) => {
    if (document.getElementById('welcome-message')) {
      document.getElementById('welcome-message').style.display = 'none';
    }

    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender);
    msgDiv.textContent = text;
    if (!animate) {
      msgDiv.style.animation = 'none';
    }
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
  };

  const scrollToBottom = () => {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  };

  const speakText = (text) => {
    if (synth) {
      synth.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      // Optional: choose a specific voice
      const voices = synth.getVoices();
      const femaleVoice = voices.find(v => v.name.includes('Female') || v.name.includes('Google US English'));
      if (femaleVoice) utterance.voice = femaleVoice;
      utterance.rate = 0.9;
      utterance.pitch = 1.1;
      synth.speak(utterance);
    }
  };

  const getAIResponse = async (userMessage) => {
    // Show typing indicator or something similar here if desired.
    // For this mock, we will just use a generic response logic.
    // In production, you would do a fetch() to your backend API.
    
    // Fallback Mock Logic
    return new Promise((resolve) => {
      setTimeout(() => {
        let response = "I'm sorry, my connection to the server is currently simulated. How can I help you further?";
        const lowerMsg = userMessage.toLowerCase();
        
        if (lowerMsg.includes('hello') || lowerMsg.includes('hi')) {
          response = "Hello there! I'm Divine. What's on your mind today?";
        } else if (lowerMsg.includes('how are you')) {
          response = "I'm feeling fantastic, thank you for asking! Ready to assist you with anything you need.";
        } else if (lowerMsg.includes('name')) {
          response = "My name is Divine, your personal AI assistant.";
        } else if (lowerMsg.includes('deploy') || lowerMsg.includes('render')) {
          response = "Deploying on Render is easy! I've already prepared the requirements.txt and gunicorn settings for the backend.";
        }

        resolve(response);
      }, 1000);
    });
  };

  const handleSendMessage = async (textOverride = null) => {
    const text = textOverride || messageInput.value.trim();
    if (!text) return;

    messageInput.value = '';
    
    // User message
    appendMessage(text, 'user');
    saveChat(text, 'user');

    // Fetch AI response
    try {
      const responseText = await getAIResponse(text);
      appendMessage(responseText, 'ai');
      saveChat(responseText, 'ai');
      
      // Auto speak if they used voice to ask or if we want it always. 
      // For now, always speak response to showcase the voice capability.
      speakText(responseText);

    } catch (error) {
      appendMessage("Sorry, I encountered an error.", 'ai');
    }
  };

  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    handleSendMessage();
  });

  newChatBtn.addEventListener('click', () => {
    clearChat();
  });

  // Load voices proactively
  if (speechSynthesis.onvoiceschanged !== undefined) {
    speechSynthesis.onvoiceschanged = () => synth.getVoices();
  }

  loadChat();
});
