# backend/main.py (Updated for Context Buffering)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
import logging
import os
import json
import asyncio
import collections # Import collections for deque

# Import Google Cloud libraries
from google.cloud import speech
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel

# Import unified LLM client
from llm_providers import llm_client, ModelProvider

# --- Configuration ---
logging.basicConfig(level=logging.INFO)
# Define logger with name "main" so other modules can get it
logger = logging.getLogger("main")

PROJECT_ID = "meetinganalyzer-454912" # Replace with your Project ID
LOCATION = "us-east1"
SPEECH_LANGUAGE_CODE = "en-US"
SPEECH_SAMPLE_RATE_HERTZ = 16000
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-pro-002")
CLAUDE_MODEL_NAME = os.getenv("CLAUDE_MODEL_NAME", "claude-3-7-sonnet-20250219")

# Rate limit for Traffic Cop calls
last_traffic_cop_call_time = 0.0
MIN_TRAFFIC_COP_INTERVAL = 10.0 # Set to 10 seconds - balance between triggering frequency and avoiding rate limits

# Context Buffer Configuration for Debate Agent
# Store approx 60 seconds. If segments are ~5-10s, 6-12 segments. Let's use 10.
CONTEXT_BUFFER_SIZE = 10

# --- Initialize Clients (Global within main) ---
speech_client = None
gemini_model = None  # Keep for backward compatibility

try:
    speech_client = speech.SpeechAsyncClient()
    logger.info("SpeechAsyncClient initialized successfully.")
except Exception as e:
    logger.error(f"Could not initialize Google Cloud SpeechAsyncClient: {e}")

# Check if we have available LLM providers
available_models = llm_client.available_models()
if available_models:
    model_info = []
    for provider, models in available_models.items():
        model_info.append(f"{provider}: {', '.join(models)}")
    logger.info(f"Available LLM models: {'; '.join(model_info)}")
    
    # Set default model based on environment or fallback to Claude if available
    default_provider = os.getenv("DEFAULT_LLM_PROVIDER", "claude").lower()
    OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "o3-mini")
    
    if default_provider == "claude" and ModelProvider.CLAUDE in available_models:
        llm_client.set_active_provider(ModelProvider.CLAUDE, CLAUDE_MODEL_NAME)
        logger.info(f"Using Claude as default provider with model {CLAUDE_MODEL_NAME}")
    elif default_provider == "gemini" and ModelProvider.GEMINI in available_models:
        llm_client.set_active_provider(ModelProvider.GEMINI, GEMINI_MODEL_NAME)
        logger.info(f"Using Gemini as default provider with model {GEMINI_MODEL_NAME}")
    elif default_provider == "openai" and ModelProvider.OPENAI in available_models:
        llm_client.set_active_provider(ModelProvider.OPENAI, OPENAI_MODEL_NAME)
        logger.info(f"Using OpenAI as default provider with model {OPENAI_MODEL_NAME}")
    elif not llm_client.active_provider:
        # If no specific default and none is active yet, prefer Claude > Gemini > OpenAI
        if ModelProvider.CLAUDE in available_models:
            llm_client.set_active_provider(ModelProvider.CLAUDE, CLAUDE_MODEL_NAME)
            logger.info(f"Defaulting to Claude with model {CLAUDE_MODEL_NAME}")
        elif ModelProvider.GEMINI in available_models:
            llm_client.set_active_provider(ModelProvider.GEMINI, GEMINI_MODEL_NAME)
            logger.info(f"Defaulting to Gemini with model {GEMINI_MODEL_NAME}")
        elif ModelProvider.OPENAI in available_models:
            llm_client.set_active_provider(ModelProvider.OPENAI, OPENAI_MODEL_NAME)
            logger.info(f"Defaulting to OpenAI with model {OPENAI_MODEL_NAME}")
        else:
            logger.warning("No LLM providers available. System functionality will be limited.")
else:
    logger.error("No LLM providers available. Please check your credentials and environment variables.")

# For backward compatibility, still set gemini_model
if llm_client.gemini_model:
    gemini_model = llm_client.gemini_model

# --- Import AI logic AFTER clients are potentially initialized ---
try:
    # Import the functions we need from traffic_cop.py
    from traffic_cop import route_to_traffic_cop, trigger_agent
    logger.info("Successfully imported from traffic_cop.py")
