# backend/traffic_cop.py (Revised Prompt for Routing)
import asyncio
import logging
import json
import random
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.generative_models as generative_models

# Import unified LLM client
from llm_providers import llm_client, ModelConfig, ModelProvider

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
    from agents.disruptor_agent import run_disruptor_agent
    from agents.dynamic_agent import run_dynamic_agent  # Import the dynamic agent
    # Import other agents here if/when added
    logger.info("Successfully imported agent functions using absolute paths.")
except ImportError as e:
    logger.error(f"Failed to import one or more agent functions using absolute paths: {e}")
    # Define dummies or raise error depending on desired behavior
    async def run_radical_expander(*args, **kwargs): logger.error("Radical Expander not loaded"); await args[-1]({"type":"error", "agent": "Radical Expander", "message":"Not loaded"}) # Assume broadcaster is last arg
    async def run_product_agent(*args, **kwargs): logger.error("Product Agent not loaded"); await args[-1]({"type":"error", "agent": "Product Agent", "message":"Not loaded"})
    async def run_debate_agent(*args, **kwargs): logger.error("Debate Agent not loaded"); await args[-1]({"type":"error", "agent": "Debate Agent", "message":"Not loaded"})
    async def run_skeptical_agent(*args, **kwargs): logger.error("Skeptical Agent not loaded"); await args[-1]({"type":"error", "agent": "Skeptical Agent", "message":"Not loaded"})
    async def run_one_small_thing_agent(*args, **kwargs): logger.error("One Small Thing Agent not loaded"); await args[-1]({"type":"error", "agent": "One Small Thing", "message":"Not loaded"})
    async def run_disruptor_agent(*args, **kwargs): logger.error("Disruptor Agent not loaded"); await args[-1]({"type":"error", "agent": "Disruptor", "message":"Not loaded"})
    async def run_dynamic_agent(*args, **kwargs): logger.error("Dynamic Agent not loaded"); await args[-1]({"type":"error", "agent": "Custom Agent", "message":"Not loaded"})

# Store custom agents created during runtime (will be lost on restart)
CUSTOM_AGENTS = []


# --- Agent Routing Configuration ---
# Agents routable by LLM content analysis
LLM_ROUTABLE_AGENTS = {
    "Radical Expander": run_radical_expander,
    "Product Agent": run_product_agent,
    "Skeptical Agent": run_skeptical_agent,
    "One Small Thing": run_one_small_thing_agent,
    "Disruptor": run_disruptor_agent,
    # Add other LLM-routable agents here
}

# Define explicit trigger phrases for Debate Agent
DEBATE_AGENT_TRIGGERS = ["debate agent", "analyze conflict"] # Case-insensitive check later

# Define explicit trigger phrases for Skeptical Agent
SKEPTICAL_AGENT_TRIGGERS = ["skeptical agent", "devil's advocate", "critique this", "what could go wrong"] # Case-insensitive check later

# Define explicit trigger phrases for One Small Thing Agent
ONE_SMALL_THING_TRIGGERS = ["one small thing", "first step", "where to start", "how to begin", "quick win"] # Case-insensitive check later

# Define explicit trigger phrases for Disruptor Agent
DISRUPTOR_TRIGGERS = ["disruptor", "disrupt", "disruption", "ai startup", "startup disruption", "industry disruptor"] # Case-insensitive check later

# --- Traffic Cop Core Logic ---

