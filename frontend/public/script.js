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
    "Product Agent": "sound-product",
    "Skeptical Agent": "sound-skeptical",
    "Debate Agent": "sound-debate",
    "One Small Thing": "sound-one-small-thing",
    "Disruptor": "sound-disruptor",
    "error": "sound-error"
    // Custom agents will use the "error" sound as default
};

// Agent icons
const agentIcons = {
    "Radical Expander": "fa-bolt",
    "Product Agent": "fa-lightbulb",
    "Skeptical Agent": "fa-question-circle",
    "Debate Agent": "fa-comments",
    "One Small Thing": "fa-check-circle",
    "Disruptor": "fa-rocket",
    "System": "fa-exclamation-circle"
    // Custom agents will default to "fa-brain" (assigned in the addInsightCard function)
};

// Predefined agent data for built-in agents
const builtInAgents = [
    {
        name: "Radical Expander",
        icon: "fa-bolt",
        type: "built-in",
        goal: "Radically expand conventional thinking by pushing ideas beyond their normal boundaries.",
        triggers: ["expand", "radical", "broader", "thinking", "innovation"],
        prompt: "Analyze the transcript and provide radical expansions on ideas mentioned, looking for unconventional connections and breakthrough possibilities."
    },
    {
        name: "Product Agent",
        icon: "fa-lightbulb",
        type: "built-in",
        goal: "Generate innovative product ideas based on needs or problems mentioned in conversation.",
        triggers: ["product", "solution", "feature", "service", "idea"],
        prompt: "Identify needs or problems in the transcript and generate creative product ideas that could address them in unique ways."
    },
    {
        name: "Skeptical Agent",
        icon: "fa-question-circle",
        type: "built-in",
        goal: "Critically examine ideas for potential flaws, risks, or unintended consequences.",
        triggers: ["critique", "skeptical", "devil's advocate", "what could go wrong"],
        prompt: "Analyze the transcript and identify potential problems, risks, or downsides to ideas being discussed."
    },
    {
        name: "Debate Agent",
        icon: "fa-comments",
        type: "built-in",
        goal: "Present multiple perspectives on a topic to facilitate more balanced thinking.",
        triggers: ["debate", "perspectives", "different views", "conflict"],
        prompt: "Analyze the transcript for points of disagreement or tension, then present balanced arguments from multiple perspectives."
    },
    {
        name: "One Small Thing",
        icon: "fa-check-circle",
        type: "built-in",
        goal: "Provide practical, actionable next steps that can be implemented immediately.",
        triggers: ["next steps", "how to start", "first step", "quick win"],
        prompt: "Analyze the transcript and suggest one small, concrete action that could be taken immediately to make progress."
    },
    {
        name: "Disruptor",
        icon: "fa-rocket",
        type: "built-in",
        goal: "Identify how emerging technologies could disrupt industries or business models mentioned.",
        triggers: ["disrupt", "industry change", "future", "technology impact"],
        prompt: "Analyze the transcript for mentions of industries or business practices that could be disrupted by AI, blockchain, or other emerging technologies."
    }
];

// Store for custom agents (will be populated during runtime)
let customAgents = [];

// Store for available LLM models
let availableModels = {
    "gemini": ["gemini-1.5-pro-002"],
    "claude": ["claude-3-7-sonnet-20250219"]
};

// Track active model
let activeModelProvider = "gemini";
let activeModelName = "gemini-1.5-pro-002";

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
    
    // Set up model selector
    setupModelSelector();
    
    // Agent Management
    setupAgentManagement();
}

// Set up model selector
function setupModelSelector() {
    const globalModelSelector = document.getElementById('global-model-selector');
    
    // Request available models from server after connection
    if (globalModelSelector) {
        // Set initial selection based on activeModelProvider and activeModelName
        updateModelSelectorUI();
        
        // Handle model selection changes
        globalModelSelector.addEventListener('change', function() {
            const selectedValue = this.value;
            const [provider, model] = selectedValue.split(':');
            
            if (provider && (provider === 'gemini' || provider === 'claude')) {
                // Send model change request to server
                if (socket && socket.readyState === WebSocket.OPEN) {
                    const message = {
                        type: 'set_model',
                        provider: provider,
                        model: model || ''
                    };
                    socket.send(JSON.stringify(message));
                    
                    // Update local tracking variables
                    activeModelProvider = provider;
                    activeModelName = model;
                    
                    // Show feedback
                    showToast(`Switching to ${provider} model: ${model || 'default'}`);
                }
            }
        });
    }
}

// Request available models from server
function requestAvailableModels() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        const message = {
            type: 'get_available_models'
        };
        socket.send(JSON.stringify(message));
    }
}

