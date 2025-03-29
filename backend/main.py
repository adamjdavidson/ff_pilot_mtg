# backend/main.py (Complete file - incorporating other LLM's fix approach)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
import logging
import os
import json
import asyncio

# Import Google Cloud libraries
from google.cloud import speech
from google.cloud import aiplatform
# Import only base classes needed here
from vertexai.generative_models import GenerativeModel, Part

# --- Configuration ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) # Define logger early

PROJECT_ID = "meetinganalyzer-454912"
LOCATION = "us-east1"
SPEECH_LANGUAGE_CODE = "en-US"
SPEECH_SAMPLE_RATE_HERTZ = 16000
# Use the model name confirmed from your last code paste
GEMINI_MODEL_NAME = "gemini-1.5-pro-002"
# Set stricter rate limit
last_traffic_cop_call_time = 0.0
MIN_TRAFFIC_COP_INTERVAL = 15.0

# --- Initialize Clients (Define Globals) ---
speech_client = None
gemini_model = None
grounding_tool = None # Grounding tool is explicitly removed/disabled

try:
    speech_client = speech.SpeechAsyncClient()
    logger.info("SpeechAsyncClient initialized successfully.")
except Exception as e:
    logger.error(f"Could not initialize Google Cloud SpeechAsyncClient: {e}")
    # speech_client remains None

try:
    endpoint = f"{LOCATION}-aiplatform.googleapis.com"
    aiplatform.init(project=PROJECT_ID, location=LOCATION, api_endpoint=endpoint)
    logger.info(f"Vertex AI initialized with endpoint: {endpoint}")

    gemini_model = GenerativeModel(GEMINI_MODEL_NAME)
    logger.info(f"Vertex AI SDK GenerativeModel loaded: {GEMINI_MODEL_NAME}.")

except ImportError as e:
     logger.error(f"ImportError during Vertex AI init: {e}")
     gemini_model = None
except Exception as e:
    logger.error(f"Could not initialize Vertex AI / Gemini: {e}")
    logger.exception("Full traceback:")
    gemini_model = None


app = FastAPI()

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self): self.active_connections: list[WebSocket] = []
    async def connect(self, websocket: WebSocket): await websocket.accept(); self.active_connections.append(websocket); logger.info(f"New WebSocket connection: {websocket.client}")
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections: self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected: {websocket.client}")
    async def broadcast(self, message: str):
        logger.info(f"Broadcasting message: {message}")
        for connection in list(self.active_connections):
            try: await connection.send_text(message)
            except Exception as e: logger.error(f"Failed to send message to {connection.client}: {e}"); self.disconnect(connection)
manager = ConnectionManager()

# --- Broadcast Insight Function ---
async def broadcast_insight(insight_data: dict):
    """Helper function to broadcast insights via the manager."""
    try:
        message_str = json.dumps(insight_data)
        await manager.broadcast(message_str)
    except Exception as e:
        logger.error(f"Error broadcasting insight: {e}")


# --- Agent Implementations ---

async def run_radical_expander(transcript_text: str):
    """Generates expansive, non-obvious ideas based on the transcript using a refined prompt."""
    logger.info(">>> Running Radical Expander Agent...")
    if not gemini_model: logger.error("Radical Expander: Gemini model not available."); return

    # Using the refined prompt from response #59
    prompt = f"""
    You are an AI assistant inspired by Ethan Mollick's thinking about the non-obvious impacts of technology.
    Analyze the core idea or topic discussed in this meeting transcript segment:
    "{transcript_text}"

    Generate 1-2 concise, provocative insights that radically expand on this core topic. Focus on:
    - Non-obvious second-order effects.
    - Unexpected ways workflows or business models could change.
    - Speculative but plausible future possibilities enabled by this core idea.
    - Avoid generic predictions. Be specific and stimulating. Do not ask for more input.
    """
    try:
        response = await gemini_model.generate_content_async(prompt)
        generated_text = response.text.strip()

        if not generated_text or "what ideas" in generated_text.lower() or "expand on" in generated_text.lower() or len(generated_text) < 20:
            logger.warning(f"Radical Expander gave generic/short response: '{generated_text}'")
        else:
            logger.info(f"Radical Expander generated: {generated_text}")
            insight_data = {
                "type": "insight",
                "agent": "Radical Expander",
                "content": generated_text
            }
            await broadcast_insight(insight_data)

    except Exception as e:
        logger.error(f"Error in Radical Expander agent: {e}")
        logger.exception("Traceback:")


