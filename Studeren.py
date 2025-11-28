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


# ---------- AI client ----------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

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


st.set_page_config(page_title="Studeren met AI", layout="wide")

# ---------- Thema ----------
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

# ---------- API Key ----------
user_key = st.text_input("Voer je eigen Gemini API key in:", type="password")
if user_key:
    client = genai.Client(api_key=user_key)
    st.success("✅ API key geladen!")
else:
    st.warning("🔑 Voeg je Gemini API key toe om de AI te gebruiken.")

data = load_data()

# -----------------------------------------------------------
# 🧠 Vakken / Hoofdstukken / Onderwerpen
# -----------------------------------------------------------
col_vak, col_hoofdstuk, col_onderwerp = st.columns(3)

# ===== VAK =====
with col_vak:
    st.markdown("### 🧠 Vak")
    vakken = list(data.keys())
    selected_vak = st.selectbox("Kies vak", vakken) if vakken else None
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("➕", key="add_vak_btn"):
            st.session_state["add_vak"] = True
    with col2:
        if selected_vak and st.button("✏️", key="edit_vak_btn"):
            st.session_state["edit_vak"] = True

    if st.session_state.get("add_vak"):
        new_vak = st.text_input("Naam nieuw vak:")
        if st.button("Opslaan vak"):
            if not new_vak.strip():
                st.error("Voer een naam in.")
            elif new_vak in data:
                st.warning("Bestaat al.")
            else:
                data[new_vak] = {"hoofdstukken": {}}
                save_data(data)
                st.success("Vak toegevoegd.")
                st.session_state.pop("add_vak")
                st.rerun()
        if st.button("Annuleer", key="cancel_vak"):
            st.session_state.pop("add_vak")
            st.rerun()

    if st.session_state.get("edit_vak") and selected_vak:
        new_name = st.text_input("Nieuwe naam voor vak:", value=selected_vak)
        if st.button("Opslaan wijziging vak"):
            if new_name.strip() and new_name != selected_vak:
                data[new_name] = data.pop(selected_vak)
                save_data(data)
                st.success("Vaknaam gewijzigd.")
                st.session_state.pop("edit_vak")
                st.rerun()

# ===== HOOFDSTUK =====
with col_hoofdstuk:
    st.markdown("### 📘 Hoofdstuk")
    selected_hoofdstuk = None
    if selected_vak:
        hoofdstukken = data[selected_vak]["hoofdstukken"]
        selected_hoofdstuk = st.selectbox("Kies hoofdstuk", list(hoofdstukken.keys())) if hoofdstukken else None
        if st.button("➕", key="add_hoofdstuk_btn"):
            st.session_state["add_hoofdstuk"] = True
        if st.session_state.get("add_hoofdstuk"):
            new_chapter = st.text_input("Naam nieuw hoofdstuk:")
            if st.button("Opslaan hoofdstuk"):
                if not new_chapter.strip():
                    st.error("Voer een naam in.")
                elif new_chapter in hoofdstukken:
                    st.warning("Bestaat al.")
                else:
                    hoofdstukken[new_chapter] = {"onderwerpen": []}
                    save_data(data)
                    st.success("Hoofdstuk toegevoegd.")
                    st.session_state.pop("add_hoofdstuk")
                    st.rerun()

