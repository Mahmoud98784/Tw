import streamlit as st

def login(username, password):
    # Simple demo auth
    if username == "admin" and password == "password":
        st.session_state["authenticated"] = True
        return True
    return False

def logout():
    st.session_state["authenticated"] = False