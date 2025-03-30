#!/bin/bash
set -e

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting deployment process...${NC}"

# Check for Anthropic API key in .env file
if grep -q "ANTHROPIC_API_KEY=your_anthropic_api_key_here" ./backend/.env || grep -q "ANTHROPIC_API_KEY=your_actual_anthropic_api_key_here" ./backend/.env; then
  echo -e "${RED}ERROR: Anthropic API key not configured in .env file!${NC}"
  echo -e "${YELLOW}Please update the ANTHROPIC_API_KEY in ./backend/.env before deploying.${NC}"
  exit 1
fi

# Install backend dependencies
echo -e "${YELLOW}Installing backend dependencies...${NC}"
cd backend
pip install -r requirements.txt
echo -e "${GREEN}Backend dependencies installed successfully.${NC}"

# Deploy backend to Google Cloud Run
echo -e "${YELLOW}Deploying backend to Google Cloud Run...${NC}"
gcloud run deploy backend \
    --source . \
    --platform managed \
    --region us-east1 \
    --allow-unauthenticated \
    --project=meetinganalyzer-454912

echo -e "${GREEN}Backend deployed successfully.${NC}"

# Deploy frontend to Firebase
echo -e "${YELLOW}Deploying frontend to Firebase...${NC}"
cd ../frontend
firebase deploy --only hosting

echo -e "${GREEN}Frontend deployed successfully.${NC}"
echo -e "${GREEN}Deployment complete! Your AI Meeting Assistant with Claude 3.7 integration is now live.${NC}"