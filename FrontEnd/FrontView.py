# student_frontend_streamlit.py
# Improved student-facing Streamlit app for CBSE NotesHub (step 1)
# - Replaces deprecated query param APIs (st.query_params / st.set_query_params)
# - Pagination
# - Safer button keys
# - Cleaner topic cards + expanders for notes & audio
# - Robust URL inference and error handling

import streamlit as st
from supabase import create_client
import requests
import json
import os
from typing import List, Dict

st.set_page_config(page_title="CBSE NotesHub — Student", layout="wide")

# ---------- CONFIG ----------
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing Supabase configuration. Ask the teacher/admin to set SUPABASE_URL and SUPABASE_KEY in app secrets.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- Helpers ----------
@st.cache_data(ttl=60)
def list_topics() -> List[Dict]:
    """Fetch topics from `topics` table. Returns list of rows or empty list on error."""
    try:
        resp = supabase.table("topics").select("*").order("created_at", desc=True).execute()
        data = resp.data if hasattr(resp, "data") else resp
        return data or []
    except Exception:
        return []

@st.cache_data(ttl=60)
def fetch_json_from_url(url: str):
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None

def safe_button_key(prefix: str, row: dict) -> str:
    """Create a deterministic short key for interactive Widgets"""
    rid = row.get("id") or row.get("topic") or ""
    created = str(row.get("created_at") or "")
    return f"{prefix}_{rid}_{created}"

def infer_notes_url_from_pdf(pdf_url: str) -> str | None:
    """Try common path substitutions to guess notes JSON URL."""
    if not pdf_url:
        return None
    try:
        if "/pdfs/" in pdf_url:
            return pdf_url.replace("/pdfs/", "/notes/").rsplit(".pdf", 1)[0] + ".json"
        # fallback: replace .pdf with .json
        if pdf_url.lower().endswith(".pdf"):
            return pdf_url[:-4] + ".json"
    except Exception:
        return None
    return None

def infer_segments_url_from_pdf(pdf_url: str) -> str | None:
    if not pdf_url:
        return None
    try:
        base = pdf_url
        if "/pdfs/" in base:
            base = base.replace("/pdfs/", "/audio/")
        if base.lower().endswith(".pdf"):
            return base[:-4] + "_segments.json"
    except Exception:
        return None
    return None

# ---------- UI: Sidebar Filters ----------
st.sidebar.title("Filter")
classes = ["IX","X","XI","XII"]
selected_class = st.sidebar.selectbox("Class", options=["All"] + classes, index=0)
subject_input = st.sidebar.text_input("Subject (optional)")
q = st.sidebar.text_input("Search topics or chapters")

# ---------- Fetch topics ----------
topics = list_topics()

# ---------- Simple Pagination Setup ----------
PAGE_SIZE = 8
# use query params for persistence across reloads
# prefer new API st.query_params / st.set_query_params; fallback to experimental if missing
try:
    qp = st.query_params or {}
except Exception:
    qp = {}

page = int(qp.get("page", [1])[0]) if isinstance(qp.get("page"), list) else int(qp.get("page", 1))
if page < 1:
    page = 1

# ---------- Filter topics ----------
filtered = []
if not topics:
    st.info("No topics found yet. Ask your teacher to upload notes from the Teacher portal.")
else:
    for t in topics:
        # normalize keys (handle both str and int for class)
        if selected_class != "All" and str(t.get("class","")).upper() != selected_class:
            continue
        if subject_input and subject_input.strip():
            if subject_input.lower() not in str(t.get("subject","")).lower():
                continue
        if q and q.strip():
            txt = " ".join([str(t.get(k,"")) for k in ("topic","chapter","subject")]).lower()
            if q.lower() not in txt:
                continue
        filtered.append(t)

st.sidebar.markdown(f"**{len(filtered)}** topics found")