except ImportError as e:
    logger.error(f"Could not import from traffic_cop.py: {e}. Using dummy functions.")
    # Define dummy functions if import fails, to prevent crashes later
    async def route_to_traffic_cop(transcript_text: str, model): logger.error("route_to_traffic_cop failed to import"); return None
    async def trigger_agent(name: str, current_segment_text: str, model, broadcaster, context_buffer: str): logger.error("trigger_agent failed to import")


app = FastAPI()

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection: {websocket.client}")
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected: {websocket.client}")
    async def broadcast(self, message: str):
        logger.info(f"Broadcasting message: {message[:100]}...") # Log snippet
        # Create a task list for all send operations
        tasks = [connection.send_text(message) for connection in self.active_connections]
        # Wait for all tasks to complete, gathering results (including exceptions)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Handle disconnections based on results
        for connection, result in zip(list(self.active_connections), results):
            if isinstance(result, Exception):
                logger.error(f"Failed to send message to {connection.client}: {result}. Disconnecting.")
                # Ensure disconnect is safe if connection already removed elsewhere
                if connection in self.active_connections:
                     self.disconnect(connection)

manager = ConnectionManager()

# --- Broadcast Insight Function (Needed globally for agents) ---
async def broadcast_insight(insight_data: dict):
    """Helper function to broadcast insights via the manager."""
    try:
        # Add agent name to log for clarity
        agent_name = insight_data.get("agent", "Unknown Agent")
        logger.info(f"Broadcasting insight from {agent_name}...")
        message_str = json.dumps(insight_data)
        await manager.broadcast(message_str)
    except Exception as e:
        logger.error(f"Error broadcasting insight: {e}")


# --- Transcription Handling (Modified for Buffering) ---
async def handle_transcript_response(response_stream, websocket: WebSocket):
    """Handles responses from the Speech-to-Text API stream and triggers agents."""
    global last_traffic_cop_call_time
    # Initialize context buffer for this connection using deque
    transcript_buffer = collections.deque(maxlen=CONTEXT_BUFFER_SIZE)
    logger.info(f">>> handle_transcript_response: Started (Buffer size: {CONTEXT_BUFFER_SIZE})")

    try:
        async for response in response_stream:
            if not response.results: continue
            result = response.results[0]
            if not result.alternatives: continue

            transcript = result.alternatives[0].transcript

            if result.is_final:
                logger.info(f"Final Transcript: {transcript}")
                # Add the finalized transcript to the buffer
                transcript_buffer.append(transcript)

                # Skip empty transcripts before calling Traffic Cop
                if not transcript or len(transcript.strip()) < 2: # Very minimal check - almost any content will pass
                    logger.info("Transcript empty, skipping Traffic Cop call.")
                    continue

                current_time = asyncio.get_event_loop().time()
                time_since_last_call = current_time - last_traffic_cop_call_time

                if time_since_last_call >= MIN_TRAFFIC_COP_INTERVAL:
                    logger.info(f"Interval passed ({time_since_last_call:.1f}s >= {MIN_TRAFFIC_COP_INTERVAL}s). Calling Traffic Cop.")
                    last_traffic_cop_call_time = current_time

                    # Get the agent name from traffic cop (pass model)
                    # Route based on the *current* segment, but traffic cop might check keywords
                    agent_name = await route_to_traffic_cop(transcript, gemini_model)

                    # Only trigger agent if a valid one was returned and it's not "None"
                    if agent_name and agent_name != "None":
                        # Prepare the context buffer by joining recent segments
                        current_context_buffer = " ".join(list(transcript_buffer))
                        # Call trigger_agent, passing the CURRENT segment AND the context buffer
                        await trigger_agent(
                            name=agent_name,
                            current_segment_text=transcript, # Pass current segment
                            model=gemini_model,
                            broadcaster=broadcast_insight, # Pass the broadcast function
                            context_buffer=current_context_buffer # Pass joined buffer
                        )
                    elif agent_name == "None":
                        logger.info("Traffic Cop decided no agent is needed for this transcript.")
                    else: # Should mean route_to_traffic_cop returned None due to error
                        logger.warning("Traffic Cop returned no agent (likely due to an error), skipping trigger.")
                else:
                    logger.info(f"Skipping Traffic Cop call (interval not met: {time_since_last_call:.1f}s < {MIN_TRAFFIC_COP_INTERVAL}s).")
            else:
                # Log interim results less verbosely if desired
                # logger.debug(f"Interim Transcript: {transcript}")
                pass

    except asyncio.CancelledError:
        logger.info("Transcript response handler cancelled.")
    except Exception as e:
        logger.error(f"Error in transcript response handler: {e}")
        logger.exception("Traceback:")
    finally:
        logger.info("Transcript response handler finished.")