# ===== ONDERWERP =====
with col_onderwerp:
    st.markdown("### 🧩 Onderwerp")
    selected_onderwerp = None
    if selected_vak and selected_hoofdstuk:
        onderwerpen = data[selected_vak]["hoofdstukken"][selected_hoofdstuk]["onderwerpen"]
        if onderwerpen:
            selected_onderwerp = st.selectbox("Kies onderwerp", [t["naam"] for t in onderwerpen])

        if st.button("➕", key="add_onderwerp_btn"):
            st.session_state["add_onderwerp"] = True

        if st.session_state.get("add_onderwerp"):
            new_topic = st.text_input("Naam nieuw onderwerp:")
            bron_text = st.text_area("Plak hier de tekst uit het bronboek:", height=200)

            upload_files = st.file_uploader(
                "📎 Voeg eventueel bestanden toe (afbeelding / PDF)",
                type=["png", "jpg", "jpeg", "pdf"],
                accept_multiple_files=True,
                key="new_topic_uploads"
            )

            if st.button("Opslaan onderwerp"):
                if not new_topic.strip():
                    st.error("Voer een naam in.")
                elif any(t["naam"] == new_topic for t in onderwerpen):
                    st.warning("Bestaat al.")
                elif not bron_text.strip():
                    st.error("Voeg bronboektekst toe.")
                else:
                    new_id = max((t["id"] for t in onderwerpen), default=0) + 1

                    files_meta = []
                    if upload_files:
                        folder = get_onderwerp_folder(selected_vak, selected_hoofdstuk, new_topic.strip())
                        for uf in upload_files:
                            dest = folder / uf.name
                            # ✅ voorkom dubbel schrijven
                            if not dest.exists():
                                with open(dest, "wb") as f:
                                    f.write(uf.getbuffer())
                            mime, _ = mimetypes.guess_type(dest.name)
                            # ✅ voorkom dubbele metadata
                            if not any(f["name"] == uf.name for f in files_meta):
                                files_meta.append({
                                    "path": str(dest),
                                    "name": uf.name,
                                    "mime_type": mime or "application/octet-stream",
                                })

                    onderwerpen.append({
                        "id": new_id,
                        "naam": new_topic.strip(),
                        "bron_text": bron_text.strip(),
                        "datum": datetime.now().isoformat(),
                        "files": files_meta,
                    })
                    save_data(data)
                    st.success("Onderwerp toegevoegd.")
                    st.session_state.pop("add_onderwerp")
                    st.rerun()

        # ===== BEWERK ONDERWERP =====
        if st.session_state.get("edit_onderwerp") and selected_onderwerp:
            onderwerp = next((t for t in onderwerpen if t["naam"] == selected_onderwerp), None)
            if onderwerp:
                if "files" not in onderwerp:
                    onderwerp["files"] = []
                new_name = st.text_input("Nieuwe naam onderwerp:", value=onderwerp["naam"])
                new_bron = st.text_area("Bewerk bronboektekst:", value=onderwerp.get("bron_text", ""), height=200)

                st.markdown("### 📎 Bestanden bij dit onderwerp")

                files = onderwerp.get("files", [])
                if files:
                    for idx, fmeta in enumerate(files):
                        colf1, colf2 = st.columns([4, 1])
                        with colf1:
                            mime = fmeta.get("mime_type", "")
                            path = fmeta.get("path", "")
                            name = fmeta.get("name", "")
                            if mime.startswith("image/") and os.path.exists(path):
                                st.image(path, caption=name, use_container_width=True)
                            elif os.path.exists(path):
                                with open(path, "rb") as fh:
                                    st.download_button(f"📄 {name}", fh, file_name=name, key=f"dl_{idx}")
                        with colf2:
                            if st.button("🗑️", key=f"del_{idx}"):
                                try:
                                    if os.path.exists(path):
                                        os.remove(path)
                                except Exception:
                                    pass
                                onderwerp["files"].pop(idx)
                                save_data(data)
                                st.success("Bestand verwijderd.")
                                st.rerun()
                else:
                    st.info("Nog geen bestanden gekoppeld.")

                # ➕ Nieuwe bestanden
                new_uploads = st.file_uploader(
                    "➕ Nieuwe bestanden toevoegen",
                    type=["png", "jpg", "jpeg", "pdf"],
                    accept_multiple_files=True,
                    key=f"edit_uploads_{onderwerp['id']}"
                )

                if new_uploads:
                    folder = get_onderwerp_folder(selected_vak, selected_hoofdstuk, new_name.strip())
                    existing_names = {f["name"] for f in onderwerp.get("files", [])}
                    for uf in new_uploads:
                        dest = folder / uf.name
                        if not dest.exists():
                            with open(dest, "wb") as f:
                                f.write(uf.getbuffer())
                        mime, _ = mimetypes.guess_type(dest.name)
                        if uf.name not in existing_names:
                            onderwerp["files"].append({
                                "path": str(dest),
                                "name": uf.name,
                                "mime_type": mime or "application/octet-stream",
                            })
                            existing_names.add(uf.name)
                    save_data(data)
                    st.success("Nieuwe bestanden toegevoegd.")
                    st.rerun()



# -----------------------------------------------------------
# ✨ Één oefensom met vragen a, b, c — met dynamische feedback
# -----------------------------------------------------------
st.markdown("---")