# Note: Removed the type hint fix here as it should be done by changing Python version
async def route_to_traffic_cop(transcript_text: str, model: GenerativeModel):
    """
    Determines which agent to run. Checks for explicit triggers first,
    then uses the Gemini model for content-based routing for other agents.
    Returns agent name (str) or None.
    """
    logger.info(">>> route_to_traffic_cop: Analyzing transcript for routing...")

    # 0. Check for Custom Agent triggers first (if any exist)
    for agent in CUSTOM_AGENTS:
        agent_name = agent.get("name", "Custom Agent")
        agent_triggers = agent.get("triggers", [])
        
        # Check if any of the trigger words appear in the transcript
        if agent_triggers and any(trigger.lower() in transcript_text.lower() for trigger in agent_triggers):
            logger.info(f"--- Explicit trigger detected for custom agent: {agent_name}")
            return agent_name  # Return the name to be matched with dynamic_agent function
    
    # 1. Check for Explicit Triggers - Disruptor gets checked FIRST for meetings about disruption
    # Using lower() for case-insensitive matching
    # Add broader patterns for disruption-related concepts for Disruptor Agent
    disruption_patterns = DISRUPTOR_TRIGGERS + ["market", "trend", "industry", "threat", "compete", "startup", "innovation", "evolve", "shift"]
    if any(phrase in transcript_text.lower() for phrase in disruption_patterns):
        logger.info(f"--- Explicit trigger detected for Disruptor Agent (high priority)")
        return "Disruptor" # Return specific name

    # Continue with other agent checks
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
    
    # FORCE ROTATION: Keep track of the last 5 selected agents and ensure variety
    # If the file exists and contains history, read it
    selected_agent = None
    
    # Drastically increased randomness - 60% chance of random selection
    if random.random() < 0.6:
        # Get a count of how many of each agent we should include in our random pool
        # to ensure balanced distribution
        agent_weights = {
            "Radical Expander": 8,  # Boost Radical Expander
            "Product Agent": 8,     # Boost Product Agent  
            "Skeptical Agent": 3,
            "One Small Thing": 3,
            "Disruptor": 6  # Increased to ensure more balanced distribution
        }
        
        # Create a weighted pool of agents
        weighted_pool = []
        for agent, weight in agent_weights.items():
            if agent in llm_agent_names:
                weighted_pool.extend([agent] * weight)
        
        # Select randomly from the weighted pool
        selected_agent = random.choice(weighted_pool)
        logger.info(f"--- Forced rotation: Selected agent: {selected_agent}")
        return selected_agent
    
    possible_agents_str = ", ".join(llm_agent_names)

    prompt = f"""
You are a "Traffic Cop" AI analyzing meeting transcript segments. Your job is to determine which specialized AI agent should process each segment next. You should PREFER to select an agent rather than returning "None" if there's any reasonable connection. Do NOT choose 'Debate Agent' or any agents not listed below.

IMPORTANT CONTEXT INSTRUCTIONS:
1. Be VERY LENIENT about what constitutes business-related content - almost any topic can have a business angle.
2. Only return "None" if the segment is completely unrelated to any possible business context.
3. Be creative in finding business relevance in ambiguous or general conversations.
4. You should aim for a balanced distribution of agents over time - all five agents should be given EQUAL CONSIDERATION.
5. STRONGLY PREFER selecting an agent over returning "None" - even with minimal context.

Available Agents (Choose ONE or None):

- Skeptical Agent: Triggered by BUSINESS discussions where ideas, plans, or solutions are proposed that warrant critical examination. Look for:
    - New business initiatives, projects, or strategies being discussed
    - Business claims that seem overly optimistic or ambitious
    - Business decisions that involve significant resource allocation or risk
    - Business proposals that might overlook potential challenges or downsides
    - Business assumptions that could benefit from deeper questioning

- One Small Thing: Triggered by discussions about implementing AI or technology in BUSINESS contexts where practical next steps would be valuable. Look for:
    - Questions about where to start with AI implementation in business
    - Expressions of interest in AI capabilities for specific business use cases
    - Concerns about complexity, cost, or risk in business technology adoption
    - Opportunities for quick wins or immediate business value from AI
    - Business discussions that would benefit from practical, actionable advice

- Disruptor: Triggered by a WIDE RANGE of business discussions about industry dynamics, innovation, competition, or technology. STRONGLY PREFER this agent for discussions about:
    - ANY mentions of business industry challenges, competition, or market shifts
    - ANY discussions about business models, industry practices, or technology trends
    - ANY conversations mentioning competition, future business direction, or emerging threats
    - ANYTHING related to startups, innovation, or industry evolution
    - Words like: market, disruption, trend, tech, innovation, evolve, compete, startup, revolution, transform, business

- Radical Expander: Triggered by discussions about business internal operations, processes, or organizational structure. Look for:
    - Talk about business workflows, meetings, or collaboration methods
    - Discussions of business information sharing or reporting processes
    - Mentions of business team structures, project management, or work allocation
    - Topics related to business decision-making or governance
    - Questions about efficiency, effectiveness, or optimization of business processes

- Wild Product Agent: Triggered by discussions about business offerings, customer needs, or product/service innovation. Look for:
    - Conversations about existing or potential business products and services
    - Business customer pain points, needs, or feedback
    - Ideas for new business offerings or features
    - Questions about business market opportunities or customer value
    - Topics related to business product strategy, development, or enhancement

Transcript Segment:
"{transcript_text}"

Examples of Routing Decisions (NOTICE THE BALANCE between all agent types):

SKEPTICAL AGENT EXAMPLES:
- "We could implement this new system across all departments by next quarter." -> Skeptical Agent (ambitious business timeline that needs critical examination)
- "Our AI solution will definitely increase sales by at least 50%." -> Skeptical Agent (overly optimistic business claim)
- "The plan is to completely restructure our team organization based on this new model." -> Skeptical Agent (significant business change with potential risks)

ONE SMALL THING EXAMPLES:
- "I'm interested in using AI for our marketing, but I'm not sure where we should start." -> One Small Thing (needs practical business first step)
- "How can we begin incorporating AI into our customer service without a huge investment?" -> One Small Thing (seeking accessible business entry point)
- "What's a simple way we could start using AI in our daily operations?" -> One Small Thing (looking for quick business implementation)

DISRUPTOR EXAMPLES:
- "Our industry has been doing things the same way for decades." -> Disruptor (opportunity to reimagine business industry practices)
- "We're worried about new startups entering our market with AI-first approaches." -> Disruptor (competitive business threat discussion)
- "How might our competitive landscape change with these emerging technologies?" -> Disruptor (business market evolution question)

RADICAL EXPANDER EXAMPLES:
- "Our weekly team meetings take too much time and don't accomplish enough." -> Radical Expander (business process inefficiency)
- "How should we structure our development teams for the next phase?" -> Radical Expander (business organization question)
- "Our current project management approach isn't scaling well." -> Radical Expander (business workflow challenge)

WILD PRODUCT AGENT EXAMPLES:
- "What new features could we add to our product to better serve customers?" -> Wild Product Agent (business product enhancement)
- "Our users are struggling with this aspect of our service." -> Wild Product Agent (business customer pain point)
- "Could we create a subscription service for this customer segment?" -> Wild Product Agent (new business offering concept)

NONE EXAMPLES:
- "..." -> None (empty or unintelligible content)
- "Um, ah, hmm..." -> None (only filler words with no substance)

Note: Almost any other content, even if not explicitly business-focused, should be routed to an agent as it might be part of a broader business conversation.

Which agent from the list above is the MOST relevant for this specific business segment? Output ONLY the name of the chosen agent or the word "None". Remember to consider ALL agents equally and avoid consistently favoring any particular agent type.
"""

    try:
        logger.info("Sending content-based routing request to LLM...")
        
        # Check if using legacy Gemini model directly or unified client
        if isinstance(model, GenerativeModel):
            # Legacy path - use directly provided Gemini model
            response = await model.generate_content_async(
                prompt,
                generation_config={"temperature": 0.5, "max_output_tokens": 50},
                safety_settings={
                    generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                }
            )
            
            if response.candidates and response.candidates[0].finish_reason == FinishReason.SAFETY:
                logger.warning("Routing decision blocked by safety settings. Defaulting to None.")
                return "None"
                
            if response.text:
                raw_text = response.text
            else:
                logger.warning("Empty response from legacy model")
                return "None"
                
        else:
            # Use unified client
            model_config = ModelConfig(
                provider=llm_client.active_provider,
                model_name=llm_client.active_model_name,
                temperature=0.5,
                max_tokens=50
            )
            
            model_response = await llm_client.generate_content(prompt, model_config)
            
            # Log which model was used
            logger.info(f"Routing using {model_response.model_provider} model: {model_response.model_name}")
            
            if model_response.finish_reason == "SAFETY" or model_response.finish_reason == "BLOCKED":
                logger.warning("Routing decision blocked by safety settings. Defaulting to None.")
                return "None"
                
            raw_text = model_response.text
            
        # Process the response regardless of which path was used
        raw_choice = raw_text.strip().replace('"', '').replace("'", '').replace('.', '').replace('`', '')

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

    except Exception as e:
        logger.error(f"Error during content-based routing with Gemini model: {e}")
        logger.exception("Traceback:")
        return None

