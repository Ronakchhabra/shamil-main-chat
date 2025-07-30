import streamlit as st
import pandas as pd
import json
from datetime import datetime
import uuid
import sys
import os
import hashlib
import base64
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# Now import your modules
from chatbot import create_chatbot
import time
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Advanced imports for professional UI more enhanced v1
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
    AGGRID_AVAILABLE = True
except ImportError:
    AGGRID_AVAILABLE = False

# Configure page with professional settings
st.set_page_config(
    page_title="Natural Language Querying",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Natural Language Querying"
    }
)

# ============== HELPER FUNCTIONS ==============

def get_base64_of_image(path):
    """Convert image to base64 string"""
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return ""

# ============== LOGIN SYSTEM ==============

# Simple user credentials dictionary (username: password)
USER_CREDENTIALS = {
    "ronak": "pass123",
    "ashwin": "pass123",
    "mahendra": "pass123",
    "shamal": "pass123"
}

def verify_password(stored_password, provided_password):
    """Verify a stored password against provided password"""
    return stored_password == provided_password

def authenticate_user(username, password):
    """Authenticate user credentials"""
    if username in USER_CREDENTIALS:
        return verify_password(USER_CREDENTIALS[username], password)
    return False

def login_form():
    """Display login form"""
    # Reduce top margin and padding significantly
    st.markdown("""
    <style>
        .main .block-container {
            padding-top: 1rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Center the login form with reduced spacing
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        # Login form with logo and sign in title in same row
        with st.form("login_form", clear_on_submit=False):
            # Logo and Sign In title in same row
            st.markdown(f"""
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem;">
                <img src="data:image/png;base64,{get_base64_of_image('logo.png')}" style="height: 50px;" />
                <h5 style="margin: 0; display: flex; align-items: center; gap: 0.5rem;">
                    🔐 Sign In
                </h5>
            </div>
            """, unsafe_allow_html=True)
            
            username = st.text_input(
                "Username",
                placeholder="Enter your username"
            )
            
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password"
            )
            
            login_button = st.form_submit_button(
                "🚀 Sign In",
                type="primary",
                use_container_width=True
            )
            
            if login_button:
                if username and password:
                    if authenticate_user(username, password):
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.login_time = datetime.now()
                        st.success("✅ Login successful! Redirecting...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
                else:
                    st.warning("⚠️ Please enter both username and password")
        
        # Add confidential notice at bottom of login
        st.markdown("""
        <div style="text-align: center; margin-top: 2rem; padding: 1rem; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0;">
            <p style="margin: 0; font-size: 0.8rem; color: #64748b;">
                <strong>CONFIDENTIAL</strong><br>
                This system contains confidential and proprietary information.<br>
                Unauthorized access is strictly prohibited.
            </p>
        </div>
        """, unsafe_allow_html=True)

def logout():
    """Logout function"""
    for key in list(st.session_state.keys()):
        if key not in ['authenticated']:
            del st.session_state[key]
    st.session_state.authenticated = False
    st.rerun()

# ============== MAIN APP LOGIC ==============

# Initialize session state for authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Show login form if not authenticated
if not st.session_state.authenticated:
    login_form()
    st.stop()

# Initialize other session state variables after authentication
if "chatbot" not in st.session_state:
    st.session_state.chatbot = create_chatbot()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_query_result" not in st.session_state:
    st.session_state.current_query_result = None
if "show_sql" not in st.session_state:
    st.session_state.show_sql = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "chat"

# Professional CSS with modern design
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {visibility: hidden;}
    
    /* Global styles - Reduced spacing */
    .main .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
        max-width: 100%;
    }
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Professional Header - Reduced margin */
    .professional-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem 2rem;
        margin: -0.5rem -0.5rem 0 -0.5rem;
        color: white;
        border-radius: 0;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
    }
    
    .header-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    .header-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: white;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    
    .header-subtitle {
        font-size: 0.9rem;
        opacity: 0.9;
        font-weight: 300;
        margin-top: 0.25rem;
    }
    
    .header-stats {
        display: flex;
        gap: 2rem;
        font-size: 0.85rem;
    }
    
    .stat-item {
        text-align: center;
        opacity: 0.9;
    }
    
    .stat-value {
        font-weight: 600;
        font-size: 1.1rem;
        display: block;
    }
    
    /* User info badge */
    .user-badge {
        background: rgba(255, 255, 255, 0.2);
        padding: 0.5rem 1rem;
        border-radius: 20px;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.85rem;
        backdrop-filter: blur(10px);
    }
    
    .logout-badge {
        background: rgba(255, 255, 255, 0.2);
        padding: 0.5rem 1rem;
        border-radius: 20px;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.85rem;
        backdrop-filter: blur(10px);
        transition: background 0.2s ease;
    }
    
    .logout-badge:hover {
        background: rgba(255, 255, 255, 0.3);
    }
    
    /* Main Layout */
    .main-container {
        display: flex;
        gap: 1.5rem;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    
    /* Chat Panel */
    .chat-panel {
        flex: 1;
        background: white;
        border-radius: 16px;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
        border: 1px solid #f1f5f9;
        display: flex;
        flex-direction: column;
    }
    
    .chat-header {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        padding: 1rem 1.5rem;
        border-bottom: 1px solid #e2e8f0;
        border-radius: 16px 16px 0 0;
    }
    
    .chat-header h3 {
        margin: 0;
        font-size: 1.1rem;
        font-weight: 600;
        color: #1e293b;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .chat-messages {
        padding: 1.5rem;
        background: #fafbfc;
        flex: 1;
    }
    
    .chat-input-section {
        padding: 1rem 1.5rem;
        background: white;
        border-top: 1px solid #e2e8f0;
        border-radius: 0 0 16px 16px;
    }
    
    /* Results Panel */
    .results-panel {
        flex: 0 0 45%;
        background: white;
        border-radius: 16px;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
        border: 1px solid #f1f5f9;
        display: flex;
        flex-direction: column;
    }
    
    .results-header {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        padding: 1.25rem 1.5rem;
        border-bottom: 1px solid #e2e8f0;
        border-radius: 16px 16px 0 0;
    }
    
    .results-header h3 {
        margin: 0;
        font-size: 1.25rem;
        font-weight: 600;
        color: #1e293b;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .results-content {
        flex: 1;
        overflow: hidden;
        display: flex;
        flex-direction: column;
    }
    
    /* Status Indicators */
    .status-success {
        background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%);
        border: 1px solid #10b981;
        color: #059669;
        padding: 1rem 1.25rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        font-weight: 500;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .status-error {
        background: linear-gradient(135deg, #fef2f2 0%, #fef7f7 100%);
        border: 1px solid #ef4444;
        color: #dc2626;
        padding: 1rem 1.25rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        font-weight: 500;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Metrics Cards */
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    
    .metric-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1e293b;
        display: block;
        margin-bottom: 0.25rem;
    }
    
    .metric-label {
        font-size: 0.8rem;
        color: #64748b;
        font-weight: 500;
    }
    
    /* Empty State */
    .empty-state {
        text-align: center;
        padding: 3rem 2rem;
        color: #64748b;
        background: #f8fafc;
        border-radius: 12px;
        border: 2px dashed #cbd5e1;
    }
    
    .empty-state-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        opacity: 0.5;
    }
    
    .empty-state h4 {
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        color: #475569;
    }
    
    /* SQL Container */
    .sql-container {
        background: #1e293b;
        border-radius: 12px;
        overflow: hidden;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    .sql-header {
        background: #334155;
        padding: 1rem 1.25rem;
        color: #e2e8f0;
        font-weight: 500;
        font-size: 0.875rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .sql-content {
        padding: 1.25rem;
        background: #1e293b;
        color: #e2e8f0;
        font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
        font-size: 0.875rem;
        line-height: 1.6;
        overflow-x: auto;
    }
    
    /* Custom Streamlit Overrides */
    .stChatMessage {
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        border: 1px solid #f1f5f9;
        margin-bottom: 1rem !important;
        padding: 1rem !important;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 500;
        padding: 0.6rem 1.2rem;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        background: #f1f5f9;
        padding: 4px;
        border-radius: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        padding: 0px 16px;
        background: transparent;
        border-radius: 6px;
        color: #64748b;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background: white;
        color: #1e293b;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .main-container {
            flex-direction: column;
        }
        
        .results-panel {
            flex: none;
        }
        
        .header-stats {
            display: none;
        }
    }
</style>
""", unsafe_allow_html=True)

