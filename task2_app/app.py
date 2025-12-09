import streamlit as st
import sqlite3
import pandas as pd
import google.generativeai as genai
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Fynd Feedback System", layout="wide")

# Try to get API key from Streamlit Secrets (for deployment), fallback to hardcoded (local)
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    API_KEY = "AIzaSyAE-Stt-y-c3up-GAg5YE0F2og2x-eYZks" # <--- PASTE KEY HERE FOR LOCAL TESTING

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-flash-lite-latest')

# --- DATABASE HANDLERS ---
DB_FILE = 'reviews.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stars INTEGER,
            review_text TEXT,
            ai_summary TEXT,
            ai_actions TEXT,
            timestamp DATETIME
        )
    ''')
    conn.commit()
    conn.close()

def save_review(stars, text, summary, actions):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO reviews (stars, review_text, ai_summary, ai_actions, timestamp) VALUES (?, ?, ?, ?, ?)",
              (stars, text, summary, actions, datetime.now()))
    conn.commit()
    conn.close()

def get_all_reviews():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM reviews ORDER BY id DESC", conn)
    conn.close()
    return df

# --- AI HANDLER ---
def process_with_ai(stars, text):
    # We ask for a User Response (displayed instantly) and Admin Insights (saved to DB)
    
    # 1. User Response
    prompt_response = f"Write a polite response to a customer who gave {stars} stars saying: '{text}'"
    user_resp = model.generate_content(prompt_response).text
    
    # 2. Admin Summary
    prompt_summary = f"Summarize this review in one sentence: '{text}'"
    summary = model.generate_content(prompt_summary).text
    
    # 3. Admin Actions
    prompt_actions = f"Suggest 2 actionable improvements based on this review: '{text}'"
    actions = model.generate_content(prompt_actions).text
    
    return user_resp, summary, actions

# --- MAIN APP LOGIC ---
init_db()

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["User Dashboard", "Admin Dashboard"])

# === PAGE 1: USER DASHBOARD ===
if page == "User Dashboard":
    st.title("🌟 Submit Your Review")
    st.markdown("We'd love to hear about your experience.")
    
    with st.form("feedback_form"):
        rating = st.slider("How many stars?", 1, 5, 5)
        text = st.text_area("Tell us more...")
        submitted = st.form_submit_button("Submit Feedback")
        
        if submitted and text:
            with st.spinner("Analyzing your feedback..."):
                # Call AI
                user_msg, summary, actions = process_with_ai(rating, text)
                
                # Save Data
                save_review(rating, text, summary, actions)
                
                # Show Result
                st.success("Thank you for your feedback!")
                st.info(f"**Our Response:** {user_msg}")

# === PAGE 2: ADMIN DASHBOARD ===
elif page == "Admin Dashboard":
    st.title("📊 Admin Insights")
    st.markdown("Internal view of customer feedback.")
    
    df = get_all_reviews()
    
    if not df.empty:
        # Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Reviews", len(df))
        col2.metric("Avg Rating", f"{df['stars'].mean():.1f}")
        col3.metric("Latest", df['timestamp'].iloc[0][:10])
        
        st.divider()
        
        # Live Feed
        st.subheader("Live Feed")
        for i, row in df.iterrows():
            with st.expander(f"{'⭐'*row['stars']} (ID: {row['id']})"):
                st.write(f"**Customer said:** {row['review_text']}")
                st.markdown("---")
                st.warning(f"**AI Summary:** {row['ai_summary']}")
                st.success(f"**Suggested Actions:**\n{row['ai_actions']}")
    else:
        st.info("No reviews submitted yet.")