// Update model selector UI with available models
function updateModelSelectorUI() {
    const globalModelSelector = document.getElementById('global-model-selector');
    const agentModelSelector = document.getElementById('edit-agent-model');
    
    if (globalModelSelector) {
        // Clear existing options
        globalModelSelector.innerHTML = '';
        
        // Add options for each provider and model
        for (const [provider, models] of Object.entries(availableModels)) {
            const providerName = provider === 'gemini' ? 'Gemini' : 'Claude';
            
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = `${provider}:${model}`;
                
                // Create a shorter, more readable name for the model
                let displayName = model;
                if (model.includes('gemini-1.5-pro')) {
                    displayName = 'Gemini 1.5 Pro';
                } else if (model.includes('gemini-1.5-flash')) {
                    displayName = 'Gemini 1.5 Flash';
                } else if (model.includes('claude-3-7-sonnet')) {
                    displayName = 'Claude 3.7 Sonnet';
                } else if (model.includes('claude-3-5-sonnet')) {
                    displayName = 'Claude 3.5 Sonnet';
                } else if (model.includes('claude-3-opus')) {
                    displayName = 'Claude 3 Opus';
                }
                
                option.textContent = `${providerName}: ${displayName}`;
                
                // Set as selected if it matches the active model
                if (provider === activeModelProvider && model === activeModelName) {
                    option.selected = true;
                }
                
                globalModelSelector.appendChild(option);
            });
        }
    }
    
    // Also update the agent-specific model selector if it exists
    if (agentModelSelector) {
        // Keep the first "System Default" option
        const defaultOption = agentModelSelector.options[0];
        agentModelSelector.innerHTML = '';
        agentModelSelector.appendChild(defaultOption);
        
        // Add options for each provider and model
        for (const [provider, models] of Object.entries(availableModels)) {
            const providerName = provider === 'gemini' ? 'Gemini' : 'Claude';
            
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = `${provider}:${model}`;
                
                // Create a shorter, more readable name for the model
                let displayName = model;
                if (model.includes('gemini-1.5-pro')) {
                    displayName = 'Gemini 1.5 Pro';
                } else if (model.includes('gemini-1.5-flash')) {
                    displayName = 'Gemini 1.5 Flash';
                } else if (model.includes('claude-3-7-sonnet')) {
                    displayName = 'Claude 3.7 Sonnet';
                } else if (model.includes('claude-3-5-sonnet')) {
                    displayName = 'Claude 3.5 Sonnet';
                } else if (model.includes('claude-3-opus')) {
                    displayName = 'Claude 3 Opus';
                }
                
                option.textContent = `${providerName}: ${displayName}`;
                agentModelSelector.appendChild(option);
            });
        }
    }
}

