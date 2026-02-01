import streamlit as st
import base64
import time
import qrcode
import io
import urllib.parse

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Valentine Surprise 💌",
    page_icon="💘",
    layout="centered"
)

# --- HELPERS ---
def encode_data(text):
    return urllib.parse.quote(
        base64.b64encode(text.encode()).decode()
    )

def decode_data(text):
    try:
        return base64.b64decode(
            urllib.parse.unquote(text).encode()
        ).decode()
    except:
        return "Unknown"

def generate_qr(link):
    qr = qrcode.make(link)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()

def get_base_url():
    return st.request.url.split("?")[0].rstrip("/")

# --- STYLES ---
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
    }
    .from {
        margin-top: 20px;
        font-style: italic;
        color: #555;
    }
    </style>
    """, unsafe_allow_html=True)

# --- QUERY PARAMS ---
params = st.query_params
msg = params.get("msg")
sender = params.get("from")

# ================= RECEIVER VIEW =================
if msg:
    apply_style()

    message_text = decode_data(msg)
    sender_name = decode_data(sender) if sender else "Secret Admirer 💘"

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

# ================= CREATOR VIEW =================
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
        sender_name = st.text_input("Your Name (Optional)")

    if st.button("Generate Surprise Link 💘", type="primary"):
        if not message:
            st.warning("Please write a message!")
        else:
            enc_msg = encode_data(message)
            base_url = get_base_url()

            final_link = f"{base_url}?msg={enc_msg}"

            if not anonymous and sender_name:
                enc_sender = encode_data(sender_name)
                final_link += f"&from={enc_sender}"

            st.success("💖 Your surprise is ready!")

            # --- SHOW LINK ---
            st.code(final_link, language="text")

            # --- QR CODE ---
            qr_img = generate_qr(final_link)
            st.image(qr_img, caption="📱 Scan to open the surprise")

            st.info("Share the link or QR code with your crush 💌")