async def audio_request_generator(audio_queue: asyncio.Queue):
    """Generates requests for the Speech-to-Text API stream."""
    logger.info(">>> audio_request_generator: Started")
    # Use try-except for potential config errors
    try:
        streaming_config = speech.StreamingRecognitionConfig(
            config=speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=SPEECH_SAMPLE_RATE_HERTZ,
                language_code=SPEECH_LANGUAGE_CODE,
                enable_automatic_punctuation=True,
                # Add other config options if needed, e.g., model selection, adaptation
                # model="telephony", # Example
                # use_enhanced=True, # Example
            ),
            interim_results=True
        )
        yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)
        logger.info("Sent streaming config to Speech API.")
    except Exception as e:
        logger.error(f"Error creating streaming config: {e}")
        # Need to decide how to handle this - maybe close connection?
        # For now, just log and the generator might stop.
        return

    while True:
        try:
            # Use wait_for for timeout, prevents indefinite blocking
            audio_chunk = await asyncio.wait_for(audio_queue.get(), timeout=5.0)
            # Check for sentinel value (None) to signal end
            if audio_chunk is None:
                logger.info("Received None, stopping audio stream generation.")
                break
            yield speech.StreamingRecognizeRequest(audio_content=audio_chunk)
            audio_queue.task_done()
        except asyncio.TimeoutError:
            # No audio received in timeout window, continue listening
            continue
        except asyncio.CancelledError:
            logger.info("Audio request generator cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in audio request generator loop: {e}")
            # Depending on error, might want to break or continue
            break # Stop on error for now
    logger.info("Audio request generator finished.")