// Setup Agent Management UI and Event Handlers
function setupAgentManagement() {
    const manageAgentsBtn = document.getElementById('manage-agents-btn');
    const modal = document.getElementById('manage-agents-modal');
    const modalCloseBtn = modal.querySelector('.modal-close');
    const agentList = document.getElementById('agent-list');
    const newAgentBtn = document.getElementById('new-agent-btn');
    const editAgentBtn = document.getElementById('edit-agent-btn');
    const deleteAgentBtn = document.getElementById('delete-agent-btn');
    const cancelEditBtn = document.querySelector('.cancel-edit-btn');
    const agentEditForm = document.getElementById('agent-edit-form');
    
    // Current selected agent
    let selectedAgentId = null;
    let isEditingNewAgent = false;
    
    // Open modal
    if (manageAgentsBtn) {
        manageAgentsBtn.addEventListener('click', () => {
            populateAgentList();
            modal.classList.add('show');
        });
    }
    
    // Close modal (X button)
    if (modalCloseBtn) {
        modalCloseBtn.addEventListener('click', () => {
            modal.classList.remove('show');
            resetAgentEditor();
        });
    }
    
    // Create New Agent button
    if (newAgentBtn) {
        newAgentBtn.addEventListener('click', () => {
            isEditingNewAgent = true;
            selectedAgentId = null;
            
            // Update form title
            document.getElementById('editor-title').textContent = 'Create New Agent';
            
            // Reset form values
            document.getElementById('edit-agent-name').value = '';
            document.getElementById('edit-agent-icon').value = 'fa-brain';
            document.getElementById('edit-agent-goal').value = '';
            document.getElementById('edit-agent-prompt').value = 'You are {name}, a specialized AI agent focused on: {goal}\n\nAnalyze the following transcript and provide insights related to your specialty.\n\nTRANSCRIPT:\n"{text}"\n\nProvide a detailed analysis and actionable recommendations.';
            document.getElementById('edit-agent-triggers').value = '';
            
            // Show editor, hide details
            document.getElementById('agent-editor').classList.add('active');
            document.getElementById('agent-details').classList.add('hidden');
            
            // Remove active class from any selected agent in list
            const activeItems = agentList.querySelectorAll('.agent-list-item.active');
            activeItems.forEach(item => item.classList.remove('active'));
        });
    }
    
    // Edit button
    if (editAgentBtn) {
        editAgentBtn.addEventListener('click', () => {
            if (!selectedAgentId) return;
            
            const agent = findAgentById(selectedAgentId);
            if (!agent) return;
            
            isEditingNewAgent = false;
            
            // Update form title
            document.getElementById('editor-title').textContent = 'Edit Agent';
            
            // Populate form with agent data
            document.getElementById('edit-agent-name').value = agent.name;
            document.getElementById('edit-agent-icon').value = agent.icon || 'fa-brain';
            document.getElementById('edit-agent-goal').value = agent.goal;
            document.getElementById('edit-agent-prompt').value = agent.prompt || 'You are {name}, a specialized AI agent focused on: {goal}\n\nAnalyze the following transcript and provide insights related to your specialty.\n\nTRANSCRIPT:\n"{text}"\n\nProvide a detailed analysis and actionable recommendations.';
            document.getElementById('edit-agent-triggers').value = agent.triggers.join(', ');
            
            // Set model preference if specified
            const modelSelector = document.getElementById('edit-agent-model');
            if (modelSelector) {
                if (agent.model) {
                    modelSelector.value = agent.model;
                } else {
                    modelSelector.value = ''; // System default
                }
            }
            
            // Show editor, hide details
            document.getElementById('agent-editor').classList.add('active');
            document.getElementById('agent-details').classList.add('hidden');
        });
    }
    
    // Delete button
    if (deleteAgentBtn) {
        deleteAgentBtn.addEventListener('click', () => {
            if (!selectedAgentId) return;
            
            const agent = findAgentById(selectedAgentId);
            if (!agent) return;
            
            // Check if it's a built-in agent
            if (agent.type === 'built-in') {
                showToast('Cannot delete built-in agents');
                return;
            }
            
            // Confirm deletion
            if (confirm(`Are you sure you want to delete the agent "${agent.name}"?`)) {
                // Remove from customAgents array
                const index = customAgents.findIndex(a => a.name === agent.name);
                if (index !== -1) {
                    customAgents.splice(index, 1);
                }
                
                // Send delete command to server
                if (socket && socket.readyState === WebSocket.OPEN) {
                    const message = {
                        type: 'delete_agent',
                        name: agent.name
                    };
                    socket.send(JSON.stringify(message));
                }
                
                // Show toast
                showToast(`Agent "${agent.name}" deleted`);
                
                // Reset selected agent
                selectedAgentId = null;
                
                // Hide details view
                document.getElementById('agent-details').classList.add('hidden');
                
                // Refresh agent list
                populateAgentList();
            }
        });
    }
    
    // Cancel Edit button
    if (cancelEditBtn) {
        cancelEditBtn.addEventListener('click', () => {
            resetAgentEditor();
        });
    }
    
    // Submit Edit form
    if (agentEditForm) {
        agentEditForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            // Get form values
            const agentName = document.getElementById('edit-agent-name').value.trim();
            const agentIcon = document.getElementById('edit-agent-icon').value;
            const agentGoal = document.getElementById('edit-agent-goal').value.trim();
            const agentPrompt = document.getElementById('edit-agent-prompt').value.trim();
            const agentModel = document.getElementById('edit-agent-model').value;
            const triggerKeywords = document.getElementById('edit-agent-triggers').value
                .split(',')
                .map(word => word.trim())
                .filter(word => word.length > 0);
            
            // Validate input
            if (!agentName || !agentGoal || triggerKeywords.length === 0) {
                showToast('Please fill in all required fields');
                return;
            }
            
            // Create agent configuration
            const agentConfig = {
                name: agentName,
                icon: agentIcon,
                type: 'custom',
                goal: agentGoal,
                prompt: agentPrompt,
                triggers: triggerKeywords
            };
            
            // Add model preference if specified
            if (agentModel) {
                agentConfig.model = agentModel;
            }
            
            if (isEditingNewAgent) {
                // Create new agent
                createCustomAgent(agentConfig);
            } else {
                // Update existing agent
                updateCustomAgent(selectedAgentId, agentConfig);
            }
            
            // Reset editor
            resetAgentEditor();
            
            // Refresh agent list
            populateAgentList();
        });
    }
    
    // Function to find agent by ID (name for now)
    function findAgentById(id) {
        // Check built-in agents
        const builtInAgent = builtInAgents.find(agent => agent.name === id);
        if (builtInAgent) return builtInAgent;
        
        // Check custom agents
        const customAgent = customAgents.find(agent => agent.name === id);
        if (customAgent) return customAgent;
        
        return null;
    }
    
    // Function to reset agent editor state
    function resetAgentEditor() {
        document.getElementById('agent-editor').classList.remove('active');
        
        // If an agent is selected, show its details
        if (selectedAgentId) {
            document.getElementById('agent-details').classList.remove('hidden');
        } else {
            document.getElementById('agent-details').classList.add('hidden');
        }
        
        // Reset form
        agentEditForm.reset();
    }
    
    // Function to populate agent list
    function populateAgentList() {
        // Clear existing list
        agentList.innerHTML = '';
        
        // Add built-in agents
        builtInAgents.forEach(agent => {
            const agentItem = createAgentListItem(agent);
            agentList.appendChild(agentItem);
        });
        
        // Add custom agents
        customAgents.forEach(agent => {
            const agentItem = createAgentListItem(agent);
            agentList.appendChild(agentItem);
        });
        
        // If a agent was previously selected, re-select it
        if (selectedAgentId) {
            const selectedItem = agentList.querySelector(`[data-agent-id="${selectedAgentId}"]`);
            if (selectedItem) {
                selectedItem.classList.add('active');
            }
        }
    }
    
    // Function to create agent list item
    function createAgentListItem(agent) {
        const item = document.createElement('div');
        item.className = 'agent-list-item';
        item.dataset.agentId = agent.name;
        
        // Add active class if this is the selected agent
        if (agent.name === selectedAgentId) {
            item.classList.add('active');
        }
        
        const icon = document.createElement('div');
        icon.className = 'agent-list-icon';
        
        const iconEl = document.createElement('i');
        iconEl.className = `fas ${agent.icon || 'fa-brain'}`;
        icon.appendChild(iconEl);
        
        const details = document.createElement('div');
        details.className = 'agent-list-details';
        
        const name = document.createElement('div');
        name.className = 'agent-list-name';
        name.textContent = agent.name;
        
        const type = document.createElement('div');
        type.className = 'agent-list-type';
        type.textContent = agent.type || 'custom';
        
        details.appendChild(name);
        details.appendChild(type);
        
        item.appendChild(icon);
        item.appendChild(details);
        
        // Add click event
        item.addEventListener('click', () => {
            // Update selected agent
            selectedAgentId = agent.name;
            
            // Update active class
            const activeItems = agentList.querySelectorAll('.agent-list-item.active');
            activeItems.forEach(activeItem => activeItem.classList.remove('active'));
            item.classList.add('active');
            
            // Hide editor if visible
            document.getElementById('agent-editor').classList.remove('active');
            
            // Update details view
            document.getElementById('detail-agent-icon').className = `fas ${agent.icon || 'fa-brain'}`;
            document.getElementById('detail-agent-name').textContent = agent.name;
            document.getElementById('detail-agent-goal').textContent = agent.goal;
            
            // Update trigger tags
            const triggerTags = document.getElementById('detail-agent-triggers');
            triggerTags.innerHTML = '';
            
            agent.triggers.forEach(trigger => {
                const tagSpan = document.createElement('span');
                tagSpan.className = 'trigger-tag';
                tagSpan.textContent = trigger;
                triggerTags.appendChild(tagSpan);
            });
            
            // Update model information
            const modelInfoElement = document.getElementById('detail-agent-model');
            if (modelInfoElement) {
                if (agent.model) {
                    const [provider, model] = agent.model.split(':');
                    const providerName = provider === 'gemini' ? 'Gemini' : 'Claude';
                    
                    // Format the model name nicely
                    let displayName = model;
                    if (model.includes('gemini-1.5-pro')) {
                        displayName = 'Gemini 1.5 Pro';
                    } else if (model.includes('gemini-1.5-flash')) {
                        displayName = 'Gemini 1.5 Flash';
                    } else if (model.includes('claude-3-7-sonnet')) {
                        displayName = 'Claude 3.7 Sonnet';
                    } else if (model.includes('claude-3-5-sonnet')) {
                        displayName = 'Claude 3.5 Sonnet';
                    } else if (model.includes('claude-3-opus')) {
                        displayName = 'Claude 3 Opus';
                    }
                    
                    modelInfoElement.textContent = `${providerName}: ${displayName}`;
                } else {
                    modelInfoElement.textContent = 'System Default';
                }
            }
            
            // Update prompt template
            document.getElementById('detail-agent-prompt').textContent = agent.prompt || 'Default prompt template (not specified)';
            
            // Show details
            document.getElementById('agent-details').classList.remove('hidden');
            
            // Disable delete button for built-in agents
            if (agent.type === 'built-in') {
                deleteAgentBtn.disabled = true;
                deleteAgentBtn.title = 'Cannot delete built-in agents';
            } else {
                deleteAgentBtn.disabled = false;
                deleteAgentBtn.title = 'Delete this agent';
            }
        });
        
        return item;
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
        
        // Request available models from the server
        requestAvailableModels();
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
        // Check if the content appears to be an error or "not enough context" message
        // This is a second safety check in case backend still sends these through
        const content = messageData.content || "";
        const lowerContent = content.toLowerCase();
        
        // Filter out various error messages or non-relevant content
        if (lowerContent.includes("insufficient context") || 
            lowerContent.includes("no business context") || 
            lowerContent.includes("not enough context") ||
            lowerContent.includes("no context") ||
            lowerContent.includes("doesn't contain") ||
            lowerContent.includes("does not contain") ||
            lowerContent.includes("doesn't provide") ||
            lowerContent.includes("does not provide") ||
            content.includes("NO_BUSINESS_CONTEXT")) {
            // Silently ignore these messages
            console.log(`Filtering out insufficient context message from ${messageData.agent}`);
            return;
        }
        
        // Also filter out messages that are too short to be meaningful
        if (content.length < 50) {
            console.log(`Filtering out too-short message from ${messageData.agent}: "${content}"`);
            return;
        }
        
        // Check if the content appears to be bland or generic
        if (lowerContent.includes("i apologize") || 
            lowerContent.includes("i'm sorry") || 
            lowerContent.includes("i am sorry") ||
            lowerContent.includes("unable to generate")) {
            console.log(`Filtering out apologetic or generic message from ${messageData.agent}`);
            return;
        }
        
        // Process valid insight
        addInsightCard(messageData);
        playSound(messageData.agent);
    } 
    else if (messageData.type === "error") {
        // Silently ignore error messages - don't show cards for errors
        console.error(`Error from ${messageData.agent}: ${messageData.message || "Unknown error"}`);
        // Don't show a card and don't play a sound
    }
    else if (messageData.type === "silent_error") {
        // Log the error in console but don't display it to the user
        console.error(`Silent error from ${messageData.agent}: ${messageData.message}`);
        // Don't show a card and don't play a sound
    }
    else if (messageData.type === "transcript" && messageData.is_final) {
        // Transcript handling can be re-enabled if needed
        return;
    }
    else if (messageData.type === "system_message") {
        // Handle system messages (like agent creation confirmation)
        showToast(messageData.message);
        return;
    }
    else if (messageData.type === "available_models") {
        // Handle available models data
        console.log("Received available models:", messageData.data);
        
        // Update available models
        if (messageData.data && messageData.data.models) {
            availableModels = messageData.data.models;
            
            // Update active model tracking
            if (messageData.data.active_provider) {
                activeModelProvider = messageData.data.active_provider;
            }
            
            if (messageData.data.active_model) {
                activeModelName = messageData.data.active_model;
            }
            
            // Update UI with new model data
            updateModelSelectorUI();
            
            console.log(`Active model set to: ${activeModelProvider}:${activeModelName}`);
        }
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
    // Check if this is a custom agent (not in our predefined list)
    const isCustomAgent = !Object.keys(agentIcons).includes(agent);
    // Apply custom styling for custom agents
    card.className = isCustomAgent 
        ? `insight-card agent-custom` 
        : `insight-card agent-${convertAgentClassname(agent)}`;
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
    // Use brain icon for custom agents, robot as fallback for any others
    iconEl.className = `fas ${isCustomAgent ? 'fa-brain' : (agentIcons[agent] || 'fa-robot')}`;
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
    
    // Clean up agent name repetition in content
    let cleanContent = content;
    // Remove agent name prefix if it exists
    const agentPrefix = agent + ":";
    if (cleanContent.startsWith(agentPrefix)) {
        cleanContent = cleanContent.substring(agentPrefix.length).trim();
    }
    // Remove "Wild Product Idea:" prefix if it exists (special case for Product Agent)
    if (agent === "Product Agent" && cleanContent.startsWith("Wild Product Idea:")) {
        cleanContent = cleanContent.substring("Wild Product Idea:".length).trim();
    }
    
    // Generate headline and summary from cleaned content
    const headline = generateHeadline(cleanContent);
    const summary = generateSummary(cleanContent);
    
    // Create headline
    const cardHeadline = document.createElement('h2');
    cardHeadline.className = 'card-headline';
    cardHeadline.textContent = headline;
    
    // Create summary
    const cardSummary = document.createElement('div');
    cardSummary.className = 'card-summary';
    cardSummary.textContent = summary;
    
    // Create content container div to hold the full detailed analysis text
    const contentContainer = document.createElement('div');
    contentContainer.className = 'detail-content';
    contentContainer.style.display = 'none';
    
    // Process and extract just the detailed analysis part
    let detailContent = extractDetailedContent(cleanContent, headline, summary);
    contentContainer.innerHTML = detailContent;
    
    // Add read more button
    const readMoreBtn = document.createElement('button');
    readMoreBtn.className = 'read-more-btn';
    readMoreBtn.textContent = 'Read More';
    readMoreBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (contentContainer.style.display === 'none') {
            contentContainer.style.display = 'block';
            readMoreBtn.textContent = 'Read Less';
        } else {
            contentContainer.style.display = 'none';
            readMoreBtn.textContent = 'Read More';
        }
    });
    
    // Create content wrapper
    const contentWrapper = document.createElement('div');
    contentWrapper.className = 'card-content-wrapper';
    contentWrapper.appendChild(cardHeadline);
    contentWrapper.appendChild(cardSummary);
    contentWrapper.appendChild(contentContainer);
    contentWrapper.appendChild(readMoreBtn);
    
    // Assemble card
    card.appendChild(cardHeader);
    card.appendChild(contentWrapper);
    
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

