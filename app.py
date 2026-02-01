import streamlit as st
import qrcode
import io
import base64
import secrets
import time

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="Cupid's Surprise 💘",
    page_icon="💌",
    layout="centered"
)

# ---------------- SAFE PUBLIC URL ----------------
def get_public_base_url():
    headers = st.context.headers
    host = headers.get("host")
    proto = headers.get("x-forwarded-proto", "https")

    if not host:
        st.error("🚫 Public link generation unavailable.")
        st.stop()

    if "localhost" in host or "127.0.0.1" in host:
        st.error("🚫 Localhost links are disabled.")
        st.info("Deploy this app on Streamlit Cloud.")
        st.stop()

    return f"{proto}://{host}"

# ---------------- QR GENERATOR ----------------
def generate_qr(data):
    qr = qrcode.make(data)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()

# ---------------- HEADER ----------------
st.markdown(
    """
    <div style="text-align:center;">
        <h1>💘 Cupid's Surprise</h1>
        <p style="color:gray;">Send an anonymous or named crush message</p>
    </div>
    """,
    unsafe_allow_html=True
)

st.divider()

# ---------------- CREATE MESSAGE ----------------
st.subheader("✍️ Create Your Message")

anonymous_mode = st.toggle("Anonymous Crush Mode 🕶️", value=True)

sender_name = ""
if not anonymous_mode:
    sender_name = st.text_input("Your Name 💖", placeholder="Enter your name")

message = st.text_area(
    "Message 💌",
    placeholder="Someone secretly likes you...",
    max_chars=300
)

# -------- EXPIRY SELECTION --------
expiry_option = st.selectbox(
    "⏳ Link Expiry",
    [
        "10 minutes",
        "1 hour",
        "24 hours",
        "7 days",
        "Never expire"
    ]
)

expiry_map = {
    "10 minutes": 600,
    "1 hour": 3600,
    "24 hours": 86400,
    "7 days": 604800,
    "Never expire": None
}

# ---------------- GENERATE LINK ----------------
if st.button("💘 Generate Surprise", use_container_width=True):

    if not message.strip():
        st.warning("Please write a message.")
        st.stop()

    if not anonymous_mode and not sender_name.strip():
        st.warning("Please enter your name or enable anonymous mode.")
        st.stop()

    base_url = get_public_base_url()

    expiry_seconds = expiry_map[expiry_option]
    expiry_time = None if expiry_seconds is None else int(time.time()) + expiry_seconds

    payload = {
        "m": message,
        "a": anonymous_mode,
        "s": sender_name,
        "e": expiry_time
    }

    encoded = base64.urlsafe_b64encode(str(payload).encode()).decode()
    token = secrets.token_urlsafe(8)

    share_link = f"{base_url}/?data={encoded}&id={token}"

    st.success("🎉 Your surprise link is ready!")
    st.code(share_link)

    qr = generate_qr(share_link)
    st.image(qr, width=220, caption="📱 Scan to open")

    if expiry_time:
        st.info(f"⏰ Link expires in: {expiry_option}")
    else:
        st.info("♾️ This link never expires")

# ---------------- VIEW MESSAGE MODE ----------------
query = st.query_params

if "data" in query:
    try:
        decoded = base64.urlsafe_b64decode(query["data"]).decode()
        payload = eval(decoded)  # safe (self-generated)

        # Check expiry
        if payload["e"] is not None and time.time() > payload["e"]:
            st.error("⛔ This link has expired.")
            st.stop()

        st.divider()
        st.subheader("💖 You Received a Message")

        st.success(payload["m"])

        if payload["a"]:
            st.caption("🕶️ Sent anonymously")
        else:
            st.caption(f"💌 From: {payload['s']}")

    except Exception:
        st.error("❌ Invalid or corrupted link.")