async def run_fact_checker(transcript_text: str):
    """Placeholder - identifies topic but performs NO actual fact-checking/search."""
    logger.info(">>> Running Fact Checker / Let's Check Agent...")
    logger.info("Fact Checker: Grounding tool/search functionality is currently disabled.")

    if not gemini_model: logger.error("Fact Checker: Gemini model not available."); return

    # Example: Simple response without search - just identify topic
    prompt = f"""
    Analyze the following meeting transcript segment:
    "{transcript_text}"
    Very briefly, state the main factual topic or question being discussed.
    """
    try:
        response = await gemini_model.generate_content_async(prompt)
        generated_text = response.text.strip()
        logger.info(f"Fact Checker (basic topic ID) generated: {generated_text}")
        insight_data = {
            "type": "insight",
            "agent": "Fact Checker / Let's Check",
            "content": f"[Topic ID Only]: {generated_text}" # Indicate no search was done
        }
        await broadcast_insight(insight_data)

    except Exception as e:
         logger.error(f"Error in basic Fact Checker agent: {e}")

# --- Other Placeholder Agent Functions ---
async def run_strategic_reframer(transcript_text: str): logger.info(">>> Strategic Re-framer Agent Triggered (Not Implemented Yet)"); pass
async def run_cross_domain_connector(transcript_text: str): logger.info(">>> Cross-Domain Connector Agent Triggered (Not Implemented Yet)"); pass
async def run_takeaway_agent(transcript_text: str): logger.info(">>> Takeaway Agent Triggered (Not Implemented Yet)"); pass
async def run_controversy_agent(transcript_text: str): logger.info(">>> Controversy Agent Triggered (Not Implemented Yet)"); pass
async def run_existential_debate_agent(transcript_text: str): logger.info(">>> Existential Debate Agent Triggered (Not Implemented Yet)"); pass


# --- Agent Trigger Router ---
async def trigger_agent(agent_name: str, transcript_text: str):
    """Calls the appropriate agent function based on the name."""
    # This function is now called by handle_transcript_response
    logger.info(f"--- Triggering Agent: {agent_name}")
    agent_functions = {
        "Radical Expander": run_radical_expander,
        "Fact Checker / Let's Check": run_fact_checker,
        "Strategic Re-framer": run_strategic_reframer,
        "Cross-Domain Connector": run_cross_domain_connector,
        "Takeaway Agent": run_takeaway_agent,
        "Controversy Agent": run_controversy_agent,
        "Existential Debate Agent": run_existential_debate_agent,
        # "None": None # Explicitly handle None in the caller
    }

    if agent_name in agent_functions:
        await agent_functions[agent_name](transcript_text)
    elif agent_name == "None":
         logger.info("--- Agent chosen: None. No action taken by trigger_agent.") # Should be handled before calling
    else:
        logger.warning(f"--- Agent '{agent_name}' is not implemented or recognized by trigger_agent.")