// Generate a headline from content
function generateHeadline(content) {
    if (!content) return 'Insight';
    
    // Remove HTML tags if any
    const plainText = content.replace(/<[^>]*>/g, '');
    
    // Check if the content has a standardized format with a headline on the first line
    const lines = plainText.split('\n');
    if (lines.length > 2 && lines[0].trim() && lines[1].trim() === '') {
        // If the first line is non-empty and followed by an empty line, use it as headline
        let headline = lines[0].trim();
        
        // Capitalize first letter
        if (headline.length > 0) {
            headline = headline.charAt(0).toUpperCase() + headline.slice(1);
        }
        
        return headline;
    }
    
    // Get first sentence or first 100 characters
    let headline = '';
    
    // First try to get the first part until a colon or period
    const colonMatch = plainText.match(/^([^:]+):/);
    if (colonMatch) {
        headline = colonMatch[1].trim();
    } else {
        const firstSentenceMatch = plainText.match(/^([^.!?]+[.!?])/);
        if (firstSentenceMatch) {
            headline = firstSentenceMatch[1].trim();
        } else {
            headline = plainText.substring(0, 100).trim();
        }
    }
    
    // No longer truncating headlines at all
    // Just use the full headline as-is
    
    // Capitalize first letter
    if (headline.length > 0) {
        headline = headline.charAt(0).toUpperCase() + headline.slice(1);
    }
    
    return headline;
}

