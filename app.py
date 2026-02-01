import streamlit as st
import qrcode
import io
import base64
import secrets
import time
from datetime import datetime, timedelta

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Cupid's Surprise 💘",
    page_icon="💌",
    layout="centered"
)

# ---------------- SESSION STATE ----------------
if "opened_links" not in st.session_state:
    st.session_state.opened_links = set()

# ---------------- THEME TOGGLE ----------------
theme = st.toggle("🌗 Dark Mode", value=False)

def apply_theme(dark=False):
    bg = "#0e1117" if dark else "#ffe6e6"
    card = "#161b22" if dark else "#ffffff"
    text = "#f0f6fc" if dark else "#000000"

    st.markdown(f"""
    <style>
    .stApp {{
        background-color: {bg};
    }}
    .card {{
        background-color: {card};
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        color: {text};
        box-shadow: 0px 10px 30px rgba(0,0,0,0.2);
    }}
    </style>
    """, unsafe_allow_html=True)

apply_theme(theme)

# ---------------- PUBLIC URL ----------------
def get_public_base_url():
    headers = st.context.headers
    host = headers.get("host")
    proto = headers.get("x-forwarded-proto", "https")

    if not host or "localhost" in host:
        st.error("🚫 Public sharing only works on Streamlit Cloud")
        st.stop()

    return f"{proto}://{host}"

# ---------------- QR ----------------
def generate_qr(data):
    qr = qrcode.make(data)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()

# ---------------- QUERY PARAMS ----------------
query = st.query_params

# ---------------- MESSAGE VIEW MODE ----------------
if "m" in query and "e" in query and "id" in query:
    link_id = query["id"]

    # One-time view check
    if link_id in st.session_state.opened_links:
        st.error("💔 This surprise has already been opened.")
        st.stop()

    expiry_time = datetime.fromtimestamp(int(query["e"]))
    now = datetime.now()

    if now > expiry_time:
        st.error("⏳ This surprise has expired.")
        st.stop()

    # Countdown
    remaining = int((expiry_time - now).total_seconds())

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("💖 You received a secret message")

    timer = st.empty()
    msg_box = st.empty()

    while remaining > 0:
        mins, secs = divmod(remaining, 60)
        timer.markdown(f"⏳ **Expires in {mins:02d}:{secs:02d}**")
        time.sleep(1)
        remaining -= 1

    try:
        decoded = base64.urlsafe_b64decode(query["m"]).decode()
        msg_box.success(decoded)
        st.caption("Someone secretly likes you 😉")

        # Mark as opened
        st.session_state.opened_links.add(link_id)

    except:
        st.error("Invalid message")

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ---------------- CREATOR MODE ----------------
st.title("💘 Cupid's Surprise")
st.caption("Anonymous • One-time • Expiring Confessions")

message = st.text_area(
    "💌 Write your message",
    placeholder="Someone secretly likes you...",
    max_chars=300
)

expiry_minutes = st.selectbox(
    "⏱ Link expiry time",
    [5, 10, 30, 60, 1440],
    format_func=lambda x: f"{x} minutes" if x < 60 else f"{x//60} hour(s)"
)

if st.button("💘 Generate Surprise"):
    if not message.strip():
        st.warning("Please write a message")
        st.stop()

    base_url = get_public_base_url()
    link_id = secrets.token_urlsafe(8)

    encoded_msg = base64.urlsafe_b64encode(message.encode()).decode()
    expiry_ts = int((datetime.now() + timedelta(minutes=expiry_minutes)).timestamp())

    share_link = f"{base_url}/?id={link_id}&m={encoded_msg}&e={expiry_ts}"

    st.success("🎉 Your surprise link is ready!")

    st.code(share_link)

    qr = generate_qr(share_link)
    st.image(qr, caption="📱 Scan to open", width=220)

    st.info("🔒 Anonymous • One-time • Auto-expires")