# --- Traffic Cop Function (Modified to RETURN agent name) ---
async def route_to_traffic_cop(transcript_text: str):
    """Sends transcript to Gemini, parses response, returns chosen agent name or None."""
    logger.info(f"--- Sending to Traffic Cop: '{transcript_text}'")
    if not gemini_model:
        logger.error("Traffic Cop: Gemini model not available.")
        return None # Return None if model isn't ready

    available_agents = [
        "Radical Expander", "Strategic Re-framer", "Cross-Domain Connector",
        "Fact Checker / Let's Check", "Takeaway Agent", "Controversy Agent",
        "Existential Debate Agent", "None"
    ]
    prompt = f"""
    You are a "Traffic Cop" AI analyzing a meeting transcript segment. Your job is to determine which specialized AI agent should process this segment next.

    Transcript Segment:
    "{transcript_text}"

    Available Agents:
    {', '.join(available_agents)}

    Analyze the transcript segment and decide which *single* agent is the MOST relevant or if 'None' are suitable. Consider the triggers mentioned previously.

    Output ONLY the name of the chosen agent from the list above. Just the name.
    """
    try:
        response = await gemini_model.generate_content_async(prompt)
        raw_choice = response.text.strip()
        logger.info(f"--- Traffic Cop Raw Response: '{raw_choice}'")

        # *** Robust Parsing Logic ***
        parsed_agent = "None" # Default to None
        for agent in available_agents:
            # Check if known agent name is substring (case-insensitive)
            if agent != "None" and agent.lower() in raw_choice.lower():
                 parsed_agent = agent
                 logger.info(f"--- Found agent match: {agent}")
                 break # Take the first match found

        logger.info(f"--- Traffic Cop Parsed Agent: {parsed_agent}")
        # Ensure we only return valid names or None
        if parsed_agent in available_agents:
            return parsed_agent
        else:
            logger.warning(f"Parsed agent '{parsed_agent}' not in list, returning None.")
            return "None"

    except Exception as e:
        logger.error(f"Error calling Traffic Cop (Gemini via Vertex AI): {e}")
        logger.exception("Traceback:")
        return None # Return None on error


# --- Transcription Handling (Modified to use Traffic Cop return value) ---
async def handle_transcript_response(response_stream, websocket: WebSocket):
    """Handles responses from the Speech-to-Text API stream."""
    global last_traffic_cop_call_time
    logger.info(">>> handle_transcript_response: Started")
    try:
        async for response in response_stream:
            if not response.results: continue
            result = response.results[0]
            if not result.alternatives: continue

            transcript = result.alternatives[0].transcript

            if result.is_final:
                logger.info(f"Final Transcript: {transcript}")

                # Skip empty or very short transcripts
                if not transcript or len(transcript.strip()) < 5: # Check length 5 or more
                    logger.info("Transcript too short, skipping Traffic Cop call.")
                    continue # Skip to next response

                current_time = asyncio.get_event_loop().time()
                time_since_last_call = current_time - last_traffic_cop_call_time

                if time_since_last_call >= MIN_TRAFFIC_COP_INTERVAL:
                    logger.info(f"Interval passed ({time_since_last_call:.1f}s >= {MIN_TRAFFIC_COP_INTERVAL}s). Calling Traffic Cop.")
                    last_traffic_cop_call_time = current_time

                    # Get the agent name from traffic cop
                    agent_name = await route_to_traffic_cop(transcript) # Function now returns name

                    # Only trigger agent if a valid one was returned and it's not "None"
                    if agent_name and agent_name != "None":
                        await trigger_agent(agent_name, transcript)
                    elif agent_name == "None":
                        logger.info("Traffic Cop decided no agent is needed for this transcript.")
                    else: # Should mean route_to_traffic_cop returned None due to error
                        logger.warning("Traffic Cop returned no agent (likely due to an error), skipping trigger.")
                else:
                    logger.info(f"Skipping Traffic Cop call (interval not met: {time_since_last_call:.1f}s < {MIN_TRAFFIC_COP_INTERVAL}s).")
            else:
                logger.debug(f"Interim Transcript: {transcript}")
    except asyncio.CancelledError:
        logger.info("Transcript response handler cancelled.")
    except Exception as e:
        logger.error(f"Error in transcript response handler: {e}")
        logger.exception("Traceback:") # Log full traceback here
    finally:
        logger.info("Transcript response handler finished.")