// Generate a summary from content
function generateSummary(content) {
    if (!content) return '';
    
    // Remove HTML tags if any
    const plainText = content.replace(/<[^>]*>/g, '');
    
    // Skip the headline part if there's a colon
    let textToSummarize = plainText;
    const colonIndex = plainText.indexOf(':');
    if (colonIndex > 0 && colonIndex < 50) {
        textToSummarize = plainText.substring(colonIndex + 1).trim();
    }
    
    // Get first sentence and second sentence if it's short
    const sentences = textToSummarize.split(/(?<=[.!?])\s+/);
    let summary = '';
    
    if (sentences.length >= 1) {
        summary = sentences[0].trim();
        
        // Add second sentence if the first one is very short
        if (sentences.length >= 2 && summary.length < 60) {
            summary += ' ' + sentences[1].trim();
        }
    }
    
    // Fallback to character-based truncation if needed
    if (!summary) {
        summary = textToSummarize.substring(0, 140).trim();
        if (textToSummarize.length > 140) summary += '...';
    }
    
    // Ensure it's not too long
    if (summary.length > 160) {
        summary = summary.substring(0, 157) + '...';
    }
    
    return summary;
}

// Format content with line breaks and styling
function formatContent(content) {
    if (!content) return '';
    
    // Replace newlines with <br> but not double newlines (paragraphs)
    let formatted = content.replace(/\n(?!\n)/g, '<br>');
    
    // Replace double newlines with paragraph breaks for better readability
    formatted = formatted.replace(/\n\n/g, '</p><p>');
    
    // Make bold text wrapped in ** or __ 
    formatted = formatted.replace(/(\*\*|__)(.*?)\1/g, '<strong>$2</strong>');
    
    // Make bullet points more visually appealing
    formatted = formatted.replace(/^•\s+(.*)/gm, '<div class="bullet-point">• $1</div>');
    
    // Wrap the content in <p> tags for proper spacing
    formatted = '<p>' + formatted + '</p>';
    
    return formatted;
}