# --- WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handles WebSocket connections and audio streaming."""
    logger.info(">>> websocket_endpoint: Entered")
    await manager.connect(websocket)
    logger.info(">>> websocket_endpoint: Connection accepted by manager")

    audio_queue = asyncio.Queue()
    transcription_task = None
    response_stream = None # Initialize here for finally block

    try:
        # Log client status on connection for debugging
        logger.info(f"Speech client ready: {bool(speech_client)}")
        logger.info(f"Gemini model ready: {bool(gemini_model)}")

        # Critical check: Ensure backend clients are ready before proceeding
        if not speech_client or not gemini_model:
            logger.error("Backend clients (Speech or Gemini) not ready during connection.")
            await websocket.send_text(json.dumps({"type": "error", "message": "Backend AI/Speech services not ready. Please try again later."}))
            # Use code 1011 for internal server error
            await websocket.close(code=1011)
            manager.disconnect(websocket) # Ensure disconnect from manager
            return

        logger.info(">>> websocket_endpoint: Creating audio request generator")
        request_generator = audio_request_generator(audio_queue)

        logger.info(">>> websocket_endpoint: Starting streaming_recognize")
        # Make the API call
        response_stream = await speech_client.streaming_recognize(requests=request_generator)
        logger.info(">>> websocket_endpoint: streaming_recognize call returned, stream active.")

        logger.info(">>> websocket_endpoint: Creating transcription task")
        # Pass websocket only if handle_transcript_response needs it directly
        transcription_task = asyncio.create_task(handle_transcript_response(response_stream, websocket))
        logger.info(">>> websocket_endpoint: Transcription task created")

        # --- Receive Audio Loop ---
        while True:
            # Handle both binary audio data and text messages
            try:
                # Try to receive as bytes first (audio data)
                audio_data = await websocket.receive_bytes()
                # Handle potential empty messages if necessary
                if not audio_data:
                    # logger.debug("Received empty audio data packet.")
                    continue
                await audio_queue.put(audio_data)
            except WebSocketDisconnect:
                # WebSocket disconnected
                raise
            except Exception as e:
                # This could be a text message - try to receive as text
                try:
                    message_data = await websocket.receive_text()
                    logger.info(f"Received text message: {message_data[:100]}...")
                    
                    # Parse the message
                    try:
                        message_json = json.loads(message_data)
                        message_type = message_json.get("type")
                        
                        # Handle create_agent message
                        if message_type == "create_agent":
                            config = message_json.get("config", {})
                            agent_name = config.get("name", "Custom Agent")
                            agent_goal = config.get("goal", "")
                            agent_prompt = config.get("prompt", "")
                            agent_icon = config.get("icon", "fa-brain")
                            agent_triggers = config.get("triggers", [])
                            agent_model = config.get("model", "")  # Optional model specification
                            
                            logger.info(f"Creating custom agent: {agent_name}")
                            
                            # Add agent to CUSTOM_AGENTS list in traffic_cop
                            from traffic_cop import CUSTOM_AGENTS
                            
                            # Create agent config
                            agent_config = {
                                "name": agent_name,
                                "goal": agent_goal,
                                "prompt": agent_prompt,
                                "icon": agent_icon,
                                "type": "custom",
                                "triggers": agent_triggers
                            }
                            
                            # Add model preference if specified
                            if agent_model:
                                agent_config["model"] = agent_model
                                logger.info(f"Agent '{agent_name}' will use model: {agent_model}")
                            
                            # Add to global list and persist to disk
                            CUSTOM_AGENTS.append(agent_config)
                            
                            # Save to file
                            from traffic_cop import save_custom_agents
                            save_custom_agents()
                            
                            # Send confirmation
                            await websocket.send_text(json.dumps({
                                "type": "system_message",
                                "message": f"Custom agent '{agent_name}' created successfully"
                            }))
                            
                            logger.info(f"Custom agent created: {agent_name} with {len(agent_triggers)} triggers")
                            
                        elif message_type == "update_agent":
                            old_name = message_json.get("old_name", "")
                            config = message_json.get("config", {})
                            agent_name = config.get("name", "Custom Agent")
                            agent_goal = config.get("goal", "")
                            agent_prompt = config.get("prompt", "")
                            agent_icon = config.get("icon", "fa-brain")
                            agent_triggers = config.get("triggers", [])
                            agent_model = config.get("model", "")  # Optional model specification
                            
                            logger.info(f"Updating custom agent: {old_name} -> {agent_name}")
                            
                            # Add agent to CUSTOM_AGENTS list in traffic_cop
                            from traffic_cop import CUSTOM_AGENTS
                            
                            # Find the agent by name
                            agent_index = -1
                            for i, agent in enumerate(CUSTOM_AGENTS):
                                if agent.get("name") == old_name:
                                    agent_index = i
                                    break
                            
                            if agent_index >= 0:
                                # Create updated agent config
                                agent_config = {
                                    "name": agent_name,
                                    "goal": agent_goal,
                                    "prompt": agent_prompt,
                                    "icon": agent_icon,
                                    "type": "custom",
                                    "triggers": agent_triggers
                                }
                                
                                # Add model preference if specified
                                if agent_model:
                                    agent_config["model"] = agent_model
                                    logger.info(f"Agent '{agent_name}' will use model: {agent_model}")
                                
                                # Update in the list
                                CUSTOM_AGENTS[agent_index] = agent_config
                                
                                # Save to file
                                from traffic_cop import save_custom_agents
                                save_custom_agents()
                                
                                # Send confirmation
                                await websocket.send_text(json.dumps({
                                    "type": "system_message",
                                    "message": f"Custom agent updated: {old_name} -> {agent_name}"
                                }))
                                
                                logger.info(f"Custom agent updated: {old_name} -> {agent_name}")
                            else:
                                # Agent not found
                                await websocket.send_text(json.dumps({
                                    "type": "system_message",
                                    "message": f"Error: Agent '{old_name}' not found"
                                }))
                                
                                logger.warning(f"Failed to update agent: {old_name} not found")
                                
                        elif message_type == "delete_agent":
                            agent_name = message_json.get("name", "")
                            
                            logger.info(f"Deleting custom agent: {agent_name}")
                            
                            # Remove from CUSTOM_AGENTS list in traffic_cop
                            from traffic_cop import CUSTOM_AGENTS
                            
                            # Find and remove the agent by name
                            agent_found = False
                            for i, agent in enumerate(CUSTOM_AGENTS):
                                if agent.get("name") == agent_name:
                                    CUSTOM_AGENTS.pop(i)
                                    agent_found = True
                                    break
                            
                            if agent_found:
                                # Save to file
                                from traffic_cop import save_custom_agents
                                save_custom_agents()
                                
                                # Send confirmation
                                await websocket.send_text(json.dumps({
                                    "type": "system_message",
                                    "message": f"Custom agent '{agent_name}' deleted successfully"
                                }))
                                
                                logger.info(f"Custom agent deleted: {agent_name}")
                            else:
                                # Agent not found
                                await websocket.send_text(json.dumps({
                                    "type": "system_message",
                                    "message": f"Error: Agent '{agent_name}' not found"
                                }))
                                
                                logger.warning(f"Failed to delete agent: {agent_name} not found")
                        else:
                            # Handle get_available_models request
                            if message_type == "get_available_models":
                                # Get available models from the LLM client
                                available_models = llm_client.available_models()
                                active_provider = llm_client.active_provider
                                active_model = llm_client.active_model_name
                                
                                # Send response with available models
                                await websocket.send_text(json.dumps({
                                    "type": "available_models",
                                    "data": {
                                        "models": available_models,
                                        "active_provider": str(active_provider) if active_provider else None,
                                        "active_model": active_model
                                    }
                                }))
                                logger.info(f"Sent available models to client")
                            
                            # Handle set_model message for changing the active LLM
                            elif message_type == "set_model":
                                model_provider = message_json.get("provider", "").lower()
                                model_name = message_json.get("model", "")
                                
                                if model_provider == "claude":
                                    # Set Claude as active model
                                    if llm_client.claude_client:
                                        success = llm_client.set_active_provider(ModelProvider.CLAUDE, model_name)
                                        if success:
                                            await websocket.send_text(json.dumps({
                                                "type": "system_message",
                                                "message": f"Active model set to Claude: {llm_client.active_model_name}"
                                            }))
                                            logger.info(f"Changed active model to Claude: {llm_client.active_model_name}")
                                        else:
                                            await websocket.send_text(json.dumps({
                                                "type": "system_message",
                                                "message": "Failed to set Claude as active model"
                                            }))
                                    else:
                                        await websocket.send_text(json.dumps({
                                            "type": "system_message",
                                            "message": "Claude is not available. Check your API key configuration."
                                        }))
                                        
                                elif model_provider == "gemini":
                                    # Set Gemini as active model
                                    if llm_client.gemini_model:
                                        success = llm_client.set_active_provider(ModelProvider.GEMINI, model_name)
                                        if success:
                                            await websocket.send_text(json.dumps({
                                                "type": "system_message",
                                                "message": f"Active model set to Gemini: {llm_client.active_model_name}"
                                            }))
                                            logger.info(f"Changed active model to Gemini: {llm_client.active_model_name}")
                                        else:
                                            await websocket.send_text(json.dumps({
                                                "type": "system_message",
                                                "message": "Failed to set Gemini as active model"
                                            }))
                                    else:
                                        await websocket.send_text(json.dumps({
                                            "type": "system_message",
                                            "message": "Gemini is not available. Check your Google Cloud configuration."
                                        }))
                                        
                                else:
                                    await websocket.send_text(json.dumps({
                                        "type": "system_message",
                                        "message": f"Unknown model provider: {model_provider}"
                                    }))
                            
                            # Handle get_agent_prompt message to retrieve prompt from agent file
                            elif message_type == "get_agent_prompt":
                                agent_name = message_json.get("agent_name", "")
                                if not agent_name:
                                    await websocket.send_text(json.dumps({
                                        "type": "system_message",
                                        "message": "Error: Agent name is required"
                                    }))
                                    continue
                                
                                # Use the extract_agent_prompt utility function
                                from utils import extract_agent_prompt
                                result = extract_agent_prompt(agent_name)
                                
                                if "error" in result:
                                    await websocket.send_text(json.dumps({
                                        "type": "system_message",
                                        "message": result["error"]
                                    }))
                                else:
                                    # Send the prompt back to the client
                                    await websocket.send_text(json.dumps({
                                        "type": "agent_prompt",
                                        "agent_name": agent_name,
                                        "prompt": result["prompt_text"].strip(),
                                        "is_original": True
                                    }))
                                    logger.info(f"Sent prompt for agent: {agent_name}")
                                    
                            # Handle get_agent_versions message
                            elif message_type == "get_agent_versions":
                                agent_name = message_json.get("agent_name", "")
                                if not agent_name:
                                    await websocket.send_text(json.dumps({
                                        "type": "system_message",
                                        "message": "Error: Agent name is required"
                                    }))
                                    continue
                                
                                # Get versions for this agent
                                from agent_versions import get_agent_versions, extract_original_agent_prompt
                                
                                # Get the original prompt first
                                original = extract_original_agent_prompt(agent_name)
                                
                                # Get all custom versions
                                versions = get_agent_versions(agent_name)
                                
                                # Send the versions back to the client
                                await websocket.send_text(json.dumps({
                                    "type": "agent_versions",
                                    "agent_name": agent_name,
                                    "original": original,
                                    "versions": versions
                                }))
                                logger.info(f"Sent {len(versions)} versions for agent: {agent_name}")
                            
                            # Handle create_agent_version message
                            elif message_type == "create_agent_version":
                                agent_name = message_json.get("agent_name", "")
                                version_name = message_json.get("version_name", "")
                                prompt_text = message_json.get("prompt_text", "")
                                description = message_json.get("description", "")
                                
                                if not agent_name or not version_name or not prompt_text:
                                    await websocket.send_text(json.dumps({
                                        "type": "system_message",
                                        "message": "Error: Agent name, version name, and prompt text are required"
                                    }))
                                    continue
                                
                                # Create new version
                                from agent_versions import create_agent_version
                                result = create_agent_version(agent_name, prompt_text, version_name, description)
                                
                                if "error" in result:
                                    await websocket.send_text(json.dumps({
                                        "type": "system_message",
                                        "message": result["error"]
                                    }))
                                else:
                                    await websocket.send_text(json.dumps({
                                        "type": "system_message",
                                        "message": f"Created new version '{version_name}' for agent '{agent_name}'"
                                    }))
                                    logger.info(f"Created new version '{version_name}' for agent '{agent_name}'")
                            
                            # Handle delete_agent_version message
                            elif message_type == "delete_agent_version":
                                agent_name = message_json.get("agent_name", "")
                                version_name = message_json.get("version_name", "")
                                
                                if not agent_name or not version_name:
                                    await websocket.send_text(json.dumps({
                                        "type": "system_message",
                                        "message": "Error: Agent name and version name are required"
                                    }))
                                    continue
                                
                                # Delete version
                                from agent_versions import delete_agent_version
                                result = delete_agent_version(agent_name, version_name)
                                
                                if "error" in result:
                                    await websocket.send_text(json.dumps({
                                        "type": "system_message",
                                        "message": result["error"]
                                    }))
                                else:
                                    await websocket.send_text(json.dumps({
                                        "type": "system_message",
                                        "message": f"Deleted version '{version_name}' of agent '{agent_name}'"
                                    }))
                                    logger.info(f"Deleted version '{version_name}' of agent '{agent_name}'")
                            
                            # Handle use_agent_version message
                            elif message_type == "use_agent_version":
                                agent_name = message_json.get("agent_name", "")
                                version_name = message_json.get("version_name", "")
                                text = message_json.get("text", "")
                                
                                if not agent_name or not text:
                                    await websocket.send_text(json.dumps({
                                        "type": "system_message",
                                        "message": "Error: Agent name and text are required"
                                    }))
                                    continue
                                
                                # Create config for the agent
                                agent_config = {
                                    "name": agent_name,
                                    "type": "versioned",
                                }
                                
                                # Include version name if specified
                                if version_name:
                                    agent_config["version_name"] = version_name
                                
                                # Run the specified version of the agent
                                from traffic_cop import run_dynamic_agent
                                await run_dynamic_agent(
                                    text=text,
                                    model=gemini_model,
                                    broadcaster=broadcast_insight,
                                    agent_config=agent_config
                                )
                                
                                await websocket.send_text(json.dumps({
                                    "type": "system_message",
                                    "message": f"Running {agent_name} with version: {version_name or 'original'}"
                                }))
                                logger.info(f"Running {agent_name} with version: {version_name or 'original'}")
                            
                            # Handle update_agent_prompt message (legacy method)
                            elif message_type == "update_agent_prompt":
                                agent_name = message_json.get("agent_name", "")
                                new_prompt = message_json.get("prompt", "")
                                
                                if not agent_name or not new_prompt:
                                    await websocket.send_text(json.dumps({
                                        "type": "system_message",
                                        "message": "Error: Agent name and prompt are required"
                                    }))
                                    continue
                                
                                # Map agent names to their file names
                                agent_files = {
                                    "Radical Expander": "radical_expander.py",
                                    "Product Agent": "product_agent.py",
                                    "Debate Agent": "debate_agent.py", 
                                    "Skeptical Agent": "skeptical_agent.py",
                                    "Next Step Agent": "one_small_thing_agent.py",
                                    "Disruptor": "disruptor_agent.py"
                                }
                                
                                if agent_name in agent_files:
                                    try:
                                        # Get the file content
                                        file_path = os.path.join(os.path.dirname(__file__), "agents", agent_files[agent_name])
                                        with open(file_path, "r") as f:
                                            content = f.read()
                                        
                                        # Replace the prompt in the file
                                        new_content = ""
                                        if "direct_prompt = f\"\"\"" in content:
                                            # Replace content between triple quotes after direct_prompt =
                                            start_idx = content.find("direct_prompt = f\"\"\"", 0)
                                            if start_idx > 0:
                                                start_idx += len("direct_prompt = f\"\"\"")
                                                end_idx = content.find("\"\"\"", start_idx)
                                                if end_idx > start_idx:
                                                    new_content = content[:start_idx] + new_prompt + content[end_idx:]
                                        
                                        # If not found with direct_prompt, try with prompt =
                                        if not new_content and "prompt = f\"\"\"" in content:
                                            start_idx = content.find("prompt = f\"\"\"", 0)
                                            if start_idx > 0:
                                                start_idx += len("prompt = f\"\"\"")
                                                end_idx = content.find("\"\"\"", start_idx)
                                                if end_idx > start_idx:
                                                    new_content = content[:start_idx] + new_prompt + content[end_idx:]
                                        
                                        # If we successfully made a replacement, write it back
                                        if new_content:
                                            with open(file_path, "w") as f:
                                                f.write(new_content)
                                            
                                            await websocket.send_text(json.dumps({
                                                "type": "system_message",
                                                "message": f"Successfully updated prompt for {agent_name}"
                                            }))
                                            logger.info(f"Updated prompt for agent: {agent_name}")
                                        else:
                                            await websocket.send_text(json.dumps({
                                                "type": "system_message",
                                                "message": f"Could not find prompt section in file for {agent_name}"
                                            }))
                                    except Exception as e:
                                        logger.error(f"Error updating prompt for agent {agent_name}: {e}")
                                        await websocket.send_text(json.dumps({
                                            "type": "system_message",
                                            "message": f"Error updating prompt for agent {agent_name}: {str(e)}"
                                        }))
                                else:
                                    await websocket.send_text(json.dumps({
                                        "type": "system_message",
                                        "message": f"Agent not found or is a custom agent: {agent_name}"
                                    }))
                            else:
                                logger.warning(f"Received unknown message type: {message_type}")
                    
                    except json.JSONDecodeError:
                        logger.warning(f"Received non-JSON text message: {message_data[:100]}...")
                        
                except Exception as text_e:
                    logger.error(f"Error handling message: {text_e}")
                    # Continue the loop, don't break on message handling errors

    except WebSocketDisconnect:
        logger.info(f"Client {websocket.client} disconnected cleanly.")
    except Exception as e:
        logger.error(f"WebSocket error for {websocket.client}: {e}")
        logger.exception("Traceback:")
        try:
            # Attempt to close websocket with error code
            await websocket.close(code=1011) # Internal error
        except Exception as close_e:
             logger.error(f"Error closing WebSocket after error: {close_e}")

    finally:
        logger.info(f"Cleaning up WebSocket resources for {websocket.client}...")
        # Signal the audio generator to stop by putting None in the queue
        if audio_queue is not None:
            await audio_queue.put(None)

        # Cancel the transcription task if it's still running
        if transcription_task and not transcription_task.done():
            logger.info("Cancelling transcription task...")
            transcription_task.cancel()
            try:
                # Wait briefly for cancellation to complete
                await asyncio.wait_for(transcription_task, timeout=2.0)
            except asyncio.CancelledError:
                logger.info("Transcription task successfully cancelled.")
            except asyncio.TimeoutError:
                 logger.warning("Timeout waiting for transcription task cancellation.")
            except Exception as e_cancel:
                 logger.error(f"Error awaiting transcription task cancellation: {e_cancel}")
        else:
             logger.info("Transcription task not running or already done.")

        # Ensure disconnection from the manager
        manager.disconnect(websocket)
        logger.info(f"Cleanup complete for {websocket.client}.")


# --- Main execution (for local testing) ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0") # Allow host override
    logger.info(f"Starting server locally on {host}:{port}")
    # Use reload=True for development, disable for production
    uvicorn.run("main:app", host=host, port=port, reload=True)