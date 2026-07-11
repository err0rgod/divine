import './style.css';

document.addEventListener('DOMContentLoaded', () => {
  const orbBtn = document.getElementById('orb-btn');
  const statusText = document.getElementById('status-text');
  const langSelect = document.getElementById('lang-select');
  
  // Tabs
  const tabVoice = document.getElementById('tab-voice');
  const tabChat = document.getElementById('tab-chat');
  const viewVoice = document.getElementById('view-voice');
  const viewChat = document.getElementById('view-chat');

  // Chat UI Elements
  const chatMessages = document.getElementById('chat-messages');
  const chatForm = document.getElementById('chat-form');
  const messageInput = document.getElementById('message-input');
  const welcomeMessage = document.getElementById('welcome-message');

  let isListening = false;
  let audioContext = null;
  let mediaStream = null;
  let sttSocket = null;
  let processor = null;
  let currentAudio = null;

  // Tab Switching
  tabVoice.addEventListener('click', () => {
    tabVoice.classList.add('active');
    tabChat.classList.remove('active');
    viewVoice.classList.add('active');
    viewChat.classList.remove('active');
  });

  tabChat.addEventListener('click', () => {
    tabChat.classList.add('active');
    tabVoice.classList.remove('active');
    viewChat.classList.add('active');
    viewVoice.classList.remove('active');
    stopListening(); // stop orb if active
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
      setStatus('', 'Tap to connect');
    }
  });

  const setStatus = (status, text) => {
    orbBtn.className = 'orb-container ' + status;
    statusText.textContent = text;
  };

  const startListening = async () => {
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }

    const currentLang = langSelect.value;

    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      sttSocket = new WebSocket(`${wsProtocol}//${window.location.host}/api/stt?lang=${currentLang}`);
      
      sttSocket.onopen = () => {
        isListening = true;
        setStatus('listening', 'Listening...');

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
        console.log("Sarvam WS Payload:", data);
        
        if (data.transcript && !data.is_final) {
          // Show partial transcript in the UI!
          setStatus('listening', `"${data.transcript}"`);
        }
        
        if (data.is_final) {
          stopListening();
          if (data.transcript) {
            handleVoiceResponse(data.transcript, currentLang);
          } else {
            setStatus('', 'Tap to connect');
          }
        }
      };

      sttSocket.onerror = (error) => {
        console.error("STT WebSocket Error:", error);
        stopListening();
        setStatus('', 'Connection error. Tap to retry.');
      };
      
      sttSocket.onclose = () => {
        stopListening();
      };
      
    } catch (err) {
      console.error("Error accessing microphone:", err);
      setStatus('', 'Microphone access denied. Tap to retry.');
    }
  };

  const stopListening = () => {
    isListening = false;
    
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

  const getAIResponse = async (userMessage, language) => {
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage, language: language })
      });
      
      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const json = await response.json();
      let audioUrl = null;
      if (json.audioBase64) {
        audioUrl = `data:audio/wav;base64,${json.audioBase64}`;
      }
      return { text: json.text, audioUrl };
    } catch (error) {
      console.error(error);
      return { text: "Error connecting to server.", audioUrl: null };
    }
  };

  const handleVoiceResponse = async (transcript, language) => {
    setStatus('thinking', 'Divine is thinking...');
    
    const result = await getAIResponse(transcript, language);
    
    if (result && result.audioUrl) {
      setStatus('speaking', 'Divine is speaking...');
      currentAudio = new Audio(result.audioUrl);
      currentAudio.onended = () => {
        setStatus('', 'Tap to connect');
        currentAudio = null;
      };
      currentAudio.play().catch(e => {
        console.error("Audio play error:", e);
        setStatus('', 'Tap to connect');
      });
    } else {
      setStatus('', 'Error occurred. Tap to retry.');
    }
  };

  orbBtn.addEventListener('click', () => {
    if (orbBtn.classList.contains('listening')) {
      // User tapped while listening -> tell Sarvam we are done speaking
      if (sttSocket && sttSocket.readyState === WebSocket.OPEN) {
        sttSocket.send("STOP");
        setStatus('thinking', 'Divine is thinking...');
      } else {
        stopListening();
        setStatus('', 'Tap to connect');
      }
    } else if (orbBtn.classList.contains('speaking')) {
      if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
      }
      setStatus('', 'Tap to connect');
    } else if (!orbBtn.classList.contains('thinking')) {
      startListening();
    }
  });

  // --- Chat UI Logic --- //
  
  const appendMessage = (text, sender) => {
    if (welcomeMessage) welcomeMessage.style.display = 'none';
    
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender);
    msgDiv.textContent = text;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  };

  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = messageInput.value.trim();
    if (!text) return;

    messageInput.value = '';
    appendMessage(text, 'user');
    
    // Stop any currently playing audio if user sends a new message
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }

    const aiMessageDiv = document.createElement('div');
    aiMessageDiv.classList.add('message', 'ai');
    aiMessageDiv.textContent = '...';
    chatMessages.appendChild(aiMessageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    const currentLang = langSelect.value;
    const result = await getAIResponse(text, currentLang);
    
    if (result) {
      aiMessageDiv.textContent = result.text;
      chatMessages.scrollTop = chatMessages.scrollHeight;
      
      if (result.audioUrl) {
        currentAudio = new Audio(result.audioUrl);
        currentAudio.play().catch(console.error);
      }
    }
  });

});