// Extract just the detailed content after headline and summary
function extractDetailedContent(fullContent, headline, summary) {
    if (!fullContent) return '';
    
    // Convert to plain text for processing
    let plainText = fullContent.replace(/<[^>]*>/g, '');
    
    // Skip headline if present at the start
    if (headline && plainText.startsWith(headline)) {
        plainText = plainText.substring(headline.length).trim();
        // Skip any empty lines after headline
        plainText = plainText.replace(/^\s*\n+/, '');
    }
    
    // Skip summary if present after headline
    if (summary && plainText.startsWith(summary)) {
        plainText = plainText.substring(summary.length).trim();
        // Skip any empty lines after summary
        plainText = plainText.replace(/^\s*\n+/, '');
    }
    
    // Look for "Detailed Analysis:" section
    const detailStart = plainText.indexOf("Detailed Analysis:");
    if (detailStart >= 0) {
        plainText = plainText.substring(detailStart + "Detailed Analysis:".length).trim();
    }
    
    // Format the remaining content
    return formatContent(plainText);
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
        
        // Generate a headline for the saved card
        const plainContent = insight.content.replace(/<[^>]*>/g, '');
        const headline = generateHeadline(plainContent);
        
        const headlineElem = document.createElement('div');
        headlineElem.className = 'saved-card-headline';
        headlineElem.textContent = headline;
        
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
        card.appendChild(headlineElem);
        card.appendChild(removeBtn);
        
        // Make the card expandable to see full content
        card.addEventListener('click', () => expandSavedInsight(insight));
        
        savedInsightsDiv.appendChild(card);
    });
}

