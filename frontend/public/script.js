// Configuration
const insightDiv = document.getElementById('insights');
const savedInsightsDiv = document.getElementById('saved-insights');
const connectionStatus = document.getElementById('connection-status');
const micStatus = document.getElementById('mic-status');
const emptyInsights = document.getElementById('empty-insights');
const filterButtons = document.querySelectorAll('.filter-btn');
const clearSavedBtn = document.getElementById('clear-saved');

// WebSocket URL - Make sure this matches your backend
const wsUrl = "wss://backend-272134414140.us-east1.run.app/ws";

// Sound file paths
const soundPaths = {
    "Radical Expander": "sound-radical",
    "Wild Product Agent": "sound-product",
    "Skeptical Agent": "sound-skeptical",
    "Debate Agent": "sound-debate",
    "One Small Thing": "sound-one-small-thing",
    "Disruptor": "sound-disruptor",
    "error": "sound-error"
};

// Agent icons
const agentIcons = {
    "Radical Expander": "fa-bolt",
    "Wild Product Agent": "fa-lightbulb",
    "Skeptical Agent": "fa-question-circle",
    "Debate Agent": "fa-comments",
    "One Small Thing": "fa-check-circle",
    "Disruptor": "fa-rocket",
    "System": "fa-exclamation-circle"
};

// Store for saved insights
let savedInsights = JSON.parse(localStorage.getItem('savedInsights') || '[]');
let activeFilter = 'all';
let socket;
let audioContext;
let processor;
let input;
let stream;
const SAMPLE_RATE = 16000;
const BUFFER_SIZE = 4096;

// Initialize the app
function init() {
    renderSavedInsights();
    setupEventListeners();
    connectWebSocket();
}

// Event Listeners
function setupEventListeners() {
    // Filter buttons
    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            activeFilter = button.dataset.filter;
            
            // Update active button styling
            filterButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Filter insights
            filterInsights();
        });
    });
    
    // Clear saved insights
    if (clearSavedBtn) {
        clearSavedBtn.addEventListener('click', clearSavedInsights);
    }
}

// Connect to WebSocket
function connectWebSocket() {
    console.log("Attempting to connect to WebSocket:", wsUrl);
    updateConnectionStatus('connecting');
    
    socket = new WebSocket(wsUrl);
    
    socket.onopen = function(event) {
        console.log("WebSocket connection opened:", event);
        updateConnectionStatus('connected');
        requestMicrophoneAccess();
    };
    
    socket.onmessage = function(event) {
        console.log("Raw data received:", event.data);
        
        let messageData;
        try {
            messageData = JSON.parse(event.data);
            handleMessage(messageData);
        } catch (e) {
            console.error("Received non-JSON message:", event.data);
            showError("Received invalid data format");
        }
    };
    
    socket.onclose = function(event) {
        console.log("WebSocket connection closed:", event);
        updateConnectionStatus('disconnected');
        stopAudioProcessing();
        setTimeout(connectWebSocket, 5000);
    };
    
    socket.onerror = function(error) {
        console.error("WebSocket error:", error);
        updateConnectionStatus('error');
        stopAudioProcessing();
    };
}

// Handle WebSocket Messages
function handleMessage(messageData) {
    console.log("Parsed message data:", messageData);
    
    // Hide empty state if it's still showing
    if (emptyInsights) {
        emptyInsights.style.display = 'none';
    }
    
    if (messageData.type === "insight") {
        addInsightCard(messageData);
        playSound(messageData.agent);
    } 
    else if (messageData.type === "error") {
        showError(messageData.message || "Unknown error occurred", messageData.agent);
        playSound("error");
    }
    else if (messageData.type === "transcript" && messageData.is_final) {
        // Transcript handling can be re-enabled if needed
        return;
    } 
    else {
        console.warn("Unknown message type:", messageData.type);
    }
}

