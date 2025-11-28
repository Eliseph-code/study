import streamlit as st
import json
from dotenv import load_dotenv
load_dotenv()
import os
from datetime import datetime
from pathlib import Path
from google import genai
import base64
import mimetypes
import shutil

# ---------- AI-client ----------
def make_client():
    """Gebruik user-key of fallback .env/secrets key"""
    user_key = st.session_state.get("user_key") or os.getenv("GEMINI_API_KEY")
    if not user_key:
        return None
    try:
        return genai.Client(api_key=user_key)
    except Exception:
        return None

# ---------- Data ----------
DATA_FILE = Path("study_data.json")
UPLOAD_ROOT = Path("uploads")
UPLOAD_ROOT.mkdir(exist_ok=True)

def get_onderwerp_folder(vak: str, hoofdstuk: str, onderwerp: str) -> Path:
    safe_v = vak.replace(" ", "_")
    safe_h = hoofdstuk.replace(" ", "_")
    safe_o = onderwerp.replace(" ", "_")
    folder = UPLOAD_ROOT / f"{safe_v}_{safe_h}_{safe_o}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder

def delete_onderwerp_files(vak: str, hoofdstuk: str, onderwerp: str):
    folder = get_onderwerp_folder(vak, hoofdstuk, onderwerp)
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)

def load_data():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------- UI-stijl ----------
st.set_page_config(page_title="Studeren met AI", layout="wide")
st.markdown("""
<style>
html, body, .stApp {background-color:#fff!important;color:#000!important;}
.stButton>button {
  background:white!important;color:#2d6cdf!important;
  border:2px solid #2d6cdf!important;border-radius:6px;padding:0.4em 0.8em;
}
.stButton>button:hover {background:#2d6cdf!important;color:white!important;}
</style>
""", unsafe_allow_html=True)

st.title("📚 Studeren met AI")

# ---------- API-key invoer ----------
key_input = st.text_input("Voer je eigen Gemini-API-key in:", type="password")
if key_input:
    st.session_state["user_key"] = key_input
client = make_client()

if client:
    st.success("✅ API-key geladen en verbinding gemaakt.")
else:
    st.warning("🔑 Voer een geldige Gemini-API-key in om de AI-functies te gebruiken.")

data = load_data()

# ---------- Hulp-functie voor veilige upload ----------
def handle_uploads(upload_widget_key, vak, hoofdstuk, onderwerp):
    """Bewaar nieuwe uploads één keer en onthoud via session_state"""
    session_key = f"uploaded_{vak}_{hoofdstuk}_{onderwerp}"
    if session_key not in st.session_state:
        st.session_state[session_key] = []
    upload_files = st.file_uploader(
        "📎 Voeg bestanden toe (afbeelding / PDF)",
        type=["png", "jpg", "jpeg", "pdf"],
        accept_multiple_files=True,
        key=upload_widget_key,
    )
    folder = get_onderwerp_folder(vak, hoofdstuk, onderwerp)
    new_files = []
    for uf in upload_files:
        dest = folder / uf.name
        if not dest.exists():
            with open(dest, "wb") as f:
                f.write(uf.getbuffer())
            mime, _ = mimetypes.guess_type(dest.name)
            meta = {"path": str(dest), "name": uf.name,
                    "mime_type": mime or "application/octet-stream"}
            st.session_state[session_key].append(meta)
            new_files.append(meta)
    return st.session_state[session_key]

# ---------- Rest van je app-logica ----------
# (hier laat je al je bestaande code voor vak/hoofdstuk/onderwerp staan;
#  gebruik de nieuwe functie handle_uploads() i.p.v. de oude upload-lus.)

# Voorbeeld van gebruik in onderwerp-toevoegen:
# files_meta = handle_uploads("new_topic_uploads", selected_vak, selected_hoofdstuk, new_topic.strip())
# onderwerpen.append({...,"files": files_meta,...})
# save_data(data)

# De rest van je AI-oefensom-sectie blijft identiek; je hoeft daar niets te wijzigen.
