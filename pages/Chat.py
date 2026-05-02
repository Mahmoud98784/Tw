import streamlit as st
from utils.agent_client import send_message
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import threading
import uvicorn
import json
import os
import zipfile
import io
import time
import uuid
import socket
import asyncio
import traceback
from datetime import datetime

CHAT_FILE = "chat_history.json"
CHATS_DIR = "chats"

# Phase definitions matching the workflow
PHASES = [
    {"id": "planning", "name": "Planning", "icon": "🤔", "status": "pending"},
    {"id": "analysis", "name": "Analysis", "icon": "🔍", "status": "pending"},
    {"id": "design", "name": "Design", "icon": "📐", "status": "pending"},
    {"id": "development", "name": "Development", "icon": "⚙️", "status": "pending"},
    {"id": "testing", "name": "Testing", "icon": "🧪", "status": "pending"},
    {"id": "deployment", "name": "Deployment", "icon": "🚀", "status": "pending"}
]

# Ensure chats directory exists
os.makedirs(CHATS_DIR, exist_ok=True)

def get_chat_file(chat_id):
    """Get the file path for a specific chat"""
    return os.path.join(CHATS_DIR, f"{chat_id}.json")

def load_chat(chat_id=None):
    """Load chat history for a specific chat or default chat"""
    if chat_id is None:
        chat_id = st.session_state.get("current_chat_id", "default")
    
    chat_file = get_chat_file(chat_id)
    try:
        if os.path.exists(chat_file):
            with open(chat_file, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        st.error(f"Error loading chat history: {e}")
    return []

def save_chat(history, chat_id=None):
    """Save chat history for a specific chat"""
    if chat_id is None:
        chat_id = st.session_state.get("current_chat_id", "default")
    
    chat_file = get_chat_file(chat_id)
    try:
        with open(chat_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except IOError as e:
        st.error(f"Error saving chat history: {e}")

def get_all_chats():
    """Get list of all chat IDs and their metadata"""
    chats = []
    if os.path.exists(CHATS_DIR):
        for filename in os.listdir(CHATS_DIR):
            if filename.endswith(".json"):
                chat_id = filename[:-5]  # Remove .json extension
                chat_file = get_chat_file(chat_id)
                try:
                    with open(chat_file, "r", encoding="utf-8") as f:
                        chat_data = json.load(f)
                        # Get first user message as title
                        title = "New Chat"
                        for role, msg in chat_data:
                            if role == "User" and isinstance(msg, str):
                                title = msg[:50] + "..." if len(msg) > 50 else msg
                                break
                        # Get last message time
                        last_modified = os.path.getmtime(chat_file)
                        chats.append({
                            "id": chat_id,
                            "title": title,
                            "last_modified": last_modified,
                            "message_count": len(chat_data)
                        })
                except Exception:
                    continue
    # Sort by last modified (newest first)
    chats.sort(key=lambda x: x["last_modified"], reverse=True)
    return chats

def delete_chat(chat_id):
    """Delete a chat file"""
    chat_file = get_chat_file(chat_id)
    try:
        if os.path.exists(chat_file):
            os.remove(chat_file)
            return True
    except Exception as e:
        st.error(f"Error deleting chat: {e}")
    return False

def create_new_chat():
    """Create a new chat and return its ID"""
    chat_id = str(uuid.uuid4())
    st.session_state.current_chat_id = chat_id
    st.session_state.chat_history = []
    save_chat([], chat_id)
    return chat_id

# -----------------------
# FastAPI setup with better port management
# -----------------------
app = FastAPI()
_server_running = False
_server_lock = threading.Lock()

@app.post("/webhook/agent-response")
async def agent_response(request: Request):
    data = await request.json()
    
    # Extract data from request - workflow sends: phase, chatInput, sessionId, chatId
    phase = data.get("phase")  # Phase identifier from workflow
    chat_id = data.get("chatId") or data.get("sessionId", "default")  # Get chatId from request, not session state
    session_id = data.get("sessionId", "default-session")
    
    # Get the agent's output - workflow sends it as "chatInput" for phase updates, "response" for final
    response = data.get("chatInput") or data.get("response") or data.get("output", "")
    
    # Try to parse response as JSON if it's a string
    if isinstance(response, str) and response.strip():
        try:
            parsed_response = json.loads(response)
            if isinstance(parsed_response, dict):
                response = parsed_response
        except (json.JSONDecodeError, ValueError):
            pass  # Keep as string if not valid JSON
    
    # Load chat history for this specific chat
    chat_file = get_chat_file(chat_id)
    try:
        if os.path.exists(chat_file):
            with open(chat_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        else:
            history = []
    except (json.JSONDecodeError, IOError):
        history = []
    
    # If phase is provided, update that specific phase placeholder
    if phase:
        # Find and update the phase placeholder (search from end to find the most recent)
        updated = False
        for i in range(len(history) - 1, -1, -1):
            role, msg = history[i]
            if role == "Twin" and isinstance(msg, dict) and msg.get("type") == "phase_status":
                if msg.get("phase") == phase:
                    # Replace the placeholder with the completed phase
                    history[i] = ("Twin", {
                        "type": "phase_complete",
                        "phase": phase,
                        "content": response,
                        "timestamp": datetime.now().isoformat()
                    })
                    updated = True
                    break
        
        # If not found, append new phase completion
        if not updated:
            history.append(("Twin", {
                "type": "phase_complete",
                "phase": phase,
                "content": response,
                "timestamp": datetime.now().isoformat()
            }))
    else:
        # No phase specified - this is the final response from the Format Final Response node
        # Remove all phase placeholders and add final response
        history = [h for h in history if not (
            h[0] == "Twin" and isinstance(h[1], dict) and h[1].get("type") == "phase_status"
        )]
        
        # Add the final response
        history.append(("Twin", response))
    
    # Save updated history
    try:
        with open(chat_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except IOError:
        pass  # Log error but don't crash
    
    return JSONResponse(content={"status": "agent response received", "phase": phase, "chatId": chat_id})

def run_fastapi():
    """Run FastAPI server in a daemon thread"""
    global _server_running
    print("[FastAPI] [run_fastapi] Function called", flush=True)
    try:
        print("[FastAPI] [run_fastapi] Creating uvicorn config...", flush=True)
        
        # Configure uvicorn
        config = uvicorn.Config(
            app, 
            host="0.0.0.0", 
            port=8503, 
            log_level="critical",
            access_log=False,
            lifespan="off"
        )
        print("[FastAPI] [run_fastapi] Creating uvicorn server...", flush=True)
        server = uvicorn.Server(config)
        
        # Run server (blocks this thread, but that's OK since it's a daemon)
        print("[FastAPI] [run_fastapi] Starting server.run()...", flush=True)
        server.run()
        
    except Exception as e:
        print(f"[FastAPI] [run_fastapi] Error: {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()

# Start FastAPI server ONLY ONCE when script runs
@st.cache_resource
def start_fastapi_server():
    """Start FastAPI server in background thread"""
    print("[FastAPI] start_fastapi_server called", flush=True)
    try:
        # Start in daemon thread so it runs in background
        print("[FastAPI] Starting daemon thread...", flush=True)
        thread = threading.Thread(target=run_fastapi, daemon=True)
        thread.start()
        
        # Wait for server to initialize
        print("[FastAPI] Waiting for server initialization...", flush=True)
        time.sleep(2)
        
        print("[FastAPI] Server startup complete!", flush=True)
        return True
    except Exception as e:
        print(f"[FastAPI] Startup failed: {e}", flush=True)
        traceback.print_exc()
        return False

# Initialize server on module load (before page config)
print("[FastAPI] Initializing FastAPI server...", flush=True)
start_fastapi_server()
print("[FastAPI] Initialization done", flush=True)

# -----------------------
# Streamlit UI
# -----------------------
st.set_page_config(page_title="Chat with AI Twin", layout="wide", page_icon="🤖")

# Enhanced CSS styling
st.markdown("""
    <style>
    /* Main container */
    .main {
        padding: 2rem;
    }
    
    /* Chat message styling */
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .twin-message {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 5px solid #667eea;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Phase status cards */
    .phase-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border: 2px solid #e0e0e0;
        transition: all 0.3s ease;
    }
    
    .phase-card.active {
        border-color: #667eea;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        animation: pulse 2s infinite;
    }
    
    .phase-card.completed {
        border-color: #4caf50;
        background: #f1f8f4;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.8; }
    }
    
    /* Chat list item */
    .chat-item {
        padding: 0.75rem;
        border-radius: 8px;
        margin: 0.25rem 0;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .chat-item:hover {
        background: rgba(102, 126, 234, 0.1);
    }
    
    .chat-item.active {
        background: rgba(102, 126, 234, 0.2);
        border-left: 3px solid #667eea;
    }
    
    /* Buttons */
    .stButton>button {
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    </style>
""", unsafe_allow_html=True)

# Migrate old chat_history.json to new structure if it exists
if os.path.exists("chat_history.json") and not os.path.exists(get_chat_file("default")):
    try:
        with open("chat_history.json", "r", encoding="utf-8") as f:
            old_history = json.load(f)
        if old_history:  # Only migrate if there's content
            save_chat(old_history, "default")
            # Optionally backup the old file
            os.rename("chat_history.json", "chat_history.json.backup")
    except Exception:
        pass  # If migration fails, just continue

# Initialize session state
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = "default"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_chat()

if "current_phase_index" not in st.session_state:
    st.session_state.current_phase_index = -1

if "phase_statuses" not in st.session_state:
    st.session_state.phase_statuses = {phase["id"]: "pending" for phase in PHASES}

# Track last file modification time to detect updates
if "last_chat_mtime" not in st.session_state:
    chat_file = get_chat_file(st.session_state.current_chat_id)
    st.session_state.last_chat_mtime = os.path.getmtime(chat_file) if os.path.exists(chat_file) else 0

# Reload chat history if file has been modified (by FastAPI webhook)
chat_file = get_chat_file(st.session_state.current_chat_id)
if os.path.exists(chat_file):
    current_mtime = os.path.getmtime(chat_file)
    if current_mtime > st.session_state.last_chat_mtime:
        # File was updated, reload chat history
        st.session_state.chat_history = load_chat()
        st.session_state.last_chat_mtime = current_mtime

# Sidebar with chat list
with st.sidebar:
    st.markdown("### 💬 Chat Management")
    
    # New Chat button
    if st.button("➕ New Chat", width='stretch', type="primary"):
        create_new_chat()
        st.rerun()
    
    st.markdown("---")
    
    # Chat list
    st.markdown("### 📋 Your Chats")
    all_chats = get_all_chats()
    
    if not all_chats:
        st.info("No chats yet. Start a new chat!")
    else:
        for chat in all_chats:
            chat_id = chat["id"]
            is_active = chat_id == st.session_state.current_chat_id
            
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(
                    chat["title"],
                    key=f"chat_{chat_id}",
                    width='stretch',
                    type="primary" if is_active else "secondary"
                ):
                    st.session_state.current_chat_id = chat_id
                    st.session_state.chat_history = load_chat(chat_id)
                    # Reset file modification tracking
                    chat_file = get_chat_file(chat_id)
                    st.session_state.last_chat_mtime = os.path.getmtime(chat_file) if os.path.exists(chat_file) else 0
                    st.rerun()
            
            with col2:
                if st.button("🗑️", key=f"del_{chat_id}", help="Delete chat"):
                    if delete_chat(chat_id):
                        if chat_id == st.session_state.current_chat_id:
                            # Switch to default chat if current chat was deleted
                            st.session_state.current_chat_id = "default"
                            st.session_state.chat_history = load_chat()
                        st.rerun()

# Main content area
st.title("💬 Chat with the Digital Twin")

# Show webhook URL status if configured
from utils.agent_client import N8N_WEBHOOK_URL
if N8N_WEBHOOK_URL:
    with st.expander("🔗 Webhook Configuration", expanded=False):
        st.success(f"✅ Webhook URL: `{N8N_WEBHOOK_URL}`")
        st.caption("If you see 404 errors, make sure the workflow is ACTIVE in n8n")
else:
    st.warning("⚠️ N8N_WEBHOOK_URL is not set. Please configure it in your .env file.")

# Clear chat button
col1, col2 = st.columns([10, 1])
with col2:
    if st.button("🗑️ Clear", help="Clear current chat"):
        st.session_state.chat_history = []
        save_chat([], st.session_state.current_chat_id)
        st.rerun()

st.markdown("---")

# Input section
with st.container():
    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_area(
            "Enter your message:",
            height=100,
            placeholder="Describe what you want to build...",
            key="user_input"
        )
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        send_button = st.button("🚀 Send", type="primary", width='stretch')

if send_button:
    if user_input.strip():
        # Add user message
        st.session_state.chat_history.append(("User", user_input))
        save_chat(st.session_state.chat_history)
        
        # Reset phase tracking
        st.session_state.current_phase_index = 0
        st.session_state.phase_statuses = {phase["id"]: "pending" for phase in PHASES}
        
        # Add phase status placeholders
        for phase in PHASES:
            st.session_state.chat_history.append(("Twin", {
                "type": "phase_status",
                "phase": phase["id"],
                "name": phase["name"],
                "icon": phase["icon"],
                "status": "processing"
            }))
        save_chat(st.session_state.chat_history)
        
        # Trigger orchestrator
        try:
            result = send_message(user_input, st.session_state.current_chat_id)
            if result and "error" in result:
                st.error(f"❌ Error: {result['error']}")
                # Remove phase placeholders on error
                st.session_state.chat_history = [
                    h for h in st.session_state.chat_history 
                    if not (h[0] == "Twin" and isinstance(h[1], dict) and h[1].get("type") == "phase_status")
                ]
                st.session_state.chat_history.append(("Twin", f"❌ Failed to send message: {result['error']}"))
                save_chat(st.session_state.chat_history)
            else:
                st.success("✅ Message sent successfully! Waiting for response...")
        except ValueError as e:
            st.error(f"❌ Configuration Error: {str(e)}")
            st.info("💡 Please set N8N_WEBHOOK_URL in your environment variables or .env file")
            # Remove phase placeholders on error
            st.session_state.chat_history = [
                h for h in st.session_state.chat_history 
                if not (h[0] == "Twin" and isinstance(h[1], dict) and h[1].get("type") == "phase_status")
            ]
            st.session_state.chat_history.append(("Twin", f"❌ Configuration error: {str(e)}"))
            save_chat(st.session_state.chat_history)
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
            # Remove phase placeholders on error
            st.session_state.chat_history = [
                h for h in st.session_state.chat_history 
                if not (h[0] == "Twin" and isinstance(h[1], dict) and h[1].get("type") == "phase_status")
            ]
            st.session_state.chat_history.append(("Twin", f"❌ Error: {str(e)}"))
            save_chat(st.session_state.chat_history)
        else:
            st.rerun()

# -----------------------
# Display chat history with enhanced UI
# -----------------------
chat_container = st.container()

with chat_container:
    completed_phases = 0
    total_phases = len(PHASES)
    
    for idx, (role, msg) in enumerate(st.session_state.chat_history):
        if role == "User":
            st.markdown(f"""
                <div class="user-message">
                    <strong>🧑 You:</strong><br>
                    {msg}
                </div>
            """, unsafe_allow_html=True)
        
        elif role == "Twin":
            # Handle phase status (processing)
            if isinstance(msg, dict) and msg.get("type") == "phase_status":
                phase_id = msg.get("phase")
                phase_name = msg.get("name", phase_id.capitalize())
                phase_icon = msg.get("icon", "⏳")
                
                st.markdown(f"""
                    <div class="phase-card active">
                        <div style="display: flex; align-items: center; gap: 1rem;">
                            <span style="font-size: 2rem;">{phase_icon}</span>
                            <div style="flex: 1;">
                                <h4 style="margin: 0; color: #667eea;">{phase_name}...</h4>
                                <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 0.9rem;">
                                    Processing your request...
                                </p>
                            </div>
                            <div class="spinner" style="border: 3px solid #f3f3f3; border-top: 3px solid #667eea; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite;"></div>
                        </div>
                    </div>
                    <style>
                    @keyframes spin {{
                        0% {{ transform: rotate(0deg); }}
                        100% {{ transform: rotate(360deg); }}
                    }}
                    </style>
                """, unsafe_allow_html=True)
            
            # Handle phase completion
            elif isinstance(msg, dict) and msg.get("type") == "phase_complete":
                phase_id = msg.get("phase")
                content = msg.get("content", "")
                phase_info = next((p for p in PHASES if p["id"] == phase_id), None)
                
                if phase_info:
                    completed_phases += 1
                    
                    # Handle development phase
                    if phase_id == "development" and isinstance(content, dict):
                        with st.expander(f"{phase_info['icon']} ✓ {phase_info['name']} Complete", expanded=True):
                            # Check for new simplified schema first
                            if "summary" in content and "details" in content:
                                # New schema: summary + details
                                if "original_request" in content:
                                    st.write("**📋 Original Request:**")
                                    st.write(content["original_request"])
                                    st.divider()
                                
                                st.write("**Summary:**")
                                st.markdown(content["summary"])
                                st.divider()
                                
                                st.write("**Details:**")
                                st.markdown(content["details"])
                                
                                # For Development phase: Check for files to create ZIP download
                                # First check if there's a separate 'files' key at the same level
                                files_list = None
                                if "files" in content and isinstance(content["files"], list):
                                    files_list = content["files"]
                                # Otherwise, try to parse files from details string if it contains JSON
                                elif isinstance(content.get("details"), str):
                                    details_str = content["details"]
                                    try:
                                        # Try to parse details as JSON if it contains file structure
                                        if "files" in details_str.lower() or "filename" in details_str.lower():
                                            import re
                                            # Look for JSON-like structure in details
                                            json_match = re.search(r'\{.*"files".*\}', details_str, re.DOTALL)
                                            if json_match:
                                                details_dict = json.loads(json_match.group())
                                                if "files" in details_dict and isinstance(details_dict["files"], list):
                                                    files_list = details_dict["files"]
                                    except:
                                        pass  # If parsing fails, continue without ZIP
                                
                                # Create ZIP download if files were found
                                if files_list:
                                    zip_buffer_dev = io.BytesIO()
                                    with zipfile.ZipFile(zip_buffer_dev, "w", zipfile.ZIP_DEFLATED) as zipf:
                                        for file_info in files_list:
                                            filename = file_info.get("filename", "unknown")
                                            file_content = file_info.get("code", file_info.get("content", ""))
                                            extension = file_info.get("extension_of_file", "txt")
                                            full_filename = f"{filename}.{extension}" if not filename.endswith(f".{extension}") else filename
                                            zipf.writestr(full_filename, file_content)
                                    zip_buffer_dev.seek(0)
                                    st.download_button(
                                        label="📦 Download All Generated Files as ZIP",
                                        data=zip_buffer_dev,
                                        file_name="generated_code.zip",
                                        mime="application/zip",
                                        key=f"dev_zip_{idx}"
                                    )
                                
                                if "next_agent_instructions" in content:
                                    st.divider()
                                    st.write("**Next Agent Instructions:**")
                                    st.info(content["next_agent_instructions"])
                            
                            # Fall back to old schema (backward compatibility)
                            elif "files" in content:
                                # Display description of work
                                if "description_of_work" in content:
                                    st.write("**Work Completed:**")
                                    st.write(content["description_of_work"])
                                
                                # Create and provide ZIP file download
                                if "files" in content and isinstance(content["files"], list):
                                    zip_buffer_dev = io.BytesIO()
                                    with zipfile.ZipFile(zip_buffer_dev, "w", zipfile.ZIP_DEFLATED) as zipf:
                                        for file_info in content["files"]:
                                            filename = file_info.get("filename", "unknown")
                                            file_content = file_info.get("code", file_info.get("content", ""))
                                            extension = file_info.get("extension_of_file", "txt")
                                            
                                            # Create full filename with extension
                                            full_filename = f"{filename}.{extension}" if not filename.endswith(f".{extension}") else filename
                                            zipf.writestr(full_filename, file_content)
                                    
                                    zip_buffer_dev.seek(0)
                                    st.download_button(
                                        label="📦 Download All Generated Files as ZIP",
                                        data=zip_buffer_dev,
                                        file_name="generated_code.zip",
                                        mime="application/zip",
                                        key=f"dev_zip_{idx}"
                                    )
                    
                    # Handle deployment phase (final output)
                    elif phase_id == "deployment" and isinstance(content, dict):
                        # Unwrap content if it's wrapped in 'output' or 'result' keys
                        deployment_content = content
                        if "output" in content and isinstance(content["output"], dict):
                            deployment_content = content["output"]
                        elif "result" in content and isinstance(content["result"], dict):
                            deployment_content = content["result"]
                        
                        with st.expander(f"{phase_info['icon']} ✓ {phase_info['name']} Complete", expanded=True):
                            # Check for new simplified schema first
                            if "summary" in deployment_content and "details" in deployment_content:
                                # New schema: summary + details
                                if "original_request" in deployment_content:
                                    st.write("**📋 Original Request:**")
                                    st.write(deployment_content["original_request"])
                                    st.divider()
                                
                                st.write("**Summary:**")
                                st.markdown(deployment_content["summary"])
                                st.divider()
                                
                                st.write("**Details:**")
                                st.markdown(deployment_content["details"])
                                
                                if "next_agent_instructions" in deployment_content:
                                    st.divider()
                                    st.write("**Next Agent Instructions:**")
                                    st.info(deployment_content["next_agent_instructions"])
                            
                            # Fall back to old structured schema (backward compatibility)
                            else:
                                # Display key deployment information in an organized way
                                
                                # 1. Original Request Context
                                if "original_request" in deployment_content:
                                    st.write("**📋 Original Request:**")
                                    st.write(deployment_content["original_request"])
                                    st.divider()
                                
                                # 2. Testing Summary
                                if "testing_summary" in deployment_content:
                                    st.write("**✅ Testing Summary:**")
                                    st.write(deployment_content["testing_summary"])
                                    st.divider()
                                
                                # 3. Deployment Strategy
                                if "deployment_strategy" in deployment_content:
                                    st.write("**🚀 Deployment Strategy:**")
                                    strategy = deployment_content["deployment_strategy"]
                                    if isinstance(strategy, dict):
                                        if "approach" in strategy:
                                            st.write(f"**Approach:** {strategy['approach']}")
                                        if "reasoning" in strategy:
                                            st.write(f"**Reasoning:** {strategy['reasoning']}")
                                        if "rollback_plan" in strategy:
                                            st.write(f"**Rollback Plan:** {strategy['rollback_plan']}")
                                    st.divider()
                                
                                # 4. Infrastructure Requirements Summary
                                if "infrastructure_requirements" in deployment_content:
                                    st.write("**🏗️ Infrastructure Requirements:**")
                                    infra = deployment_content["infrastructure_requirements"]
                                    if isinstance(infra, dict):
                                        if "hosting" in infra and isinstance(infra["hosting"], dict):
                                            hosting = infra["hosting"]
                                            st.write(f"**Platform:** {hosting.get('platform', 'N/A')}")
                                            if "estimated_cost" in hosting:
                                                st.write(f"**Estimated Cost:** {hosting['estimated_cost']}")
                                        if "services" in infra and isinstance(infra["services"], list):
                                            st.write("**Services:**")
                                            for service in infra["services"]:
                                                if isinstance(service, dict):
                                                    st.write(f"- **{service.get('service', 'Service')}**: {service.get('purpose', '')}")
                                    st.divider()
                                
                                # 5. CI/CD Pipeline Overview
                                if "ci_cd_pipeline" in deployment_content:
                                    st.write("**🔄 CI/CD Pipeline:**")
                                    pipeline = deployment_content["ci_cd_pipeline"]
                                    if isinstance(pipeline, dict):
                                        if "tool" in pipeline:
                                            st.write(f"**Tool:** {pipeline['tool']}")
                                        if "stages" in pipeline and isinstance(pipeline["stages"], list):
                                            st.write("**Stages:**")
                                            for stage in pipeline["stages"]:
                                                if isinstance(stage, dict):
                                                    stage_name = stage.get('stage', 'Stage')
                                                    st.write(f"- {stage_name}")
                                                    if "steps" in stage and isinstance(stage["steps"], list):
                                                        for step in stage["steps"][:3]:  # Show first 3 steps
                                                            st.write(f"  • {step}")
                                                    if len(stage.get("steps", [])) > 3:
                                                        st.write(f"  • ... and {len(stage['steps']) - 3} more steps")
                                    st.divider()
                                
                                # 6. Deployment Steps
                                if "deployment_steps" in deployment_content and isinstance(deployment_content["deployment_steps"], list):
                                    st.write("**📝 Deployment Steps:**")
                                    for step in deployment_content["deployment_steps"]:
                                        if isinstance(step, dict):
                                            step_num = step.get('step_number', '?')
                                            action = step.get('action', 'N/A')
                                            st.write(f"**Step {step_num}:** {action}")
                                            if "verification" in step:
                                                st.write(f"  *Verification:* {step['verification']}")
                                    st.divider()
                                
                                # 7. Monitoring Overview
                                if "monitoring_and_observability" in deployment_content:
                                    st.write("**📊 Monitoring & Observability:**")
                                    monitoring = deployment_content["monitoring_and_observability"]
                                    if isinstance(monitoring, dict):
                                        if "logging" in monitoring and isinstance(monitoring["logging"], dict):
                                            st.write(f"**Logging Tool:** {monitoring['logging'].get('tool', 'N/A')}")
                                        if "metrics" in monitoring and isinstance(monitoring["metrics"], list):
                                            st.write("**Key Metrics:**")
                                            for metric in monitoring["metrics"][:5]:  # Show first 5 metrics
                                                if isinstance(metric, dict):
                                                    st.write(f"- {metric.get('metric', 'Metric')}: {metric.get('threshold', 'N/A')}")
                                            if len(monitoring["metrics"]) > 5:
                                                st.write(f"- ... and {len(monitoring['metrics']) - 5} more metrics")
                                        if "alerts" in monitoring and isinstance(monitoring["alerts"], list):
                                            st.write("**Critical Alerts:**")
                                            for alert in monitoring["alerts"][:3]:  # Show first 3 alerts
                                                if isinstance(alert, dict):
                                                    st.write(f"- **{alert.get('severity', 'Alert')}**: {alert.get('condition', 'N/A')}")
                                    st.divider()
                                
                                # 8. Security Measures
                                if "security_measures" in deployment_content:
                                    st.write("**🔒 Security Measures:**")
                                    security = deployment_content["security_measures"]
                                    if isinstance(security, dict):
                                        if "ssl_certificates" in security:
                                            st.write(f"**SSL/TLS:** {security['ssl_certificates']}")
                                        if "secrets_management" in security:
                                            st.write(f"**Secrets Management:** {security['secrets_management']}")
                                        if "access_control" in security and isinstance(security["access_control"], list):
                                            st.write("**Access Control:**")
                                            for control in security["access_control"][:3]:
                                                st.write(f"- {control}")
                                    st.divider()
                                
                                # 9. Disaster Recovery
                                if "disaster_recovery" in deployment_content:
                                    st.write("**🔄 Disaster Recovery:**")
                                    dr = deployment_content["disaster_recovery"]
                                    if isinstance(dr, dict):
                                        if "backup_strategy" in dr:
                                            st.write(f"**Backup Strategy:** {dr['backup_strategy']}")
                                        if "recovery_time_objective" in dr:
                                            st.write(f"**RTO:** {dr['recovery_time_objective']}")
                                        if "recovery_point_objective" in dr:
                                            st.write(f"**RPO:** {dr['recovery_point_objective']}")
                                    st.divider()
                                
                                # 10. Final Summary
                                if "final_summary" in deployment_content:
                                    st.write("**📌 Final Summary:**")
                                    st.write(deployment_content["final_summary"])
                                
                                # If no specific content found, display full JSON
                                if not any(key in deployment_content for key in ["original_request", "deployment_strategy", "infrastructure_requirements"]):
                                    st.write("**Deployment Configuration:**")
                                    st.json(deployment_content)
                    
                    # Handle other phases (planning, analysis, design, testing)
                    else:
                        with st.expander(f"{phase_info['icon']} ✓ {phase_info['name']} Complete", expanded=True):
                            if isinstance(content, str):
                                if content.strip():
                                    st.markdown(content)
                                else:
                                    st.info("Phase completed but no content received.")
                            elif isinstance(content, dict):
                                # Check for new simplified schema first (for testing phase and others)
                                if "summary" in content and "details" in content:
                                    # New schema: summary + details
                                    if "original_request" in content:
                                        st.write("**📋 Original Request:**")
                                        st.write(content["original_request"])
                                        st.divider()
                                    
                                    st.write("**Summary:**")
                                    st.markdown(content["summary"])
                                    st.divider()
                                    
                                    st.write("**Details:**")
                                    st.markdown(content["details"])
                                    
                                    if "next_agent_instructions" in content:
                                        st.divider()
                                        st.write("**Next Agent Instructions:**")
                                        st.info(content["next_agent_instructions"])
                                
                                # Fall back to old structured outputs (backward compatibility)
                                elif phase_id == "planning" and "project_overview" in content:
                                    st.write("**Project Overview:**")
                                    overview = content["project_overview"]
                                    if isinstance(overview, dict):
                                        for key, value in overview.items():
                                            if isinstance(value, list):
                                                st.write(f"**{key.replace('_', ' ').title()}:**")
                                                for item in value:
                                                    st.write(f"- {item}")
                                            else:
                                                st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                                
                                elif phase_id == "analysis" and "technical_feasibility" in content:
                                    st.write("**Technical Feasibility:**")
                                    feasibility = content["technical_feasibility"]
                                    if isinstance(feasibility, dict):
                                        for key, value in feasibility.items():
                                            st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                                
                                elif phase_id == "design" and "database_design" in content:
                                    st.write("**Database Design:**")
                                    db_design = content["database_design"]
                                    if isinstance(db_design, dict):
                                        if "schema" in db_design:
                                            st.write("**Schema:**")
                                            for table in db_design["schema"]:
                                                st.write(f"**Table: {table.get('table_name', 'Unknown')}**")
                                                for col in table.get("columns", []):
                                                    st.write(f"- {col.get('name')} ({col.get('type')})")
                                
                                elif phase_id == "testing" and "test_strategy" in content:
                                    st.write("**Test Strategy:**")
                                    strategy = content["test_strategy"]
                                    if isinstance(strategy, dict):
                                        for key, value in strategy.items():
                                            st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                                
                                # Generic display for other dict content
                                else:
                                    # Try to display as formatted text
                                    try:
                                        formatted_content = json.dumps(content, indent=2)
                                        st.code(formatted_content, language="json")
                                    except:
                                        for key, value in content.items():
                                            if isinstance(value, (str, int, float, bool)):
                                                st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                                            elif isinstance(value, list):
                                                st.write(f"**{key.replace('_', ' ').title()}:**")
                                                for item in value:
                                                    st.write(f"- {item}")
                            else:
                                st.write(content)
            
            # Handle simple text responses or final response without phase
            else:
                if isinstance(msg, str):
                    # Check if it's a placeholder status
                    if "..." in msg or any(phase["icon"] in msg for phase in PHASES):
                        # Show as processing status
                        for phase in PHASES:
                            if phase["icon"] in msg:
                                st.markdown(f"""
                                    <div class="phase-card active">
                                        <div style="display: flex; align-items: center; gap: 1rem;">
                                            <span style="font-size: 2rem;">{phase['icon']}</span>
                                            <div style="flex: 1;">
                                                <h4 style="margin: 0; color: #667eea;">{phase['name']}...</h4>
                                            </div>
                                            <div class="spinner" style="border: 3px solid #f3f3f3; border-top: 3px solid #667eea; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite;"></div>
                                        </div>
                                    </div>
                                """, unsafe_allow_html=True)
                                break
                    else:
                        st.markdown(f"""
                            <div class="twin-message">
                                <strong>🤖 Twin:</strong><br>
                                {msg}
                            </div>
                        """, unsafe_allow_html=True)
                elif isinstance(msg, dict):
                    # Handle final response from Format Final Response node
                    if "output" in msg or "response" in msg:
                        final_content = msg.get("output", msg.get("response", msg))
                        st.markdown(f"""
                            <div class="twin-message">
                                <strong>🎉 Final Response:</strong><br>
                                {str(final_content)}
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                            <div class="twin-message">
                                <strong>🤖 Twin:</strong><br>
                                {json.dumps(msg, indent=2)}
                            </div>
                        """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                        <div class="twin-message">
                            <strong>🤖 Twin:</strong><br>
                            {str(msg)}
                        </div>
                    """, unsafe_allow_html=True)

# Auto-refresh every 2 seconds if there are processing phases or if file was recently modified
has_processing = any(
    (isinstance(msg, dict) and msg.get("type") == "phase_status") or
    (isinstance(msg, str) and "..." in msg and any(phase["icon"] in msg for phase in PHASES))
    for _, msg in st.session_state.chat_history
)

# Also check if file was modified recently (within last 5 seconds)
chat_file = get_chat_file(st.session_state.current_chat_id)
file_recently_modified = False
if os.path.exists(chat_file):
    current_mtime = os.path.getmtime(chat_file)
    # If file was modified in the last 5 seconds, it might be a new update
    if current_mtime > st.session_state.last_chat_mtime:
        file_recently_modified = True
        st.session_state.last_chat_mtime = current_mtime
        # Reload chat history
        st.session_state.chat_history = load_chat()

if has_processing or file_recently_modified:
    time.sleep(2)
    st.rerun()