// Create and Add Insight Card
function addInsightCard(insightData) {
    const agent = insightData.agent;
    const content = insightData.content;
    
    // Create card elements
    const card = document.createElement('div');
    card.className = `insight-card agent-${convertAgentClassname(agent)}`;
    card.dataset.agent = agent;
    
    // Create card header
    const cardHeader = document.createElement('div');
    cardHeader.className = 'card-header';
    
    // Agent info section
    const agentInfo = document.createElement('div');
    agentInfo.className = 'agent-info';
    
    const agentIcon = document.createElement('div');
    agentIcon.className = 'agent-icon';
    const iconEl = document.createElement('i');
    iconEl.className = `fas ${agentIcons[agent] || 'fa-robot'}`;
    agentIcon.appendChild(iconEl);
    
    const agentName = document.createElement('div');
    agentName.className = 'agent-name';
    agentName.textContent = agent;
    
    agentInfo.appendChild(agentIcon);
    agentInfo.appendChild(agentName);
    
    // Card actions
    const cardActions = document.createElement('div');
    cardActions.className = 'card-actions';
    
    const saveButton = document.createElement('button');
    saveButton.className = 'card-action-btn save-insight';
    saveButton.title = 'Save this insight';
    const saveIcon = document.createElement('i');
    saveIcon.className = 'fas fa-bookmark';
    saveButton.appendChild(saveIcon);
    saveButton.addEventListener('click', () => saveInsight(agent, content));
    
    const dismissButton = document.createElement('button');
    dismissButton.className = 'card-action-btn dismiss-insight';
    dismissButton.title = 'Dismiss this insight';
    const dismissIcon = document.createElement('i');
    dismissIcon.className = 'fas fa-times';
    dismissButton.appendChild(dismissIcon);
    dismissButton.addEventListener('click', () => dismissInsight(card));
    
    cardActions.appendChild(saveButton);
    cardActions.appendChild(dismissButton);
    
    // Assemble header
    cardHeader.appendChild(agentInfo);
    cardHeader.appendChild(cardActions);
    
    // Create content
    const cardContent = document.createElement('div');
    cardContent.className = 'card-content';
    cardContent.innerHTML = formatContent(content);
    
    // Add expand button
    const expandBtn = document.createElement('button');
    expandBtn.className = 'expand-btn';
    expandBtn.textContent = 'Read More';
    expandBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        cardContent.classList.toggle('expanded');
        expandBtn.textContent = cardContent.classList.contains('expanded') ? 'Show Less' : 'Read More';
    });
    
    // Assemble card
    card.appendChild(cardHeader);
    card.appendChild(cardContent);
    card.appendChild(expandBtn);
    
    // Add to container with animation
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px)';
    
    // Insert at the beginning
    if (insightDiv.firstChild) {
        insightDiv.insertBefore(card, insightDiv.firstChild);
    } else {
        insightDiv.appendChild(card);
    }
    
    // Trigger animation
    setTimeout(() => {
        card.style.opacity = '1';
        card.style.transform = 'translateY(0)';
    }, 10);
    
    // Apply active filter
    if (activeFilter !== 'all' && agent !== activeFilter) {
        card.style.display = 'none';
    }
}

// Format content with line breaks and styling
function formatContent(content) {
    if (!content) return '';
    
    // Replace newlines with <br>
    let formatted = content.replace(/\n/g, '<br>');
    
    // Make bold text wrapped in ** or __
    formatted = formatted.replace(/(\*\*|__)(.*?)\1/g, '<strong>$2</strong>');
    
    // Make bullet points more visually appealing
    formatted = formatted.replace(/^•\s+(.*)/gm, '<div class="bullet-point">• $1</div>');
    
    return formatted;
}

// Play sound for agent
function playSound(agent) {
    const soundId = soundPaths[agent] || soundPaths.error;
    const sound = document.getElementById(soundId);
    
    if (sound) {
        // Reset and play
        sound.pause();
        sound.currentTime = 0;
        
        // Try to play (handle autoplay restrictions)
        const playPromise = sound.play();
        if (playPromise !== undefined) {
            playPromise.catch(error => {
                console.warn("Audio play failed:", error);
            });
        }
    }
}

// Save insight to sidebar
function saveInsight(agent, content) {
    // Create unique ID
    const id = Date.now().toString();
    
    // Add to saved insights array
    savedInsights.push({
        id,
        agent,
        content,
        timestamp: new Date().toISOString()
    });
    
    // Save to localStorage
    localStorage.setItem('savedInsights', JSON.stringify(savedInsights));
    
    // Render updated saved insights
    renderSavedInsights();
    
    // Show visual feedback
    showToast('Insight saved');
}