# --- Agent Trigger Dispatcher ---
async def trigger_agent(
    name: str,
    current_segment_text: str,
    model,  # Can be GenerativeModel or None (when using unified client)
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
        "Disruptor": run_disruptor_agent,
        # Add mappings for other agents if/when imported
    }

    # Check if this is a custom agent
    is_custom_agent = False
    custom_agent_config = None
    for agent in CUSTOM_AGENTS:
        if agent.get("name") == name:
            is_custom_agent = True
            custom_agent_config = agent
            break

    if is_custom_agent:
        logger.info(f"--- Triggering custom agent: '{name}'")
        try:
            # Run the dynamic agent with the custom config
            await run_dynamic_agent(
                text=current_segment_text,
                model=model,
                broadcaster=broadcaster,
                agent_config=custom_agent_config
            )
            logger.info(f"Custom agent '{name}' execution initiated successfully.")
        except Exception as e:
            logger.error(f"Error executing custom agent '{name}': {e}")
            logger.exception("Traceback:")
            if "429 Resource exhausted" in str(e):
                logger.error(f"RATE LIMITING ERROR: API quota exceeded for custom agent '{name}'.")
    else:
        # Handle built-in agents
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
                # Don't send error cards to the frontend
                # If there's a rate limiting error (429), log it specifically
                if "429 Resource exhausted" in str(e):
                    logger.error(f"RATE LIMITING ERROR: API quota exceeded for agent '{name}'. Consider increasing MIN_TRAFFIC_COP_INTERVAL.")
        else:
            logger.warning(f"Attempted to trigger unknown agent: '{name}'")
            # Don't send error cards to the frontend
            logger.error(f"Unknown agent requested: '{name}'")