async def audio_request_generator(audio_queue: asyncio.Queue):
    """Generates requests for the Speech-to-Text API stream."""
    logger.info(">>> audio_request_generator: Started")
    streaming_config = speech.StreamingRecognitionConfig(
        config=speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=SPEECH_SAMPLE_RATE_HERTZ,
            language_code=SPEECH_LANGUAGE_CODE,
            enable_automatic_punctuation=True
        ),
        interim_results=True
    )
    yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)
    logger.info("Sent streaming config to Speech API.")
    while True:
        try:
            audio_chunk = await asyncio.wait_for(audio_queue.get(), timeout=5.0)
            if audio_chunk is None: logger.info("Received None, stopping audio stream generation."); break
            yield speech.StreamingRecognizeRequest(audio_content=audio_chunk)
            audio_queue.task_done()
        except asyncio.TimeoutError: continue
        except asyncio.CancelledError: logger.info("Audio request generator cancelled."); break
        except Exception as e: logger.error(f"Error in audio request generator: {e}"); break
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
    response_stream = None

    try:
        # Log client status on connection for debugging
        logger.info(f"Speech client ready: {bool(speech_client)}")
        logger.info(f"Gemini model ready: {bool(gemini_model)}")

        if not speech_client or not gemini_model:
            logger.error("Backend clients not ready during connection.")
            # Send error and close connection gracefully
            await websocket.send_text(json.dumps({"type": "error", "message": "Backend AI/Speech services not ready. Please try again later."}))
            await websocket.close(code=1011) # Internal error
            return

        logger.info(">>> websocket_endpoint: Creating request generator")
        request_generator = audio_request_generator(audio_queue)

        logger.info(">>> websocket_endpoint: Starting streaming_recognize")
        response_stream = await speech_client.streaming_recognize(requests=request_generator)
        logger.info(">>> websocket_endpoint: streaming_recognize call returned")

        logger.info(">>> websocket_endpoint: Creating transcription task")
        transcription_task = asyncio.create_task(handle_transcript_response(response_stream, websocket))
        logger.info(">>> websocket_endpoint: Transcription task created")

        # --- Receive Audio Loop ---
        while True:
            audio_data = await websocket.receive_bytes()
            if not audio_data: continue
            await audio_queue.put(audio_data)

    except WebSocketDisconnect:
        logger.info(f"Client {websocket.client} disconnected cleanly.")
    except Exception as e:
        logger.error(f"WebSocket error for {websocket.client}: {e}")
        logger.exception("Traceback:") # Log full traceback for WebSocket errors
        try:
            # Attempt to close websocket on error
            await websocket.close(code=1011) # Internal error
        except Exception as close_e:
             logger.error(f"Error closing WebSocket after error: {close_e}")

    finally:
        logger.info(f"Cleaning up WebSocket for {websocket.client}...")
        if audio_queue is not None:
            await audio_queue.put(None) # Signal audio generator to stop

        # Check if task exists and is not done before cancelling
        if transcription_task and not transcription_task.done():
            logger.info("Cancelling transcription task...")
            transcription_task.cancel()
            try:
                await asyncio.wait_for(transcription_task, timeout=2.0) # Wait briefly
            except asyncio.CancelledError:
                logger.info("Transcription task successfully cancelled.")
            except asyncio.TimeoutError:
                 logger.warning("Timeout waiting for transcription task cancellation.")
            except Exception as e_cancel:
                 logger.error(f"Error awaiting transcription task cancellation: {e_cancel}")
        else:
             logger.info("Transcription task not running or already done.")

        manager.disconnect(websocket)
        logger.info(f"Cleanup complete for {websocket.client}.")


# --- Main execution (for local testing) ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server locally on port {port}")
    # Note: Uvicorn needs the app location string 'module:variable'
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)