// Render saved insights in sidebar
function renderSavedInsights() {
    if (!savedInsightsDiv) return;
    
    // Clear container
    savedInsightsDiv.innerHTML = '';
    
    // If empty, show empty state
    if (savedInsights.length === 0) {
        const emptyState = document.createElement('div');
        emptyState.className = 'empty-state';
        
        const icon = document.createElement('i');
        icon.className = 'fas fa-bookmark';
        
        const text = document.createElement('p');
        text.textContent = 'Save important insights here';
        
        emptyState.appendChild(icon);
        emptyState.appendChild(text);
        savedInsightsDiv.appendChild(emptyState);
        return;
    }
    
    // Render each saved insight
    savedInsights.forEach(insight => {
        const card = document.createElement('div');
        card.className = `saved-card agent-${convertAgentClassname(insight.agent)}-border`;
        card.dataset.id = insight.id;
        
        const header = document.createElement('div');
        header.className = 'saved-card-header';
        
        const icon = document.createElement('i');
        icon.className = `fas ${agentIcons[insight.agent] || 'fa-robot'}`;
        
        const name = document.createElement('span');
        name.textContent = insight.agent;
        
        header.appendChild(icon);
        header.appendChild(name);
        
        const content = document.createElement('div');
        content.className = 'saved-card-content';
        content.textContent = insight.content.replace(/<[^>]*>/g, '').substring(0, 100);
        
        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-saved';
        removeBtn.title = 'Remove from saved';
        
        const removeIcon = document.createElement('i');
        removeIcon.className = 'fas fa-times';
        
        removeBtn.appendChild(removeIcon);
        removeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            removeSavedInsight(insight.id);
        });
        
        card.appendChild(header);
        card.appendChild(content);
        card.appendChild(removeBtn);
        
        // Make the card expandable to see full content
        card.addEventListener('click', () => expandSavedInsight(insight));
        
        savedInsightsDiv.appendChild(card);
    });
}

// Expand a saved insight to show full content
function expandSavedInsight(insight) {
    // You could show a modal or expand in place
    alert(`${insight.agent}:\n\n${insight.content.replace(/<[^>]*>/g, '')}`);
}

// Remove a saved insight
function removeSavedInsight(id) {
    savedInsights = savedInsights.filter(insight => insight.id !== id);
    localStorage.setItem('savedInsights', JSON.stringify(savedInsights));
    renderSavedInsights();
    showToast('Insight removed');
}

// Clear all saved insights
function clearSavedInsights() {
    if (confirm('Clear all saved insights?')) {
        savedInsights = [];
        localStorage.setItem('savedInsights', JSON.stringify(savedInsights));
        renderSavedInsights();
        showToast('All insights cleared');
    }
}

// Dismiss an insight card
function dismissInsight(card) {
    // Animate out
    card.style.opacity = '0';
    card.style.transform = 'translateY(-20px)';
    
    // Remove after animation completes
    setTimeout(() => {
        card.remove();
        
        // Show empty state if no insights left
        if (insightDiv.children.length === 0) {
            if (emptyInsights) {
                emptyInsights.style.display = 'flex';
            }
        }
    }, 300);
}

