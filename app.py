import streamlit as st
import base64
import urllib.parse
import qrcode
import io
import time
import os

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="Valentine Surprise 💌",
    page_icon="💘",
    layout="centered"
)

# -------------------------------------------------
# HELPERS
# -------------------------------------------------
def encode_data(text: str) -> str:
    return urllib.parse.quote(
        base64.b64encode(text.encode()).decode()
    )

def decode_data(text: str) -> str:
    try:
        return base64.b64decode(
            urllib.parse.unquote(text).encode()
        ).decode()
    except:
        return "Unknown"

def generate_qr(link: str):
    qr = qrcode.make(link)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()

def get_public_base_url():
    """
    HARD RULE:
    - If NOT deployed → STOP (no localhost allowed)
    - If deployed → return public Streamlit Cloud URL
    """
    if "STREAMLIT_SERVER_PORT" not in os.environ:
        st.error("🚫 Shareable links are disabled in local mode.")
        st.info("Deploy this app on Streamlit Cloud to generate public links.")
        st.stop()

    proto = st.request.headers.get("x-forwarded-proto", "https")
    host = st.request.headers.get("host")

    if not host:
        st.error("Unable to detect public URL.")
        st.stop()

    return f"{proto}://{host}"

# -------------------------------------------------
# STYLES
# -------------------------------------------------
def apply_style():
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(to bottom right, #ffe6e6, #ffb3b3);
    }
    .card {
        background: rgba(255,255,255,0.95);
        border-radius: 25px;
        padding: 40px;
        text-align: center;
        box-shadow: 0 12px 30px rgba(0,0,0,0.15);
    }
    .message {
        font-size: 30px;
        color: #d63384;
        font-weight: bold;
        font-family: 'Comic Sans MS', cursive;
        line-height: 1.6;
    }
    .from {
        margin-top: 20px;
        font-style: italic;
        color: #555;
        font-size: 18px;
    }
    </style>
    """, unsafe_allow_html=True)

# -------------------------------------------------
# QUERY PARAMS
# -------------------------------------------------
params = st.query_params
msg_param = params.get("msg")
from_param = params.get("from")

# =================================================
# RECEIVER VIEW
# =================================================
if msg_param:
    apply_style()

    message_text = decode_data(msg_param)
    sender_name = decode_data(from_param) if from_param else "Secret Admirer 💘"

    st.markdown(f"""
        <div class="card">
            <h1>💌</h1>
            <div class="message">"{message_text}"</div>
            <div class="from">— {sender_name}</div>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("YES ❤️", use_container_width=True, type="primary"):
            st.balloons()
            st.success("They said YES 💖")
            time.sleep(1)
            st.snow()

    with col2:
        if st.button("No 💔", use_container_width=True):
            st.error("Wrong choice 😜 Try again")

    st.divider()

    if st.button("↺ Create your own surprise"):
        st.query_params.clear()
        st.rerun()

# =================================================
# CREATOR VIEW
# =================================================
else:
    st.title("🏹 Cupid’s Surprise Generator")

    message = st.text_area(
        "Your Message 💕",
        placeholder="Will you be my Valentine?",
        height=120
    )

    anonymous = st.toggle("Anonymous Crush Mode 💭", value=False)

    sender_name = ""
    if not anonymous:
        sender_name = st.text_input("Your Name (optional)")

    if st.button("Generate Surprise 💘", type="primary"):
        if not message:
            st.warning("Please write a message first!")
        else:
            base_url = get_public_base_url()

            enc_msg = encode_data(message)
            final_link = f"{base_url}?msg={enc_msg}"

            if not anonymous and sender_name:
                enc_sender = encode_data(sender_name)
                final_link += f"&from={enc_sender}"

            st.success("💖 Your surprise is ready!")

            st.code(final_link, language="text")

            qr_img = generate_qr(final_link)
            st.image(qr_img, caption="📱 Scan to open the surprise")

            st.info("Share the link or QR code with your crush 💌")