// Expand a saved insight to show full content
function expandSavedInsight(insight) {
    // Create a modal to show the full content
    const modal = document.createElement('div');
    modal.className = 'insight-modal';
    
    const modalContent = document.createElement('div');
    modalContent.className = `modal-content agent-${convertAgentClassname(insight.agent)}`;
    
    const modalHeader = document.createElement('div');
    modalHeader.className = 'modal-header';
    
    const agentInfo = document.createElement('div');
    agentInfo.className = 'agent-info';
    
    const agentIcon = document.createElement('div');
    agentIcon.className = 'agent-icon';
    const iconEl = document.createElement('i');
    iconEl.className = `fas ${agentIcons[insight.agent] || 'fa-robot'}`;
    agentIcon.appendChild(iconEl);
    
    const agentName = document.createElement('div');
    agentName.className = 'agent-name';
    agentName.textContent = insight.agent;
    
    agentInfo.appendChild(agentIcon);
    agentInfo.appendChild(agentName);
    
    const closeBtn = document.createElement('button');
    closeBtn.className = 'modal-close';
    closeBtn.innerHTML = '&times;';
    closeBtn.addEventListener('click', () => modal.remove());
    
    modalHeader.appendChild(agentInfo);
    modalHeader.appendChild(closeBtn);
    
    // Generate headline and summary
    const plainContent = insight.content.replace(/<[^>]*>/g, '');
    const headline = generateHeadline(plainContent);
    const summary = generateSummary(plainContent);
    
    const modalHeadline = document.createElement('h2');
    modalHeadline.className = 'modal-headline';
    modalHeadline.textContent = headline;
    
    const modalSummary = document.createElement('div');
    modalSummary.className = 'modal-summary';
    modalSummary.textContent = summary;
    
    const modalFullContent = document.createElement('div');
    modalFullContent.className = 'modal-full-content';
    modalFullContent.innerHTML = formatContent(insight.content);
    
    modalContent.appendChild(modalHeader);
    modalContent.appendChild(modalHeadline);
    modalContent.appendChild(modalSummary);
    modalContent.appendChild(modalFullContent);
    
    modal.appendChild(modalContent);
    
    // Close when clicking outside the modal content
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
    
    document.body.appendChild(modal);
    
    // Add some simple modal styling if not already in CSS
    if (!document.querySelector('style#modal-styles')) {
        const style = document.createElement('style');
        style.id = 'modal-styles';
        style.textContent = `
            .insight-modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 1000;
            }
            .modal-content {
                background-color: white;
                padding: 0;
                border-radius: 8px;
                width: 80%;
                max-width: 600px;
                max-height: 90vh;
                overflow-y: auto;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
            }
            .modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 1rem 1.5rem;
                border-bottom: 1px solid rgba(0, 0, 0, 0.1);
            }
            .modal-close {
                background: none;
                border: none;
                font-size: 1.5rem;
                cursor: pointer;
                color: #666;
            }
            .modal-headline {
                font-size: 1.8rem;
                padding: 1.5rem 1.5rem 0.5rem;
                margin: 0;
            }
            .modal-summary {
                padding: 0 1.5rem 1.5rem;
                color: #555;
                font-size: 1.1rem;
                border-bottom: 1px solid rgba(0, 0, 0, 0.05);
            }
            .modal-full-content {
                padding: 1.5rem;
                font-size: 1rem;
                line-height: 1.6;
            }
        `;
        document.head.appendChild(style);
    }
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
    
    // Create headline
    const cardHeadline = document.createElement('h2');
    cardHeadline.className = 'card-headline';
    cardHeadline.textContent = "Error Occurred";
    
    // Create error message
    const cardSummary = document.createElement('div');
    cardSummary.className = 'card-summary';
    cardSummary.textContent = message;
    
    // Create content wrapper
    const contentWrapper = document.createElement('div');
    contentWrapper.className = 'card-content-wrapper';
    contentWrapper.appendChild(cardHeadline);
    contentWrapper.appendChild(cardSummary);
    
    card.appendChild(cardHeader);
    card.appendChild(contentWrapper);
    
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
        'Product Agent': 'product',
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

// Create Custom Agent
function createCustomAgent(agentConfig) {
    // Validate connection
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        showToast('Cannot create agent: Not connected to server');
        return;
    }
    
    // Create message
    const message = {
        type: 'create_agent',
        config: agentConfig
    };
    
    // Send to server
    socket.send(JSON.stringify(message));
    
    // Add to local custom agents array
    customAgents.push(agentConfig);
    
    // Show success message
    showToast(`Created custom agent: ${agentConfig.name}`);
    
    // Add a custom filter button for this agent if it doesn't exist
    addCustomAgentFilter(agentConfig.name);
}

