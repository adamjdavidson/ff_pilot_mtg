"""
Agent versioning system for the AI Meeting Assistant.
Allows creating and managing multiple versions of agents without modifying the original code.
"""
import os
import json
import logging
import time
from utils import extract_agent_prompt

# Get the logger instance configured in main.py
logger = logging.getLogger("main")

# File to store agent versions
AGENT_VERSIONS_FILE = os.path.join(os.path.dirname(__file__), 'agent_versions.json')

# Initialize agent versions with empty data if file doesn't exist
if not os.path.exists(AGENT_VERSIONS_FILE):
    with open(AGENT_VERSIONS_FILE, 'w') as f:
        json.dump({}, f)
        logger.info(f"Created empty agent versions file at {AGENT_VERSIONS_FILE}")

# Load agent versions from file
def load_agent_versions():
    """Load all agent versions from the JSON file."""
    try:
        with open(AGENT_VERSIONS_FILE, 'r') as f:
            versions = json.load(f)
            logger.info(f"Loaded agent versions from {AGENT_VERSIONS_FILE}")
            return versions
    except Exception as e:
        logger.error(f"Error loading agent versions: {e}")
        return {}

# Save agent versions to file
def save_agent_versions(versions):
    """Save agent versions to the JSON file."""
    try:
        with open(AGENT_VERSIONS_FILE, 'w') as f:
            json.dump(versions, f, indent=2)
        logger.info(f"Saved agent versions to {AGENT_VERSIONS_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error saving agent versions: {e}")
        return False

# Get all versions of a specific agent
def get_agent_versions(agent_name):
    """Get all versions of a specific agent."""
    versions = load_agent_versions()
    if agent_name in versions:
        return versions[agent_name]
    return []

# Get the latest version of a specific agent
def get_latest_agent_version(agent_name):
    """Get the latest version of a specific agent."""
    versions = get_agent_versions(agent_name)
    if versions:
        # Sort by timestamp (descending) and get the first one
        sorted_versions = sorted(versions, key=lambda x: x.get('timestamp', 0), reverse=True)
        return sorted_versions[0]
    return None

# Create a new version of an agent
def create_agent_version(agent_name, prompt_text, version_name, description=""):
    """Create a new version of an agent."""
    versions = load_agent_versions()
    
    # Initialize agent entry if it doesn't exist
    if agent_name not in versions:
        versions[agent_name] = []
    
    # Create new version object
    version = {
        "version_name": version_name,
        "prompt_text": prompt_text,
        "timestamp": int(time.time()),
        "description": description
    }
    
    # Add to versions list
    versions[agent_name].append(version)
    
    # Save updated versions
    if save_agent_versions(versions):
        return {"success": True, "version": version}
    else:
        return {"error": "Failed to save agent version"}

# Delete a specific version of an agent
def delete_agent_version(agent_name, version_name):
    """Delete a specific version of an agent."""
    versions = load_agent_versions()
    
    if agent_name not in versions:
        return {"error": f"Agent {agent_name} not found"}
    
    # Find version by name
    for i, version in enumerate(versions[agent_name]):
        if version.get("version_name") == version_name:
            versions[agent_name].pop(i)
            
            # Save updated versions
            if save_agent_versions(versions):
                return {"success": True, "message": f"Deleted version {version_name} of {agent_name}"}
            else:
                return {"error": "Failed to save after deletion"}
    
    return {"error": f"Version {version_name} not found for {agent_name}"}

# Extract the original prompt for an agent
def extract_original_agent_prompt(agent_name):
    """Extract the original prompt for an agent."""
    result = extract_agent_prompt(agent_name)
    if "error" in result:
        return result
    
    return {
        "success": True,
        "agent_name": agent_name,
        "prompt_text": result["prompt_text"],
        "is_original": True
    }