import streamlit as st
import requests

# Set page configuration
st.set_page_config(page_title="🤖 AI PDF Chatbot (Gemini)", layout="wide")

# Custom CSS for better UI
st.markdown(
    """
    <style>
    body {background-color: #0f0f0f;}
    .stTextInput > div > div > input {
        background-color: #222;
        color: white;
        border-radius: 10px;
        padding: 10px;
    }
    .chat-container {max-height: 500px; overflow-y: auto; padding: 10px;}
    .user-message {background-color: #0052cc; color: white; padding: 10px; border-radius: 10px; text-align: right; margin-bottom: 5px;}
    .bot-message {background-color: #222; color: #0ff; padding: 10px; border-radius: 10px; margin-bottom: 5px;}
    .clear-btn {background-color: #ff1744; color: white; padding: 8px; border-radius: 10px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# Title and description
st.title("🤖 AI PDF Chatbot ")
st.markdown("<p style='color: #bbb;'>Upload a PDF and start chatting!</p>", unsafe_allow_html=True)

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None
if "last_query" not in st.session_state:
    st.session_state.last_query = None
if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False #Add file upload state.

# Sidebar for file upload
with st.sidebar:
    st.subheader("📂 Upload PDF")
    uploaded_file = st.file_uploader("Upload a PDF", type="pdf")

    if uploaded_file and uploaded_file != st.session_state.uploaded_file:
        st.session_state.uploaded_file = uploaded_file
        with st.spinner("📤 Uploading PDF..."):
            files = {"file": uploaded_file.getvalue()}
            response = requests.post("http://127.0.0.1:8000/upload/", files=files)

        if response.status_code == 200:
            st.success(f"✅ {uploaded_file.name} uploaded successfully!")
            st.session_state.file_uploaded = True #set upload flag to true.
        else:
            st.error(f"🚨 Upload failed! Error: {response.text}")

# Function to get chatbot response
def get_response(query):
    try:
        response = requests.post("http://127.0.0.1:8000/query/", json={"query": query})
        response.raise_for_status()
        return response.json().get("answer", "🤖 No answer found.")
    except requests.exceptions.RequestException as e:
        return f"🚨 Error: {str(e)}"

# Chat display container
chat_display = st.empty()

# Display chat history
with chat_display.container():
    for chat in st.session_state.chat_history:
        role_class = "user-message" if chat["role"] == "user" else "bot-message"
        st.markdown(f"<div class='{role_class}'>{chat['text']}</div>", unsafe_allow_html=True)

# User Query Input
query = st.text_input("📝 Enter your query:", key="query", help="Ask a question about the uploaded PDF")

if query and query != st.session_state.last_query:
    st.session_state.last_query = query
    st.session_state.chat_history.append({"role": "user", "text": query})
    with st.spinner("🤖 Thinking..."):
        answer = get_response(query)
    st.session_state.chat_history.append({"role": "bot", "text": answer})
    st.rerun()

