# Deployment Instructions

## Prerequisites
1. Ensure you have the Google Cloud SDK installed and configured
2. Ensure you have the Firebase CLI installed and configured
3. Make sure you have the necessary API keys:
   - Google Cloud API key for Gemini
   - Anthropic API key for Claude

## Pre-Deployment Checks
1. Make sure all code is working properly:
   - Fixed indentation issues in `traffic_cop.py`
   - All imports work correctly
   - Test the application locally if possible

## Environment Setup
1. Update the `.env` file with your actual API keys:
   ```
   # Replace the placeholder with your actual Anthropic API key
   ANTHROPIC_API_KEY=your_actual_anthropic_api_key_here
   ```

2. Choose your default LLM provider (gemini or claude):
   ```
   DEFAULT_LLM_PROVIDER=gemini
   ```

## Backend Deployment
Deploy the backend to Google Cloud Run:

```bash
cd backend
gcloud run deploy backend \
    --source . \
    --platform managed \
    --region us-east1 \
    --allow-unauthenticated \
    --project=meetinganalyzer-454912
```

## Frontend Deployment
Deploy the frontend to Firebase:

```bash
cd frontend
firebase deploy --only hosting
```

## Verifying Deployment
1. After deployment, your application should be available at the Firebase hosting URL
2. Verify that both LLM providers (Gemini and Claude) are working correctly
3. Test the model switching functionality in the UI
4. Test per-agent model preferences