def add_message(content, role="user", avatar=None):
    """Add message to chat history"""
    message = {
        "content": content,
        "role": role,
        "timestamp": datetime.now(),
        "avatar": avatar
    }
    st.session_state.messages.append(message)

def process_user_query(user_input):
    """Process user query and update results with step-by-step spinners"""
    if not user_input.strip():
        return
    
    # Add user message to chat
    add_message(user_input, "user", "👤")
    
    try:
        # Initialize the generator
        query_generator = st.session_state.chatbot.process_query_with_progress(user_input)
        final_result = None
        
        # Step 1: Initialize
        with st.spinner("🔄 Starting analysis..."):
            status, message, partial_result = next(query_generator)
        
        # Step 2: Retrieve context
        with st.spinner("🔍 Retrieving contextual information..."):
            status, message, partial_result = next(query_generator)
        
        # Step 3: Load schema
        with st.spinner("📋 Loading database schema..."):
            status, message, partial_result = next(query_generator)
        
        # Step 4: Analyze question
        with st.spinner("🧠 Analyzing your question and requirements..."):
            status, message, partial_result = next(query_generator)
        
        # Step 5: Generate SQL
        with st.spinner("🔧 Generating SQL query from your request..."):
            status, message, partial_result = next(query_generator)
            # Check if we need to retry generation
            if status == "retrying_generation":
                with st.spinner("🔄 Trying alternative approach..."):
                    status, message, partial_result = next(query_generator)
            # Check if SQL generation failed
            if status == "error":
                final_result = partial_result
                raise StopIteration
        
        # Step 6: Validate SQL
        with st.spinner("✅ Validating SQL query syntax..."):
            status, message, partial_result = next(query_generator)
            # Check if we need to fix SQL
            if status == "fixing_sql":
                with st.spinner("🛠️ SQL validation failed, fixing query..."):
                    status, message, partial_result = next(query_generator)
            # Check if fixing failed
            if status == "error":
                final_result = partial_result
                raise StopIteration
        
        # Step 7: Execute query
        with st.spinner("⚡ Executing query against database..."):
            status, message, partial_result = next(query_generator)
            # Check if we need to fix execution
            if status == "fixing_execution":
                with st.spinner("🛠️ Query execution failed, fixing and retrying..."):
                    status, message, partial_result = next(query_generator)
            # Check if execution failed
            if status == "error":
                final_result = partial_result
                raise StopIteration
        
        # Step 8: Generate response
        with st.spinner("🤖 Generating AI response..."):
            status, message, partial_result = next(query_generator)
        
        # Step 9: Store in memory
        with st.spinner("💾 Storing interaction in memory..."):
            status, message, partial_result = next(query_generator)
        
        # Step 10: Complete
        with st.spinner("✅ Finalizing analysis..."):
            status, message, final_result = next(query_generator)
        
        # Process final result
        if final_result and final_result['success']:
            # Store result for display in results panel
            st.session_state.current_query_result = final_result
            
            # Create AI response
            response_content = f"""**Analysis Complete!**

{final_result['response']}
"""
            add_message(response_content, "assistant", "🤖")
            
        else:
            # Handle error
            error_content = f"""❌ **Query Error**

{final_result['response'] if final_result else 'Unknown error occurred'}

**Error Details:** {final_result.get('error', 'Unknown error') if final_result else 'Processing failed'}"""
            
            add_message(error_content, "assistant", "⚠️")
            
    except StopIteration:
        # Handle early termination (usually due to error)
        if final_result:
            error_content = f"""❌ **Query Error**

{final_result['response']}

**Error Details:** {final_result.get('error', 'Unknown error')}"""
            add_message(error_content, "assistant", "⚠️")
        else:
            add_message("❌ **Processing Error**\n\nQuery processing was interrupted.", "assistant", "⚠️")
            
    except Exception as e:
        error_msg = f"❌ **System Error**\n\nError processing query: {str(e)}"
        add_message(error_msg, "assistant", "⚠️")

