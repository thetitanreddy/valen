import streamlit as st
import qrcode
import io
import base64
import secrets

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
        st.error("🚫 Public link generation is unavailable.")
        st.stop()

    if "localhost" in host or "127.0.0.1" in host:
        st.error("🚫 Localhost links are disabled.")
        st.info("Deploy on Streamlit Cloud to enable sharing.")
        st.stop()

    return f"{proto}://{host}"

# ---------------- QR GENERATOR ----------------
def generate_qr(data):
    qr = qrcode.make(data)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()

# ---------------- UI ----------------
st.title("💘 Cupid's Surprise")
st.caption("Anonymous Crush Confession Generator")

anonymous_mode = st.toggle("Anonymous Crush Mode 🕶️", value=True)

message = st.text_area(
    "💌 Write your message",
    placeholder="Someone secretly likes you...",
    max_chars=300
)

if st.button("💘 Generate Surprise"):
    if not message.strip():
        st.warning("Please write a message")
        st.stop()

    base_url = get_public_base_url()

    token = secrets.token_urlsafe(8)

    encoded_msg = base64.urlsafe_b64encode(message.encode()).decode()

    share_link = f"{base_url}/?c={token}&m={encoded_msg}"

    st.success("🎉 Your surprise link is ready!")

    st.code(share_link, language="text")

    qr_bytes = generate_qr(share_link)
    st.image(qr_bytes, caption="📱 Scan to open", width=220)

    st.info("🔒 Identity remains hidden. Message only!")

# ---------------- MESSAGE VIEW MODE ----------------
query = st.query_params

if "m" in query:
    try:
        decoded = base64.urlsafe_b64decode(query["m"]).decode()
        st.divider()
        st.subheader("💖 You received a secret message")
        st.success(decoded)
        st.caption("Someone has a crush on you 😉")
    except Exception:
        st.error("Invalid or broken link")
