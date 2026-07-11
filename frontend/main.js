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
    // Show a small UI indication if desired
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage })
      });
      
      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      // The server sends back the text response in a custom header
      const responseText = response.headers.get('X-Response-Text') || "Here is your response.";
      
      // Get the audio bytes
      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      
      return { text: responseText, audioUrl };
    } catch (error) {
      console.error(error);
      return { text: "I'm sorry, I couldn't connect to the server.", audioUrl: null };
    }
  };

  const handleSendMessage = async (textOverride = null) => {
    const text = textOverride || messageInput.value.trim();
    if (!text) return;

    messageInput.value = '';
    
    // User message
    appendMessage(text, 'user');
    saveChat(text, 'user');

    // Show indicator
    const aiMessageDiv = document.createElement('div');
    aiMessageDiv.classList.add('message', 'ai');
    aiMessageDiv.textContent = '...';
    chatMessages.appendChild(aiMessageDiv);
    scrollToBottom();

    // Fetch AI response
    try {
      const { text: responseText, audioUrl } = await getAIResponse(text);
      aiMessageDiv.textContent = responseText;
      saveChat(responseText, 'ai');
      
      // Play the audio
      if (audioUrl) {
        if (synth) synth.cancel(); // Stop browser TTS if any
        const audio = new Audio(audioUrl);
        audio.play().catch(e => console.error("Audio play error:", e));
      }

    } catch (error) {
      aiMessageDiv.textContent = "Sorry, I encountered an error.";
    }
    scrollToBottom();
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