def clear_chat():
    """Clear chat history"""
    st.session_state.messages = []
    st.session_state.current_query_result = None

def create_results_table(query_result):
    """Create and display results table"""
    if not query_result or not query_result.get('success'):
        return None
    
    try:
        # Execute query to get actual data
        chatbot = st.session_state.chatbot
        sql_query = query_result['sql_query']
        
        # Get the data
        df = chatbot.db_manager.execute_query(sql_query)
        
        if df.empty:
            st.info("📊 No data found for this query.")
            return None
        
        if AGGRID_AVAILABLE:
            # Use AgGrid for advanced table features
            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_default_column(
                resizable=True,
                sortable=True,
                filterable=True,
                editable=False,
                wrapHeaderText=True,
                autoHeaderHeight=True,
                cellStyle={'fontSize': '14px', 'fontFamily': 'Inter, sans-serif'}
            )
            
            gb.configure_pagination(paginationAutoPageSize=True)
            gb.configure_side_bar()
            gb.configure_selection('multiple', use_checkbox=True)
            
            grid_options = gb.build()
            
            # Display the grid
            grid_response = AgGrid(
                df,
                gridOptions=grid_options,
                data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
                update_mode=GridUpdateMode.SELECTION_CHANGED,
                fit_columns_on_grid_load=True,
                theme='streamlit',
                enable_enterprise_modules=False,
                height=400,
                width='100%',
                reload_data=False
            )
            
            return grid_response
        else:
            # Fallback to native Streamlit dataframe
            st.dataframe(
                df,
                use_container_width=True,
                height=400
            )
            return {"data": df}
        
    except Exception as e:
        st.error(f"Error creating table: {str(e)}")
        return None

