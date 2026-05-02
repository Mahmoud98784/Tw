import streamlit as st
from datetime import datetime

def show_settings_page():
    
    st.markdown('<div class="main-header">⚙️ My Settings</div>', unsafe_allow_html=True)
    
    # Tabs for different settings categories
    tab_profile, tab_privacy, tab_notifications, tab_about = st.tabs([
        "👤 Profile", "🔒 Privacy", "🔔 Notifications", "ℹ️ About"
    ])
    
    with tab_profile:
        st.markdown("### Personal Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Display Name", value=st.session_state.username)
            email = st.text_input("Email Address", placeholder="your.email@example.com")
        
        with col2:
            company = st.text_input("Company/Organization", placeholder="Optional")
            role = st.selectbox("Primary Role", [
                "Project Manager",
                "Developer",
                "Business Analyst",
                "Product Owner",
                "Student",
                "Researcher",
                "Other"
            ])
        
        # Expertise level
        st.markdown("### Expertise Level")
        expertise = st.select_slider(
            "How would you describe your technical expertise?",
            options=["Beginner", "Intermediate", "Advanced", "Expert"]
        )
        
        if st.button("💾 Save Profile Changes", type="primary"):
            st.session_state.username = name
            st.success("Profile updated successfully!")
    
    with tab_privacy:
        st.markdown("### Privacy & Data Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            privacy_mode = st.toggle(
                "Enhanced Privacy Mode",
                value=st.session_state.settings['privacy_mode'],
                help="When enabled, your conversations are not stored for improvement"
            )
            
            data_retention = st.selectbox(
                "Chat History Retention",
                ["7 days", "30 days", "90 days", "Keep forever"],
                index=1
            )
        
        with col2:
            allow_analytics = st.toggle(
                "Allow Anonymous Analytics",
                value=True,
                help="Help improve the service (no personal data collected)"
            )
            
            auto_clear = st.toggle(
                "Auto-clear old conversations",
                value=False,
                help="Automatically remove conversations older than retention period"
            )
        
        st.markdown("---")
        st.markdown("### Data Management")
        
        col_export, col_clear = st.columns(2)
        
        with col_export:
            if st.button("📥 Export My Data", use_container_width=True):
                st.info("Export feature coming soon")
                # TODO: Implement data export
        
        with col_clear:
            if st.button("🗑️ Clear All My Data", use_container_width=True, type="secondary"):
                if st.checkbox("I understand this will delete all my chat history and settings"):
                    st.session_state.chat_history = []
                    st.session_state.settings = {
                        'theme': 'light',
                        'notifications': True,
                        'privacy_mode': False,
                        'data_retention_days': 30
                    }
                    st.success("All personal data cleared!")
                    st.rerun()
    
    with tab_notifications:
        st.markdown("### Notification Preferences")
        
        email_notifications = st.toggle(
            "Email Notifications",
            value=st.session_state.settings['notifications'],
            help="Receive updates and summaries via email"
        )
        
        st.markdown("#### Notification Types")
        
        col1, col2 = st.columns(2)
        
        with col1:
            new_features = st.checkbox("New features & updates", value=True)
            weekly_summary = st.checkbox("Weekly summary report", value=True)
        
        with col2:
            important_alerts = st.checkbox("Important alerts", value=True)
            tips_tutorials = st.checkbox("Tips & tutorials", value=False)
        
        notification_frequency = st.select_slider(
            "Notification Frequency",
            options=["Minimal", "Normal", "Frequent"]
        )
        
        if st.button("💾 Save Notification Settings", type="primary"):
            st.session_state.settings['notifications'] = email_notifications
            st.success("Notification settings saved!")
    
    with tab_about:
        st.markdown("### About Digital Twin AI")
        
        st.markdown("""
        **Version**: 1.0.0  
        **Last Updated**: October 2024  
        **Developed by**: Digital Twin AI Team
        
        ---
        
        ### 🤖 What is Digital Twin AI?
        
        Digital Twin AI is an intelligent assistant that helps you make informed decisions 
        about AI tools and technologies by analyzing real-time community insights, 
        technical specifications, and project requirements.
        
        ---
        
        ### 🔧 How It Works
        
        1. **Analysis**: Processes your query and requirements
        2. **Research**: Gathers insights from developer communities and technical sources
        3. **Evaluation**: Compares AI models based on multiple criteria
        4. **Recommendation**: Provides personalized suggestions with reasoning
        
        ---
        
        ### 📊 Data Sources
        
        - Developer community discussions
        - Technical documentation and benchmarks
        - Real-world implementation experiences
        - Industry trends and analysis
        
        ---
        
        ### 🔒 Privacy Commitment
        
        Your conversations are private. We don't:
        - Share your data with third parties
        - Use your conversations for training without consent
        - Store personal identifiable information
        
        ---
        
        ### 🆘 Need Help?
        
        - Check our documentation
        - Contact support: support@digitaltwin-ai.com
        - Report issues on GitHub
        
        """)
        
        st.markdown("---")
        st.caption("© 2026 Digital Twin AI. All rights reserved.")

if __name__ == "__main__":
    show_settings_page()