if selected_vak and selected_hoofdstuk and selected_onderwerp:
    st.header(f"Oefensom – {selected_onderwerp}")

    onderwerp_obj = next(
        (t for t in data[selected_vak]["hoofdstukken"][selected_hoofdstuk]["onderwerpen"]
         if t["naam"] == selected_onderwerp),
        None,
    )

    if onderwerp_obj and client:
        bron_text = onderwerp_obj.get("bron_text", "")
        files = onderwerp_obj.get("files", [])

        if st.button("🧠 Laat AI één oefensom met vragen a, b, c maken"):
            # 🧹 Reset alle relevante sessiegegevens
            for key in list(st.session_state.keys()):
                if key.startswith("ans_") or key.startswith("fb_") or key.startswith("single_exercise_"):
                    del st.session_state[key]

            # ⬆️ Verhoog de resetcounter om nieuwe input keys te forceren
            if "input_reset_counter" not in st.session_state:
                st.session_state["input_reset_counter"] = 0
            st.session_state["input_reset_counter"] += 1

            with st.spinner("AI maakt oefensom."):
                try:
                    basis_prompt = f"""
    Je bent een leraar {selected_vak.lower()}.
    Gebruik onderstaande brontekst en eventuele bijgevoegde bestanden om één oefensom te maken met drie deelvragen: a, b en c.
    1. Begin met een korte uitleg van de theorie.
    2. Schrijf daarna één oefenopgave met drie subvragen a, b en c.
    3. Formatteer als:
    'Oefening:
    a) ...
    b) ...
    c) ...'

    Brontekst:
    {bron_text[:6000]}
    """

                    beschrijving_bestanden = ""
                    if files:
                        beschrijving_bestanden = "Bij dit onderwerp horen de volgende bestanden (afbeeldingen / PDF's):\n"
                        for fmeta in files:
                            beschrijving_bestanden += f"- {fmeta.get('name', 'bestand')} ({fmeta.get('mime_type', '')})\n"

                    user_parts = [{"text": basis_prompt + "\n" + beschrijving_bestanden}]

                    inline_file_parts = []
                    for fmeta in files:
                        path = fmeta.get("path", "")
                        mime = fmeta.get("mime_type", "application/octet-stream")
                        if not os.path.exists(path):
                            continue
                        if mime.startswith("image/"):
                            with open(path, "rb") as f:
                                raw_bytes = f.read()
                            b64_data = base64.b64encode(raw_bytes).decode("utf-8")
                            inline_file_parts.append(
                                {
                                    "inline_data": {
                                        "mime_type": mime,
                                        "data": b64_data,
                                    }
                                }
                            )

                    contents = [
                        {
                            "role": "user",
                            "parts": user_parts + inline_file_parts,
                        }
                    ]

                    resp = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=contents,
                    )
                    ai_output = resp.text.strip()

                    st.session_state[
                        f"single_exercise_{selected_vak}_{selected_hoofdstuk}_{selected_onderwerp}"
                    ] = ai_output
                    st.success("✅ Nieuwe AI-oefensom aangemaakt!")
                except Exception as e:
                    st.error(f"Fout bij genereren: {e}")




    ex_key = f"single_exercise_{selected_vak}_{selected_hoofdstuk}_{selected_onderwerp}"
    # Zorg dat er een reset teller bestaat voor antwoordvelden
    if "input_reset_counter" not in st.session_state:
        st.session_state["input_reset_counter"] = 0

    if ex_key in st.session_state:
        st.markdown("""
            <style>
            .stTextInput input {
                background-color: #ffffff !important;
                color: black !important;
                border: 1px solid #ccc !important;
                border-radius: 6px;
                padding: 8px;
            }

            .stButton>button {
                background-color: white !important;
                color: #2d6cdf !important;
                border: 2px solid #2d6cdf !important;
                border-radius: 6px;
                padding: 0.4em 0.8em;
            }

            .stButton>button:hover {
                background-color: #2d6cdf !important;
                color: white !important;
            }

            h4 {
                margin-top: 1.2em;
                margin-bottom: 0.2em;
            }
            </style>
        """, unsafe_allow_html=True)

        st.markdown("### 📘 Theorie en oefensom")

        # Tekst van de AI-oefening
        oefening_tekst = st.session_state[ex_key]

        # Splits op a), b), c)
        import re
        delen = re.split(r"(?<=\n)a\)|(?<=\n)b\)|(?<=\n)c\)", oefening_tekst)

        if len(delen) >= 2:
            st.markdown(delen[0].strip())  # Inleiding / theorie

            subvragen = ["a", "b", "c"]
            for i, sub in enumerate(subvragen):
                vraagtekst = ""
                if i + 1 < len(delen):
                    vraagtekst = "a)" + delen[i + 1] if i == 0 else \
                                 "b)" + delen[i + 1] if i == 1 else \
                                 "c)" + delen[i + 1]

                # Vraagtekst
                st.markdown(f"<h4>✏️ Vraag {sub})</h4>", unsafe_allow_html=True)
                st.markdown(vraagtekst.strip())

                # Antwoordveld en knop
                cols = st.columns([8, 1])
                with cols[0]:
                    user_answer = st.text_input(
                        "",
                        key=f"ans_{sub}_{st.session_state['input_reset_counter']}"
                    )

                with cols[1]:
                    if st.button("✔️", key=f"check_{sub}"):
                        with st.spinner(f"AI controleert jouw antwoord voor vraag {sub}..."):
                            try:
                                check_prompt = f"""
Hieronder staat een oefensom met drie subvragen a, b en c:
{st.session_state[ex_key]}

De leerling geeft dit antwoord op vraag {sub}:
{user_answer}

Controleer alleen vraag {sub}.
Geef terug:
- CORRECT of NIET CORRECT
- het juiste antwoord
- een korte uitleg.
"""
                                resp2 = client.models.generate_content(
                                    model="gemini-2.0-flash",
                                    contents=check_prompt
                                )
                                st.session_state[f"fb_{sub}"] = resp2.text.strip()
                            except Exception as e:
                                st.error(f"Fout bij controle: {e}")

                # Feedback alleen tonen na klikken
                if f"fb_{sub}" in st.session_state:
                    st.markdown("**🧾 Feedback:**")
                    st.markdown(st.session_state[f"fb_{sub}"])

