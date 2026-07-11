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
  let synth = window.speechSynthesis;
  let audioContext = null;
  let mediaStream = null;
  let sttSocket = null;
  let processor = null;

  const startListening = async () => {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      sttSocket = new WebSocket(`${wsProtocol}//${window.location.host}/api/stt`);
      
      sttSocket.onopen = () => {
        isListening = true;
        speakBtn.classList.add('active');
        speakingIndicator.classList.remove('hidden');
        messageInput.placeholder = "Listening (Hindi/English)...";

        const source = audioContext.createMediaStreamSource(mediaStream);
        processor = audioContext.createScriptProcessor(1024, 1, 1);
        
        processor.onaudioprocess = (e) => {
          if (!isListening || sttSocket.readyState !== WebSocket.OPEN) return;
          const inputData = e.inputBuffer.getChannelData(0);
          const pcm16 = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
            pcm16[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7FFF;
          }
          sttSocket.send(pcm16.buffer);
        };
        
        source.connect(processor);
        processor.connect(audioContext.destination);
      };

      sttSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        messageInput.value = data.transcript;
        if (data.is_final) {
          stopListening();
          handleSendMessage(data.transcript);
        }
      };

      sttSocket.onerror = (error) => {
        console.error("STT WebSocket Error:", error);
        stopListening();
      };
      
      sttSocket.onclose = () => {
        stopListening();
      };
      
    } catch (err) {
      console.error("Error accessing microphone:", err);
      alert("Microphone access denied or unavailable.");
    }
  };

  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const stopListening = () => {
    isListening = false;
    speakBtn.classList.remove('active');
    speakingIndicator.classList.add('hidden');
    messageInput.placeholder = "Type a message or click the mic to speak...";
    
    if (processor) {
      processor.disconnect();
      processor = null;
    }
    if (audioContext) {
      audioContext.close();
      audioContext = null;
    }
    if (mediaStream) {
      mediaStream.getTracks().forEach(track => track.stop());
      mediaStream = null;
    }
    if (sttSocket && sttSocket.readyState === WebSocket.OPEN) {
      sttSocket.close();
      sttSocket = null;
    }
  };

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

      const json = await response.json();
      const responseText = json.text || "Here is your response.";
      
      let audioUrl = null;
      if (json.audioBase64) {
        audioUrl = `data:audio/mpeg;base64,${json.audioBase64}`;
      }
      
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