# Professional Header with user info and YASH logo
current_user = st.session_state.get('username', 'Unknown') 
login_time = st.session_state.get('login_time')
session_duration = ""
if login_time:
    duration = datetime.now() - login_time
    minutes = int(duration.total_seconds() // 60)
    session_duration = f"{minutes}m"

st.markdown(f"""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem 2rem; margin: -0.5rem -0.5rem 0 -0.5rem; color: white; display: flex; align-items: center; justify-content: space-between;">
    <div style="display: flex; align-items: center; gap: 1rem;">
        <img src="data:image/png;base64,{get_base64_of_image('logo.png')}" style="height: 40px;" />
        <div>
            <div style="font-size: 1.6rem; font-weight: 700; margin: 0;">
                Natural Language Querying
            </div>
            <div style="font-size: 0.9rem; opacity: 0.9; font-weight: 300; margin-top: 0.25rem;">
                AI-Powered Financial Data Analytics & Insights
            </div>
        </div>
    </div>
    <div style="display: flex; align-items: center; gap: 0.75rem;">
        <div style="background: rgba(255, 255, 255, 0.2); padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.85rem; backdrop-filter: blur(10px);">
            👤 {current_user} {f'• {session_duration}' if session_duration else ''}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Logout button in sidebar (simplified)
with st.sidebar:
    st.markdown("### 👤 User Information")
    st.write(f"**Username:** {current_user}")
    if login_time:
        st.write(f"**Login Time:** {login_time.strftime('%H:%M:%S')}")
        st.write(f"**Session Duration:** {session_duration}")
    
    st.markdown("---")
    st.markdown("**📊 System Status**")
    st.write("✅ Database Connected")
    st.write("🔒 Session Active")

# Main Container
st.markdown('<div class="main-container">', unsafe_allow_html=True)

# Chat Panel
col1, col2 = st.columns([1.2, 1])

with col1:
    st.markdown("""
    <div class="chat-panel">
        <div class="chat-header">
            <h3>💬 Intelligent Assistant</h3>
        </div>
        <div class="chat-messages">
    """, unsafe_allow_html=True)
    
    # Display chat history only
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"], avatar=message.get("avatar")):
            st.markdown(message["content"])
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Simple input section
    st.markdown("""
    <div class="chat-input-section">
    """, unsafe_allow_html=True)
    
    # Chat input
    user_input = st.chat_input(
        placeholder="Ask me anything about your financial data...",
        key="main_chat_input"
    )
    
    if user_input:
        process_user_query(user_input)
        st.rerun()
    
    # Simple clear button
    if st.button("🧹 Clear Chat", key="clear_chat", type="secondary", use_container_width=True):
        clear_chat()
        st.rerun()
    
    st.markdown('</div></div>', unsafe_allow_html=True)

# Results Panel
with col2:
    st.markdown("""
    <div class="results-panel">
        <div class="results-header">
            <h3>📊 Analytics Dashboard</h3>
        </div>
        <div class="results-content">
    """, unsafe_allow_html=True)
    
    if st.session_state.current_query_result:
        result = st.session_state.current_query_result
        
        if result['success']:
            # Success status
            st.markdown(f"""
            <div class="status-success">
                <span>✅</span>
                <div>
                    <strong>Query Successful</strong><br>
                    {result['results_count']} rows • {len(result['tables_used'])} tables analyzed
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Metrics cards
            st.markdown('<div class="metrics-grid">', unsafe_allow_html=True)
            
            metrics_cols = st.columns(4)
            with metrics_cols[0]:
                st.markdown(f"""
                <div class="metric-card">
                    <span class="metric-value">{result['results_count']}</span>
                    <span class="metric-label">Records</span>
                </div>
                """, unsafe_allow_html=True)
            
            with metrics_cols[1]:
                st.markdown(f"""
                <div class="metric-card">
                    <span class="metric-value">{len(result['tables_used'])}</span>
                    <span class="metric-label">Tables</span>
                </div>
                """, unsafe_allow_html=True)
            
            with metrics_cols[2]:
                st.markdown(f"""
                <div class="metric-card">
                    <span class="metric-value">{len(st.session_state.messages)//2}</span>
                    <span class="metric-label">Queries</span>
                </div>
                """, unsafe_allow_html=True)
            
            with metrics_cols[3]:
                st.markdown(f"""
                <div class="metric-card">
                    <span class="metric-value">{result.get('context_info', {}).get('semantic_matches_count', 0)}</span>
                    <span class="metric-label">Insights</span>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Tabs for different views
            tab1, tab2, tab3 = st.tabs(["📋 Data", "📊 SQL Query", "⚙️ Actions"])
            
            with tab1:
                # Display the data table
                st.markdown("#### Query Results")
                grid_response = create_results_table(result)
                
                if grid_response and not grid_response['data'].empty:
                    st.success(f"✅ Displaying {len(grid_response['data'])} rows of data")
            
            with tab2:
                st.markdown(f"""
                <div class="sql-container">
                    <div class="sql-header">
                        <span>Generated SQL Query</span>
                        <span>SQL</span>
                    </div>
                    <div class="sql-content">{result['sql_query']}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with tab3:
                st.markdown("#### Export & Actions")
                
                action_row1 = st.columns(2)
                with action_row1[0]:
                    if st.button("📊 Export CSV", key="export_csv", type="primary"):
                        try:
                            df = st.session_state.chatbot.db_manager.execute_query(result['sql_query'])
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="⬇️ Download CSV File",
                                data=csv,
                                file_name=f"financial_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                type="primary"
                            )
                        except Exception as e:
                            st.error(f"Export failed: {str(e)}")
                
                with action_row1[1]:
                    if st.button("🔄 Refresh Data", key="refresh_data", type="secondary"):
                        st.success("✅ Data refreshed successfully!")
                
                action_row2 = st.columns(2)
                with action_row2[0]:
                    if st.button("📋 Copy Query", key="copy_query", type="secondary"):
                        st.code(result['sql_query'], language='sql')
                
                with action_row2[1]:
                    if st.button("🧹 Clear Results", key="clear_results", type="secondary"):
                        st.session_state.current_query_result = None
                        st.rerun()
        
        else:
            # Error status
            st.markdown(f"""
            <div class="status-error">
                <span>❌</span>
                <div>
                    <strong>Query Failed</strong><br>
                    {result.get('error', 'Unknown error occurred')}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if result.get('sql_query'):
                st.markdown("**🔍 Failed Query:**")
                st.code(result['sql_query'], language='sql')
    
    st.markdown('</div></div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Professional Footer with YASH Technologies branding (without logout)
st.markdown(f"""
<div style="margin-top: 2rem; padding: 1.5rem 2rem; background: #f8fafc; border-top: 1px solid #e2e8f0; border-radius: 0;">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="display: flex; align-items: center; gap: 1rem; font-size: 0.875rem; color: #64748b;">
            <span>✅ Connected to financial_data.db</span>
            <span>•</span>
            <span>📊 3 tables available</span>
            <span>•</span>
            <span>🔒 Session secured</span>
            <span>•</span>
            <span>👤 Logged in as {current_user}</span>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 0.25rem;">
                <strong style="color: #ef4444;">CONFIDENTIAL</strong> • Session: {session_duration if session_duration else 'Active'}
            </div>
            <div style="font-size: 0.75rem; color: #64748b; display: flex; align-items: center; gap: 0.5rem; justify-content: flex-end;">
                <span>Powered by</span>
                <img src="data:image/png;base64,{get_base64_of_image('logo.png')}" style="height: 16px;" />
                <strong>YASH Technologies</strong>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# External logout button - positioned at top right of main content area
st.markdown("""
<style>
.logout-floating-btn button {
    position: fixed !important;
    top: 20px !important;
    right: 20px !important;
    z-index: 1000 !important;
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important;
    color: white !important;
    border: none !important;
    padding: 0.6rem 1.2rem !important;
    border-radius: 25px !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3) !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
}
.logout-floating-btn button:hover {
    background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 16px rgba(239, 68, 68, 0.4) !important;
}
.logout-floating-btn button:focus {
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.3) !important;
}
</style>
""", unsafe_allow_html=True)

# Add floating logout button
st.markdown('<div class="logout-floating-btn">', unsafe_allow_html=True)
if st.button("🚪 Logout", key="floating_logout_btn"):
    logout()
st.markdown('</div>', unsafe_allow_html=True)