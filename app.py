import streamlit as st
import base64
import time

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Valentine Surprise",
    page_icon="💌",
    layout="centered"
)

# --- HELPER FUNCTIONS ---
def encode_data(text):
    """Encodes text to Base64 to make the URL look cleaner."""
    return base64.b64encode(text.encode()).decode()

def decode_data(text):
    """Decodes Base64 back to text."""
    try:
        return base64.b64decode(text.encode()).decode()
    except:
        return "Unknown"

# --- CSS STYLING ---
def apply_style():
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(to bottom right, #ffe6e6, #ffb3b3);
        }
        .card {
            background-color: rgba(255, 255, 255, 0.9);
            border: 3px solid #ff4d4d;
            border-radius: 25px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .message-text {
            font-family: 'Comic Sans MS', cursive, sans-serif;
            color: #d63384;
            font-size: 30px;
            font-weight: bold;
            line-height: 1.6;
        }
        .signature {
            font-family: 'Arial', sans-serif;
            color: #555;
            font-style: italic;
            margin-top: 20px;
            font-size: 18px;
        }
        .big-emoji {
            font-size: 80px;
            margin-bottom: 20px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# --- MAIN LOGIC ---

# 1. Check Query Parameters (The Receiver View)
query_params = st.query_params
msg_param = query_params.get("msg", None)
from_param = query_params.get("from", None)

if msg_param:
    # --- RECEIVER VIEW ---
    apply_style()
    
    # Decode the hidden message and sender
    message_text = decode_data(msg_param)
    sender_name = decode_data(from_param) if from_param else "Secret Admirer"

    # Display the Valentine Card
    st.markdown(f"""
        <div class="card">
            <div class="big-emoji">💌</div>
            <div class="message-text">"{message_text}"</div>
            <div class="signature">- From: {sender_name}</div>
        </div>
    """, unsafe_allow_html=True)

    # Interactive Buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("YES! ❤️", use_container_width=True, type="primary"):
            st.balloons()
            st.success("Yay! They said YES! 💖")
            time.sleep(1)
            st.snow()
            
    with col2:
        if st.button("No 💔", use_container_width=True):
            st.error("Wrong answer! Try clicking the other button... 😉")

    # Link to make their own
    st.write("---")
    if st.button("↺ Create your own link"):
        st.query_params.clear()
        st.rerun()

else:
    # --- CREATOR VIEW ---
    st.title("🏹 Cupid's Link Generator")
    st.write("Create a surprise message link for someone special.")

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            sender = st.text_input("Your Name", placeholder="e.g. Romeo")
        with col2:
            # Helper to get the correct URL
            # Users must update this if deployed
            base_url = st.text_input("Your App URL", value="http://localhost:8501")
        
        message = st.text_area("Your Message", placeholder="Will you be my Valentine?", height=100)

        submitted = st.button("Generate Link", type="primary")

    if submitted:
        if not message:
            st.warning("Please enter a message first!")
        else:
            # Encode inputs
            enc_msg = encode_data(message)
            enc_sender = encode_data(sender) if sender else ""
            
            # Create full URL
            # We strip trailing slashes to ensure the query param appends correctly
            clean_base_url = base_url.rstrip("/")
            final_link = f"{clean_base_url}/?msg={enc_msg}&from={enc_sender}"
            
            st.success("Link Ready! Copy it below:")
            st.code(final_link, language="text")
            st.info("👉 Send this link to your crush/partner!")