// Update Custom Agent
function updateCustomAgent(oldName, agentConfig) {
    // Validate connection
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        showToast('Cannot update agent: Not connected to server');
        return;
    }
    
    // Check if name changed
    const nameChanged = oldName !== agentConfig.name;
    
    // Create message
    const message = {
        type: 'update_agent',
        old_name: oldName,
        config: agentConfig
    };
    
    // Send to server
    socket.send(JSON.stringify(message));
    
    // Update in local customAgents array
    const index = customAgents.findIndex(agent => agent.name === oldName);
    if (index !== -1) {
        customAgents[index] = agentConfig;
    }
    
    // Show success message
    showToast(`Updated agent: ${agentConfig.name}`);
    
    // If name changed, update filter button or add a new one
    if (nameChanged) {
        // Remove old filter button if it exists
        const oldFilterBtn = Array.from(filterButtons).find(btn => btn.dataset.filter === oldName);
        if (oldFilterBtn) {
            oldFilterBtn.remove();
        }
        
        // Add new filter button
        addCustomAgentFilter(agentConfig.name);
    }
}

// Add Custom Agent Filter Button
function addCustomAgentFilter(agentName) {
    // Check if filter already exists
    const existingFilter = Array.from(filterButtons).find(btn => btn.dataset.filter === agentName);
    if (existingFilter) return;
    
    // Get parent container
    const filterContainer = document.querySelector('.filter-controls');
    if (!filterContainer) return;
    
    // Create new button
    const newFilterBtn = document.createElement('button');
    newFilterBtn.className = 'filter-btn';
    newFilterBtn.dataset.filter = agentName;
    
    // Use a shortened name if needed
    if (agentName.length > 10) {
        // Get first word or first 8 characters
        const shortName = agentName.split(' ')[0] || agentName.substring(0, 8);
        newFilterBtn.textContent = shortName;
        // Add tooltip with full name
        newFilterBtn.title = agentName;
    } else {
        newFilterBtn.textContent = agentName;
    }
    
    // Add event listener
    newFilterBtn.addEventListener('click', () => {
        activeFilter = agentName;
        filterButtons.forEach(btn => btn.classList.remove('active'));
        newFilterBtn.classList.add('active');
        filterInsights();
    });
    
    // Add to container
    filterContainer.appendChild(newFilterBtn);
    
    // Update filterButtons NodeList
    filterButtons = document.querySelectorAll('.filter-btn');
}

// Initialize the app when the page loads
document.addEventListener('DOMContentLoaded', init);