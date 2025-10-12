# student_frontend_streamlit.py
# A student-facing Streamlit app for CBSE NotesHub
# Features:
# - Browse topics by Class / Subject
# - Search topics
# - Topic detail page: embedded PDF, notes view, audio playlist (playable links)
# - Uses Supabase anon key (read-only) stored in Streamlit Secrets

import streamlit as st
from supabase import create_client
import requests
import json
import os

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
def list_topics():
    """Fetch topics from `topics` table. Returns list of rows or fallback seed."""
    try:
        resp = supabase.table("topics").select("*").order("created_at", desc=True).execute()
        data = resp.data if hasattr(resp, "data") else resp
        if not data:
            return []
        return data
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

# ---------- UI: Sidebar Filters ----------
st.sidebar.title("Filter")
classes = ["IX","X","XI","XII"]
selected_class = st.sidebar.selectbox("Class", options=["All"]+classes, index=0)
subject_input = st.sidebar.text_input("Subject (optional)")
q = st.sidebar.text_input("Search topics or chapters")

# ---------- Main ----------
st.title("📚 CBSE NotesHub — Student Portal")
st.markdown("Browse uploaded topics, read notes, view PDFs and listen to audio explanations.")

topics = list_topics()
if not topics:
    st.info("No topics found yet. Ask your teacher to upload notes from the Teacher portal.")
else:
    # Filter topics
    filtered = []
    for t in topics:
        if selected_class != "All" and str(t.get("class","")).upper() != selected_class:
            continue
        if subject_input and subject_input.lower() not in str(t.get("subject","")).lower():
            continue
        if q:
            txt = " ".join([str(t.get(k,"") ) for k in ("topic","chapter","subject")]).lower()
            if q.lower() not in txt:
                continue
        filtered.append(t)

    st.sidebar.markdown(f"**{len(filtered)}** topics found")

    # Display list
    for row in filtered:
        col1, col2 = st.columns([3,1])
        with col1:
            st.subheader(f"{row.get('topic')} — {row.get('chapter')}")
            st.write(f"**Class:** {row.get('class')}  •  **Subject:** {row.get('subject')}")
            buttons = st.columns([0.2,0.2,3])
            if buttons[0].button("View", key=f"view_{row.get('topic')}_{row.get('created_at')}"):
                st.session_state._selected = row
            if buttons[1].button("Open", key=f"open_{row.get('topic')}_{row.get('created_at')}"):
                pdf_url = row.get("pdf_url")
                if pdf_url:
                    st.experimental_set_query_params(topic=row.get('topic'))
                    st.experimental_rerun()
        with col2:
            st.write("")

# ---------- Topic Detail (if selected in session or query param) ----------
selected = None
if st.session_state.get("_selected"):
    selected = st.session_state._selected
else:
    params = st.experimental_get_query_params()
    if params.get("topic"):
        tname = params.get("topic")[0]
        for r in topics:
            if r.get("topic") == tname:
                selected = r
                break

if selected:
    st.markdown("---")
    st.header(f"{selected.get('topic')} — {selected.get('chapter')}")
    st.write(f"**Class:** {selected.get('class')}  •  **Subject:** {selected.get('subject')}")

    pdf_url = selected.get("pdf_url")
    notes_url = selected.get("notes_url") or selected.get("notes_json") or None

    # Embedded PDF (iframe)
    if pdf_url:
        st.markdown("**PDF Resource**")
        st.components.v1.iframe(pdf_url, height=600)
    else:
        st.warning("PDF not available for this topic.")

    # Notes (fetch notes_url if present or try to find notes in storage naming)
    st.markdown("**Notes**")
    notes_json = None
    if selected.get("notes_url"):
        notes_json = fetch_json_from_url(selected.get("notes_url"))
    else:
        # try to infer notes from same folder: replace '/pdfs/' with '/notes/' and .pdf -> .json
        if pdf_url and ".pdf" in pdf_url:
            maybe = pdf_url.replace("/pdfs/", "/notes/").rsplit(".pdf",1)[0] + ".json"
            notes_json = fetch_json_from_url(maybe)

    if notes_json:
        st.json(notes_json)
    else:
        st.info("Notes not available publicly. Teacher may not have generated notes JSON yet.")

    # Audio segments
    st.markdown("**Audio segments**")
    # look for segments JSON in storage path logic
    segments = None
    if selected.get("segments_url"):
        segments = fetch_json_from_url(selected.get("segments_url"))
    if not segments and pdf_url and ".pdf" in pdf_url:
        base = pdf_url.replace('/pdfs/','/audio/').rsplit('.pdf',1)[0]
        candidate = base + "_segments.json"
        segments = fetch_json_from_url(candidate)

    if segments:
        for seg in segments:
            url = seg.get("url") or seg.get("audio_url")
            seg_id = seg.get("segment_id")
            st.markdown(f"**{seg_id}**")
            if url:
                st.audio(url)
            else:
                st.write("Audio not available for this segment.")
    else:
        st.info("No audio segments published for this topic yet.")

    st.markdown("---")
    if st.button("Back to list"):
        if st.session_state.get('_selected'):
            del st.session_state['_selected']
        st.experimental_set_query_params()
        st.experimental_rerun()

# ---------- Footer ----------
st.markdown("---")
st.caption("CBSE NotesHub — student viewer. If content missing, ask your teacher to upload from the Teacher portal.")
