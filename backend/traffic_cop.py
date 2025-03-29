# backend/traffic_cop.py (Revised Prompt for Routing)
import asyncio
import logging
import json
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.generative_models as generative_models

# Get the logger instance configured in main.py
logger = logging.getLogger("main")

# --- Import Agent Functions using ABSOLUTE paths from /app ---
try:
    # Assumes agents folder is directly under the WORKDIR (/app)
    from agents.radical_expander import run_radical_expander
    from agents.product_agent import run_product_agent
    from agents.debate_agent import run_debate_agent
    from agents.skeptical_agent import run_skeptical_agent
    from agents.one_small_thing_agent import run_one_small_thing_agent
    # Import other agents here if/when added
    logger.info("Successfully imported agent functions using absolute paths.")
except ImportError as e:
    logger.error(f"Failed to import one or more agent functions using absolute paths: {e}")
    # Define dummies or raise error depending on desired behavior
    async def run_radical_expander(*args, **kwargs): logger.error("Radical Expander not loaded"); await args[-1]({"type":"error", "agent": "Radical Expander", "message":"Not loaded"}) # Assume broadcaster is last arg
    async def run_product_agent(*args, **kwargs): logger.error("Product Agent not loaded"); await args[-1]({"type":"error", "agent": "Wild Product Agent", "message":"Not loaded"})
    async def run_debate_agent(*args, **kwargs): logger.error("Debate Agent not loaded"); await args[-1]({"type":"error", "agent": "Debate Agent", "message":"Not loaded"})
    async def run_skeptical_agent(*args, **kwargs): logger.error("Skeptical Agent not loaded"); await args[-1]({"type":"error", "agent": "Skeptical Agent", "message":"Not loaded"})
    async def run_one_small_thing_agent(*args, **kwargs): logger.error("One Small Thing Agent not loaded"); await args[-1]({"type":"error", "agent": "One Small Thing", "message":"Not loaded"})


# --- Agent Routing Configuration ---
# Agents routable by LLM content analysis
LLM_ROUTABLE_AGENTS = {
    "Radical Expander": run_radical_expander,
    "Wild Product Agent": run_product_agent,
    "Skeptical Agent": run_skeptical_agent,
    "One Small Thing": run_one_small_thing_agent,
    # Add other LLM-routable agents here
}

# Define explicit trigger phrases for Debate Agent
DEBATE_AGENT_TRIGGERS = ["debate agent", "analyze conflict"] # Case-insensitive check later

# Define explicit trigger phrases for Skeptical Agent
SKEPTICAL_AGENT_TRIGGERS = ["skeptical agent", "devil's advocate", "critique this", "what could go wrong"] # Case-insensitive check later

# Define explicit trigger phrases for One Small Thing Agent
ONE_SMALL_THING_TRIGGERS = ["one small thing", "first step", "where to start", "how to begin", "quick win"] # Case-insensitive check later

# --- Traffic Cop Core Logic ---

