const insightsDiv = document.getElementById('insights');
const statusDiv = document.getElementById('connection-status');

// --- IMPORTANT: CONFIGURE WEBSOCKET URL ---
// Make sure this matches your deployed backend URL (wss://...run.app/ws)
const wsUrl = "wss://backend-272134414140.us-east1.run.app/ws"; // <-- DOUBLE-CHECK THIS URL

let socket;
let audioContext;
let processor;
let input;
let stream; // Keep track of the media stream

const SAMPLE_RATE = 16000;
const BUFFER_SIZE = 4096;

function connectWebSocket() {
    console.log("Attempting to connect to WebSocket:", wsUrl);
    statusDiv.textContent = "Connecting...";
    statusDiv.style.color = "#666";

    socket = new WebSocket(wsUrl);

    socket.onopen = function(event) {
        console.log("WebSocket connection opened:", event);
        statusDiv.textContent = "Connected. Requesting Mic...";
        statusDiv.style.color = "orange";
        requestMicrophoneAccess();
    };

    // *** THIS IS THE UPDATED MESSAGE HANDLER ***
    socket.onmessage = function(event) {
        console.log("Raw data received:", event.data); // Log raw data first

        let messageData;
        try {
            messageData = JSON.parse(event.data);
        } catch (e) {
            console.error("Received non-JSON message:", event.data);
            // Display raw non-JSON data as fallback
            const rawElement = document.createElement('div');
            rawElement.classList.add('raw-message');
            rawElement.textContent = `Raw: ${event.data}`;
            insightsDiv.insertBefore(rawElement, insightsDiv.firstChild);
            return; // Stop processing this message
        }

        console.log("Parsed message data:", messageData); // Log parsed data

        // Create elements based on message type
        const card = document.createElement('div');
        card.classList.add('message-card'); // General class for all messages

        if (messageData.type === "insight") {
            console.log("Processing insight:", messageData);
            card.classList.add('insight-card'); // Specific class for insights

            const header = document.createElement('div');
            header.classList.add('insight-header');
            // Basic icon map (can be extended)
            const icons = {
                "Radical Expander": "💡",
                "Fact Checker / Let's Check": "✅",
                "Strategic Re-framer": "📈",
                "Cross-Domain Connector": "🔗",
                "Takeaway Agent": "📝",
                "Controversy Agent": "🗣️",
                "Existential Debate Agent": "🎭",
            };
            header.textContent = `${icons[messageData.agent] || '🔹'} ${messageData.agent || 'Insight'}:`; // Show icon + Agent Name
            card.appendChild(header);

            const content = document.createElement('div');
            content.classList.add('insight-content');
            // Replace newline characters (\n) in the content with <br> tags for HTML display
            // Also handle potential errors if content is not a string
            let contentHtml = "[No content]";
            if (typeof messageData.content === 'string') {
                 contentHtml = messageData.content.replace(/\n/g, '<br>');
            } else {
                 console.warn("Insight content was not a string:", messageData.content);
                 contentHtml = JSON.stringify(messageData.content); // Show JSON if not string
            }
            content.innerHTML = contentHtml;
            card.appendChild(content);

        } else if (messageData.type === "transcript" && messageData.is_final) {
            // *** HIDE RAW TRANSCRIPTS NOW - Comment out/remove if you don't want them displayed ***
            // console.log("Processing final transcript:", messageData);
            // card.classList.add('transcript-card');
            // card.textContent = `Transcript: ${messageData.text}`;
            return; // Skip displaying raw transcripts on the page for now

        } else if (messageData.type === "error") {
            console.error("Processing error message:", messageData);
            card.classList.add('error-card');
            card.textContent = `Error [${messageData.agent || 'System'}]: ${messageData.message}`;

        } else {
             console.warn("Processing unknown message type:", messageData);
            // Fallback for other message types or raw transcripts if needed
            card.classList.add('raw-message');
            card.textContent = `Raw (${messageData.type || 'Unknown'}): ${messageData.text || JSON.stringify(messageData)}`;
        }

        // Add the new message card to the top of the insights div
        // Only add if it wasn't skipped (like raw transcripts might be)
        if (card.hasChildNodes() || card.textContent) {
             insightsDiv.insertBefore(card, insightsDiv.firstChild);
        }


        // Optional: Limit the number of messages shown
        const maxMessages = 20; // Limit total cards
        if (insightsDiv.children.length > maxMessages) {
            insightsDiv.removeChild(insightsDiv.lastChild);
        }
    };


    socket.onclose = function(event) {
        console.log("WebSocket connection closed:", event);
        statusDiv.textContent = `Disconnected (Code: ${event.code})`;
        statusDiv.style.color = "red";
        stopAudioProcessing();
        setTimeout(connectWebSocket, 5000);
    };

    socket.onerror = function(error) {
        console.error("WebSocket error:", error);
        statusDiv.textContent = "Connection Error";
        statusDiv.style.color = "red";
        stopAudioProcessing();
    };
}

async function requestMicrophoneAccess() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        statusDiv.textContent = "Mic Access Granted. Starting Audio...";
        statusDiv.style.color = "lightblue";
        startAudioProcessing(stream);
    } catch (err) {
        console.error("Error getting microphone access:", err);
        statusDiv.textContent = "Mic Access Denied!";
        statusDiv.style.color = "red";
    }
}

function startAudioProcessing(audioStream) {
    if (!socket || socket.readyState !== WebSocket.OPEN) { /* ... */ return; }
    audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: SAMPLE_RATE });
    input = audioContext.createMediaStreamSource(audioStream);
    processor = audioContext.createScriptProcessor(BUFFER_SIZE, 1, 1);
    processor.onaudioprocess = function(e) {
        if (!socket || socket.readyState !== WebSocket.OPEN) return;
        const audioData = e.inputBuffer.getChannelData(0);
        const int16Data = new Int16Array(audioData.length);
        for (let i = 0; i < audioData.length; i++) {
            int16Data[i] = Math.max(-1, Math.min(1, audioData[i])) * 32767;
        }
        socket.send(int16Data.buffer);
    };
    input.connect(processor);
    processor.connect(audioContext.destination);
    statusDiv.textContent = "Connected & Streaming Audio";
    statusDiv.style.color = "green";
    console.log("Audio processing started.");
}

function stopAudioProcessing() {
    if (stream) { stream.getTracks().forEach(track => track.stop()); stream = null; }
    if (input) { input.disconnect(); input = null; }
    if (processor) { processor.disconnect(); processor = null; }
    if (audioContext) { audioContext.close().then(() => console.log("AudioContext closed.")); audioContext = null; }
    console.log("Audio processing stopped.");
    if (statusDiv.textContent.includes("Streaming")) {
         statusDiv.textContent = "Connected (Mic Stopped)";
         statusDiv.style.color = "orange";
    }
}

connectWebSocket(); // Initial connection attempt