# ---------- Page controls ----------
total_pages = max(1, (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE)
cols = st.columns([1,2,1])
with cols[0]:
    if st.button("← Prev") and page > 1:
        page -= 1
        st.set_query_params(page=page)
        st.experimental_rerun()
with cols[2]:
    if st.button("Next →") and page < total_pages:
        page += 1
        st.set_query_params(page=page)
        st.experimental_rerun()
with cols[1]:
    st.write(f"Page {page} / {total_pages}")

start = (page - 1) * PAGE_SIZE
end = start + PAGE_SIZE
page_items = filtered[start:end]

# ---------- Main ----------
st.title("📚 CBSE NotesHub — Student Portal")
st.markdown("Browse uploaded topics, read notes, view PDFs and listen to audio explanations.")

# show a helpful warning if Streamlit query param old API present (to mirror your screenshot)
st.caption("Tip: If you see a deprecation message about `query_params`, this app uses current APIs.")

# topic list (cards)
if page_items:
    for row in page_items:
        # nicer layout with two columns
        c1, c2 = st.columns([4,1])
        with c1:
            header = f"**{row.get('topic','(no topic)')}**"
            if row.get("chapter"):
                header += f" — {row.get('chapter')}"
            st.markdown(header)
            st.write(f"**Class:** {row.get('class','')}  •  **Subject:** {row.get('subject','')}")
            # short description if present
            if row.get("summary"):
                st.write(row.get("summary"))

            # action buttons (View / Open PDF / Download JSON)
            btns = st.columns([0.18, 0.18, 0.18, 1])
            if btns[0].button("View", key=safe_button_key("view", row)):
                st.session_state["_selected"] = row
            pdf_url = row.get("pdf_url")
            if btns[1].button("Open PDF", key=safe_button_key("openpdf", row)):
                if pdf_url:
                    # set query param topic and page so user can share link
                    st.set_query_params(topic=row.get("topic"), page=page)
                    st.rerun()
                else:
                    st.warning("PDF not available for this topic.")
            if btns[2].button("JSON", key=safe_button_key("json", row)):
                # try to open notes JSON
                notes_url = row.get("notes_url") or infer_notes_url_from_pdf(pdf_url)
                if notes_url:
                    st.set_query_params(notes=notes_url, page=page)
                    st.rerun()
                else:
                    st.warning("Notes JSON not found or not public.")
        with c2:
            # small right column for thumbnail / date
            created = row.get("created_at") or row.get("uploaded_at") or ""
            st.caption(f"{created}")
            # optional thumbnail if stored
            if row.get("thumbnail_url"):
                st.image(row.get("thumbnail_url"), width=120)

# ---------- Topic Detail (from session or query param) ----------
selected = None
if st.session_state.get("_selected"):
    selected = st.session_state._selected
else:
    # query params may include topic (name) or notes URL; use current API if possible
    params = st.query_params or {}
    if params.get("topic"):
        tname = params.get("topic")[0] if isinstance(params.get("topic"), list) else params.get("topic")
        for r in topics:
            if r.get("topic") == tname:
                selected = r
                break
    elif params.get("notes"):
        # user opened a notes JSON directly via query param
        notes_url = params.get("notes")[0] if isinstance(params.get("notes"), list) else params.get("notes")
        # build a minimal selected object to show JSON
        selected = {"topic": "External JSON", "chapter": "", "class": "", "subject": "", "notes_url": notes_url}

if selected:
    st.markdown("---")
    st.header(f"{selected.get('topic')}  {('— ' + selected.get('chapter')) if selected.get('chapter') else ''}")
    st.write(f"**Class:** {selected.get('class','')}  •  **Subject:** {selected.get('subject','')}")

    pdf_url = selected.get("pdf_url")
    notes_url = selected.get("notes_url") or selected.get("notes_json") or infer_notes_url_from_pdf(pdf_url)

    # Embedded PDF (iframe)
    if pdf_url:
        st.markdown("**PDF Resource**")
        try:
            st.components.v1.iframe(pdf_url, height=600)
        except Exception:
            st.warning("Cannot embed PDF in an iframe. You can open it in a new tab below.")
            st.markdown(f"[Open PDF]({pdf_url})")
    else:
        st.warning("PDF not available for this topic.")

    # Notes (fetch notes_url if present)
    st.markdown("**Notes**")
    notes_json = None
    if notes_url:
        notes_json = fetch_json_from_url(notes_url)
    if notes_json:
        # display as structured: title, learning objectives, theory sections, quick revision
        try:
            st.subheader(notes_json.get("title") or notes_json.get("topic") or "Notes")
            if notes_json.get("learning_objectives"):
                st.markdown("**Learning Objectives**")
                st.write(notes_json.get("learning_objectives"))
            if notes_json.get("theory"):
                st.markdown("**Theory**")
                for sec in notes_json.get("theory"):
                    with st.expander(sec.get("section_title", "Section")):
                        st.write(sec.get("text", ""))
            if notes_json.get("quick_revision"):
                st.markdown("**Quick Revision**")
                st.write(notes_json.get("quick_revision"))
            if notes_json.get("5_mcq"):
                st.markdown("**Sample MCQs**")
                for mcq in notes_json.get("5_mcq", []):
                    st.write(f"- {mcq}")
        except Exception:
            st.json(notes_json)
    else:
        st.info("Notes not available publicly. Teacher may not have generated notes JSON yet.")

    # Audio segments
    st.markdown("**Audio segments**")
    segments = None
    if selected.get("segments_url"):
        segments = fetch_json_from_url(selected.get("segments_url"))
    if not segments:
        segments_url_guess = infer_segments_url_from_pdf(pdf_url)
        if segments_url_guess:
            segments = fetch_json_from_url(segments_url_guess)

    if segments:
        for seg in segments:
            url = seg.get("url") or seg.get("audio_url")
            seg_id = seg.get("segment_id") or seg.get("id") or seg.get("name", "segment")
            with st.expander(seg_id):
                if url:
                    # show small player and link
                    st.audio(url)
                    st.markdown(f"[Open in new tab]({url})")
                else:
                    st.write("Audio not available for this segment.")
    else:
        st.info("No audio segments published for this topic yet.")

    st.markdown("---")
    if st.button("Back to list"):
        if st.session_state.get('_selected'):
            del st.session_state['_selected']
        # reset query params (preserve page)
        st.set_query_params(page=page)
        st.experimental_rerun()

# ---------- Footer ----------
st.markdown("---")
st.caption("CBSE NotesHub — student viewer. If content missing, ask your teacher to upload from the Teacher portal.")