# Note: Removed the type hint fix here as it should be done by changing Python version
async def route_to_traffic_cop(transcript_text: str, model: GenerativeModel):
    """
    Determines which agent to run. Checks for explicit triggers first,
    then uses the Gemini model for content-based routing for other agents.
    Returns agent name (str) or None.
    """
    logger.info(">>> route_to_traffic_cop: Analyzing transcript for routing...")

    # 1. Check for Explicit Triggers (Debate Agent)
    # Using lower() for case-insensitive matching
    if any(phrase in transcript_text.lower() for phrase in DEBATE_AGENT_TRIGGERS):
        logger.info(f"--- Explicit trigger detected for Debate Agent")
        return "Debate Agent" # Return specific name
        
    # Check for Explicit Triggers (Skeptical Agent)
    if any(phrase in transcript_text.lower() for phrase in SKEPTICAL_AGENT_TRIGGERS):
        logger.info(f"--- Explicit trigger detected for Skeptical Agent")
        return "Skeptical Agent" # Return specific name
        
    # Check for Explicit Triggers (One Small Thing Agent)
    if any(phrase in transcript_text.lower() for phrase in ONE_SMALL_THING_TRIGGERS):
        logger.info(f"--- Explicit trigger detected for One Small Thing Agent")
        return "One Small Thing" # Return specific name

    # 2. If no explicit trigger, proceed with content-based routing (if model available)
    if not model:
        logger.error("Routing failed: Gemini model is not available for content-based routing.")
        return None

    llm_agent_names = list(LLM_ROUTABLE_AGENTS.keys())
    if not llm_agent_names:
        logger.warning("Routing skipped: No LLM-routable agents are configured.")
        return "None"

    possible_agents_str = ", ".join(llm_agent_names)

    prompt = f"""
You are a "Traffic Cop" AI analyzing meeting transcript segments. Your job is to determine which specialized AI agent should process each segment next, IF ANY. Do NOT choose 'Debate Agent' or any agents not listed below.

Available Agents (Choose ONE or None):
- Radical Expander: Triggered by discussions focused on *internal* business operations, workflows, or organizational design. Examples include:
    - How we conduct meetings/collaborations.
    - How we report information internally.
    - How we develop new products (the *process* of development).
    - How we analyze our financial data (the *process* of analysis).
    - How we structure our teams or departments.
    - How we manage projects or track progress.
    This agent proposes *radical rethinkings* or *paradigm shifts* in these *internal* areas.
- Wild Product Agent: Triggered by discussions focused on *external*, customer-facing offerings. Examples include:
    - What products/services we offer to customers.
    - New product/service concepts or ideas.
    - Ways to improve existing products/services for customers.
    - Customer needs, problems, or feedback related to our offerings.
- Skeptical Agent: Triggered by discussions where someone proposes an idea, plan, or solution that would benefit from critical analysis. Examples include:
    - When a new initiative is being proposed and benefits are emphasized without considering difficulties.
    - During discussions about resource allocation or investment decisions.
    - When significant organizational changes are proposed.
    - During discussions that seem overly optimistic without addressing risks.
    This agent identifies potential challenges, assumptions, and risks that might not have been considered.
- One Small Thing: Triggered by discussions about implementing AI where participants need practical next steps. Examples include:
    - When participants express interest in AI but aren't sure where to start.
    - During discussions about AI capabilities that could immediately benefit their work.
    - When participants want to implement AI but are concerned about complexity or risk.
    - During conversations where immediate, practical action items would be valuable.
    This agent suggests one concrete, immediately implementable first step to begin an AI journey.

Transcript Segment:
"{transcript_text}"

Examples of Routing Decisions:
- "Our weekly status meetings are incredibly inefficient and waste a lot of time." -> Radical Expander (internal process)
- "What new AI-powered tools could help us automate expense reporting for employees?" -> Radical Expander (internal process)
- "Should we offer a personalized meal planning subscription service to our customers?" -> Wild Product Agent (external service)
- "Customer churn is way too high; we need to reduce it for our premium product." -> Wild Product Agent (external product/service)
- "Should we completely reimagine our sales compensation structure for our sales team?" -> Radical Expander (internal structure/process)
- "I propose implementing a companywide AI assistant for all employees to boost productivity." -> Skeptical Agent (new initiative that needs critical examination)
- "The plan is to roll out the new system to all departments simultaneously next month." -> Skeptical Agent (ambitious plan that may overlook challenges)
- "Our competitors aren't a concern since our new feature is revolutionary and they can't catch up." -> Skeptical Agent (potentially overlooking market realities)
- "We should migrate all our systems to this new technology immediately." -> Skeptical Agent (potential implementation challenges)
- "We're interested in using AI for customer service, but we're not sure where to start." -> One Small Thing (need for practical first step)
- "How could we begin using AI in our HR processes without a big investment?" -> One Small Thing (looking for an entry point)
- "I'm concerned about implementing AI because it seems so complex." -> One Small Thing (needs a simple starting point)
- "What would be the quickest way to see some value from AI in our operations?" -> One Small Thing (seeking quick wins)

Which agent from the list above is the MOST relevant for this specific segment? Output ONLY the name of the chosen agent or the word "None".
"""

    try:
        logger.info("Sending content-based routing request to Gemini...")
        response = await model.generate_content_async(
            prompt,
            generation_config={"temperature": 0.2, "max_output_tokens": 50},
            safety_settings={
                generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
        )
        logger.debug(f"Routing response received: {response}")

        if response.candidates and response.candidates[0].finish_reason == FinishReason.SAFETY:
             logger.warning("Routing decision blocked by safety settings. Defaulting to None.")
             return "None"

        if response.text:
            # More robust cleaning, handle potential markdown like ```agent_name```
            raw_choice = response.text.strip().replace('"', '').replace("'", '').replace('.', '').replace('`', '')

            # Check for exact match first (case-insensitive)
            for agent_name in llm_agent_names:
                if agent_name.lower() == raw_choice.lower():
                    logger.info(f"Routing decision (LLM - Exact): Trigger '{agent_name}'")
                    return agent_name

            # If no exact match, check containment (as fallback) - might be less reliable
            for agent_name in llm_agent_names:
                 if agent_name.lower() in raw_choice.lower():
                      logger.info(f"Routing decision (LLM - Contained): Trigger '{agent_name}'")
                      return agent_name

            # Check for "None" variations
            if "none" in raw_choice.lower():
                 logger.info("Routing decision (LLM): No agent needed ('None')")
                 return "None"

            # If we reach here, it's an unknown response
            logger.warning(f"Routing failed: Model returned an unrecognized response: '{raw_choice}'. Defaulting to None.")
            return "None"

        else:
             logger.warning("Routing failed: Model did not return a valid text response. Defaulting to None.")
             return "None"

    except Exception as e:
        logger.error(f"Error during content-based routing with Gemini model: {e}")
        logger.exception("Traceback:")
        return None

# --- Agent Trigger Dispatcher ---
async def trigger_agent(
    name: str,
    current_segment_text: str,
    model: GenerativeModel,
    broadcaster: callable,
    context_buffer: str
):
    """
    Triggers the specified agent function, passing the appropriate context.
    """
    logger.info(f">>> trigger_agent: Attempting to trigger agent '{name}'")

    # Combine all known agent functions for lookup using corrected absolute imports
    all_agent_functions = {
        "Radical Expander": run_radical_expander,
        "Wild Product Agent": run_product_agent,
        "Debate Agent": run_debate_agent,
        "Skeptical Agent": run_skeptical_agent,
        "One Small Thing": run_one_small_thing_agent,
        # Add mappings for other agents if/when imported
    }

    agent_function = all_agent_functions.get(name)

    if agent_function:
        try:
            if name == "Debate Agent":
                logger.info(f"--- Passing context buffer (len: {len(context_buffer)}) to {name}")
                await agent_function(recent_context=context_buffer, model=model, broadcaster=broadcaster)
            # Check if the agent is one of the content-routable ones expecting 'text'
            elif name in LLM_ROUTABLE_AGENTS:
                 logger.info(f"--- Passing current segment (len: {len(current_segment_text)}) to {name}")
                 await agent_function(text=current_segment_text, model=model, broadcaster=broadcaster)
            else:
                 # Fallback for safety, though ideally all called agents should be categorized
                 logger.warning(f"Agent '{name}' triggered but not explicitly categorized for context. Passing current segment.")
                 await agent_function(text=current_segment_text, model=model, broadcaster=broadcaster)

            logger.info(f"Agent '{name}' execution initiated successfully.")

        except Exception as e:
            logger.error(f"Error executing agent '{name}': {e}")
            logger.exception("Traceback:")
            try:
                await broadcaster({"type": "error", "agent": name, "message": f"Failed to execute agent '{name}'."})
            except Exception as broadcast_err:
                 logger.error(f"Failed to broadcast agent execution error: {broadcast_err}")
    else:
        logger.warning(f"Attempted to trigger unknown agent: '{name}'")
        try:
            await broadcaster({"type": "error", "agent": "System", "message": f"Unknown agent requested: '{name}'."})
        except Exception as broadcast_err:
             logger.error(f"Failed to broadcast unknown agent error: {broadcast_err}")
