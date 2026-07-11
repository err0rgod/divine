import './style.css';

document.addEventListener('DOMContentLoaded', () => {
  const orbBtn = document.getElementById('orb-btn');
  const statusText = document.getElementById('status-text');
  const langSelect = document.getElementById('lang-select');

  let isListening = false;
  let audioContext = null;
  let mediaStream = null;
  let sttSocket = null;
  let processor = null;
  let currentAudio = null;

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
        if (data.is_final) {
          stopListening();
          handleResponse(data.transcript, currentLang);
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
        audioUrl = `data:audio/mpeg;base64,${json.audioBase64}`;
      }
      return audioUrl;
    } catch (error) {
      console.error(error);
      return null;
    }
  };

  const handleResponse = async (transcript, language) => {
    setStatus('thinking', 'Divine is thinking...');
    
    const audioUrl = await getAIResponse(transcript, language);
    
    if (audioUrl) {
      setStatus('speaking', 'Divine is speaking...');
      currentAudio = new Audio(audioUrl);
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
    if (isListening) {
      stopListening();
      setStatus('', 'Tap to connect');
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

});
