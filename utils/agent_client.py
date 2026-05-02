import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

def send_message(user_message: str, chat_id: str = "default"):
    """Send a message to the n8n workflow"""
    if not N8N_WEBHOOK_URL:
        raise ValueError("N8N_WEBHOOK_URL is not set in environment variables. Please set it in your .env file or environment variables.")

    payload = {
        "message": user_message,
        "sessionId": chat_id,
        "chatId": chat_id
    }
    
    try:
        resp = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=120)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. The workflow may be taking longer than expected."}
    except requests.exceptions.ConnectionError:
        return {"error": f"Failed to connect to n8n workflow at {N8N_WEBHOOK_URL}. Please check if n8n is running and the webhook URL is correct."}
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP error {e.response.status_code}"
        try:
            error_data = e.response.json()
            if "message" in error_data:
                error_msg += f": {error_data['message']}"
                if "hint" in error_data:
                    error_msg += f"\n💡 Hint: {error_data['hint']}"
            else:
                error_msg += f": {e.response.text}"
        except:
            error_msg += f": {e.response.text}"
        
        # Provide specific guidance for 404 errors
        if e.response.status_code == 404:
            error_msg += "\n\n🔧 Troubleshooting:\n"
            error_msg += "1. Make sure the workflow is ACTIVE (toggle in top-right of n8n editor)\n"
            error_msg += "2. Check that N8N_WEBHOOK_URL is correct:\n"
            error_msg += "   - Should be: http://localhost:5678/webhook/orchestrator-agent\n"
            error_msg += "   - Or if using Docker: http://host.docker.internal:5678/webhook/orchestrator-agent\n"
            error_msg += "3. Try using the webhook ID instead: http://localhost:5678/webhook/f1c2a252-37d2-40f0-a960-5d1656dddc39"
        
        return {"error": error_msg}
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to connect to agent: {str(e)}"}

    try:
        data = resp.json()
        return data
    except ValueError:
        return {"error": "Invalid JSON response from agent"}