// Filter insights based on selected agent
function filterInsights() {
    const cards = insightDiv.querySelectorAll('.insight-card');
    
    cards.forEach(card => {
        if (activeFilter === 'all' || card.dataset.agent === activeFilter) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}

// Show error message
function showError(message, agent = 'System') {
    const card = document.createElement('div');
    card.className = 'insight-card agent-error';
    
    const cardHeader = document.createElement('div');
    cardHeader.className = 'card-header';
    
    const agentInfo = document.createElement('div');
    agentInfo.className = 'agent-info';
    
    const agentIcon = document.createElement('div');
    agentIcon.className = 'agent-icon';
    const iconEl = document.createElement('i');
    iconEl.className = 'fas fa-exclamation-triangle';
    agentIcon.appendChild(iconEl);
    
    const agentName = document.createElement('div');
    agentName.className = 'agent-name';
    agentName.textContent = `${agent} Error`;
    
    agentInfo.appendChild(agentIcon);
    agentInfo.appendChild(agentName);
    
    const cardContent = document.createElement('div');
    cardContent.className = 'card-content';
    cardContent.textContent = message;
    
    const dismissButton = document.createElement('button');
    dismissButton.className = 'card-action-btn dismiss-insight';
    dismissButton.title = 'Dismiss this error';
    const dismissIcon = document.createElement('i');
    dismissIcon.className = 'fas fa-times';
    dismissButton.appendChild(dismissIcon);
    dismissButton.addEventListener('click', () => dismissInsight(card));
    
    const cardActions = document.createElement('div');
    cardActions.className = 'card-actions';
    cardActions.appendChild(dismissButton);
    
    cardHeader.appendChild(agentInfo);
    cardHeader.appendChild(cardActions);
    
    card.appendChild(cardHeader);
    card.appendChild(cardContent);
    
    if (insightDiv.firstChild) {
        insightDiv.insertBefore(card, insightDiv.firstChild);
    } else {
        insightDiv.appendChild(card);
    }
}

// Show toast notification
function showToast(message) {
    // Create toast element if it doesn't exist
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        document.body.appendChild(toast);
        
        // Add some basic styling
        toast.style.position = 'fixed';
        toast.style.bottom = '20px';
        toast.style.right = '20px';
        toast.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
        toast.style.color = 'white';
        toast.style.padding = '10px 20px';
        toast.style.borderRadius = '4px';
        toast.style.zIndex = '1000';
        toast.style.transition = 'opacity 0.3s ease';
    }
    
    // Update message and show
    toast.textContent = message;
    toast.style.opacity = '1';
    
    // Auto hide after 3 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
    }, 3000);
}

// Update connection status UI
function updateConnectionStatus(status) {
    if (!connectionStatus) return;
    
    connectionStatus.className = 'connection-status';
    
    switch (status) {
        case 'connecting':
            connectionStatus.classList.add('connecting');
            connectionStatus.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> <span>Connecting...</span>';
            break;
        case 'connected':
            connectionStatus.classList.add('connected');
            connectionStatus.innerHTML = '<i class="fas fa-plug"></i> <span>Connected</span>';
            break;
        case 'disconnected':
            connectionStatus.classList.add('disconnected');
            connectionStatus.innerHTML = '<i class="fas fa-unlink"></i> <span>Disconnected</span>';
            break;
        case 'error':
            connectionStatus.classList.add('disconnected');
            connectionStatus.innerHTML = '<i class="fas fa-exclamation-triangle"></i> <span>Connection Error</span>';
            break;
    }
}

// Update microphone status UI
function updateMicStatus(active) {
    if (!micStatus) return;
    
    if (active) {
        micStatus.className = 'mic-status active';
        micStatus.innerHTML = '<i class="fas fa-microphone"></i> <span>Listening</span>';
    } else {
        micStatus.className = 'mic-status';
        micStatus.innerHTML = '<i class="fas fa-microphone-slash"></i> <span>Microphone inactive</span>';
    }
}

// Audio Processing Functions
async function requestMicrophoneAccess() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        updateMicStatus(true);
        startAudioProcessing(stream);
    } catch (err) {
        console.error("Error getting microphone access:", err);
        updateMicStatus(false);
        showError("Microphone access denied. Please enable microphone permissions.");
    }
}

function startAudioProcessing(audioStream) {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    
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
    console.log("Audio processing started.");
}

function stopAudioProcessing() {
    updateMicStatus(false);
    
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
    
    if (input) {
        input.disconnect();
        input = null;
    }
    
    if (processor) {
        processor.disconnect();
        processor = null;
    }
    
    if (audioContext) {
        audioContext.close().then(() => console.log("AudioContext closed."));
        audioContext = null;
    }
    
    console.log("Audio processing stopped.");
}

// Helper to convert agent name to CSS class-friendly format
function convertAgentClassname(agent) {
    if (!agent) return 'unknown';
    
    // Agent name to CSS class mapping
    const agentClassMap = {
        'Radical Expander': 'radical-expander',
        'Wild Product Agent': 'wild-product',
        'Skeptical Agent': 'skeptical',
        'Debate Agent': 'debate',
        'One Small Thing': 'one-small-thing',
        'Disruptor': 'disruptor'
    };
    
    // Return mapped class if available, otherwise convert from agent name
    return agentClassMap[agent] || agent.toLowerCase()
        .replace(/\s+/g, '-') // Replace spaces with hyphens
        .replace(/[^a-z0-9-]/g, ''); // Remove any non-alphanumeric characters except hyphens
}

// Initialize the app when the page loads
document.addEventListener('DOMContentLoaded', init);