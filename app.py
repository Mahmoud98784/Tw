import streamlit as st
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

st.set_page_config(
    page_title="AI Twin",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = True  # Auto-authenticate for now

if "username" not in st.session_state:
    st.session_state.username = "User"

if "settings" not in st.session_state:
    st.session_state.settings = {
        'theme': 'light',
        'notifications': True,
        'privacy_mode': False,
        'data_retention_days': 30
    }

# Custom CSS for enhanced UI
st.markdown("""
    <style>
    /* Main styling */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    [data-testid="stSidebar"] .sidebar-content {
        color: white;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
    }
    
    /* Chat messages */
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .twin-message {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #667eea;
    }
    
    /* Code blocks */
    .stCodeBlock {
        border-radius: 8px;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
    }
    </style>
""", unsafe_allow_html=True)

def main():
    # Enhanced sidebar navigation
    with st.sidebar:
        st.markdown("""
            <div style='text-align: center; padding: 1rem 0;'>
                <h1 style='color: white; margin: 0;'>🤖 AI Twin</h1>
                <p style='color: rgba(255,255,255,0.8); margin: 0.5rem 0;'>Digital Twin System</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        page = st.radio(
            "Navigate to:",
            ["🏠 Home", "💬 Chat", "⚙️ Settings"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # User info
        st.markdown(f"""
            <div style='padding: 1rem; background: rgba(255,255,255,0.1); border-radius: 8px;'>
                <p style='color: white; margin: 0;'><strong>👤 {st.session_state.username}</strong></p>
            </div>
        """, unsafe_allow_html=True)
    
    # Route to pages
    if "🏠 Home" in page:
        from pages import home
    elif "💬 Chat" in page:
        from pages import Chat
    elif "⚙️ Settings" in page:
        from pages import Settings
        Settings.show_settings_page()

if __name__ == "__main__":
    main()