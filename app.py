# app.py (clean version)
import streamlit as st
from io import BytesIO
from datetime import datetime
import json
import base64
import os
import tempfile
import traceback
from PyPDF2 import PdfReader
from supabase import create_client, Client

try:
    import openai
except Exception:
    openai = None

st.set_page_config(page_title="CBSE NotesHub — Teacher Upload", layout="wide")

# ---------- CONFIG ----------
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE = st.secrets.get("SUPABASE_SERVICE_ROLE") or os.getenv("SUPABASE_SERVICE_ROLE")
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ Missing Supabase credentials. Please set SUPABASE_URL and SUPABASE_KEY in Streamlit Secrets.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE) if SUPABASE_SERVICE_ROLE else supabase

# ---------- CONSTANTS ----------
PLACEHOLDER_MP3_B64 = (
    "SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU2LjExLjEwMAAAAAAAAAAAAAAA//tQxAADB"
    "AAAAAABP/7UMQAAEwAAAAAAAE8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
)

# ---------- UTILITIES ----------
def upload_bytes_to_supabase(bucket: str, path: str, data: bytes, content_type="application/octet-stream"):
    """Upload bytes to Supabase and return a public URL."""
    client = supabase_admin if supabase_admin else supabase

    try:
        client.storage.create_bucket(bucket)
    except Exception:
        pass

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(path)[1]) as tmp:
            tmp.write(data)
            tmp.flush()
            tmp_path = tmp.name

        client.storage.from_(bucket).upload(path=path, file=tmp_path, file_options={"content-type": content_type})

        # handle all possible return formats
        public = client.storage.from_(bucket).get_public_url(path)
        if isinstance(public, dict):
            return public.get("publicURL") or public.get("public_url")
        if hasattr(public, "public_url"):
            return getattr(public, "public_url")
        if isinstance(public, str):
            return public
        return None

    except Exception as e:
        st.error("⚠️ Upload failed.")
        st.caption(f"Details: {repr(e)}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    return "\n\n".join([p.extract_text() or "" for p in reader.pages])

def generate_notes_via_openai(class_name, subject, chapter, topic, text):
    if not openai or not OPENAI_KEY:
        return None
    openai.api_key = OPENAI_KEY
    prompt = open("prompts/llm_generate_notes.txt").read().format(
        class_name=class_name, subject=subject, chapter=chapter, topic=topic
    )
    prompt += "\n\nRESOURCE_TEXT:\n" + text[:30000]
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.0,
        )
        return json.loads(resp["choices"][0]["message"]["content"])
    except Exception as e:
        st.warning(f"⚠️ OpenAI generation failed: {e}")
        return None

def generate_notes_fallback(class_name, subject, chapter, topic):
    try:
        with open("notes/n_perceptron.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "id": "sample_fallback",
            "class": class_name,
            "subject": subject,
            "chapter": chapter,
            "topic": topic,
            "title": f"{topic} (sample)",
            "theory": [{"section_title": "Sample", "audio_segment_id": f"{topic}_s1", "text": "Sample fallback content."}],
            "learning_objectives": [], "examples": [], "quick_revision": [], "5_mcq": []
        }

def create_narration_segments(notes_json):
    segments = []
    for idx, sec in enumerate(notes_json.get("theory", []), start=1):
        segments.append({
            "segment_id": f"{notes_json.get('topic','topic')}_sec{idx}",
            "text": sec.get("text", "")[:600],
            "approx_duration_seconds": min(90, max(20, int(len(sec.get("text",""))/5))),
        })
    for i, q in enumerate(notes_json.get("quick_revision", [])[:3], start=len(segments)+1):
        segments.append({"segment_id": f"{notes_json.get('topic','topic')}_qr{i}", "text": q, "approx_duration_seconds": 20})
    return segments

def synthesize_placeholder_audio(segment):
    return base64.b64decode(PLACEHOLDER_MP3_B64)

# ---------- STREAMLIT UI ----------
st.title("📘 CBSE NotesHub — Teacher Upload Portal")
st.markdown("_Easily upload, auto-generate, and publish AI-powered CBSE notes._")

with st.form("upload_form"):
    col1, col2 = st.columns([2, 1])
    with col1:
        class_name = st.selectbox("Class", ["IX", "X", "XI", "XII"], index=2)
        subject = st.selectbox("Subject", ["Artificial Intelligence", "Informatics Practices", "Mathematics", "Computer Science"])
        chapter = st.text_input("Chapter", value="Introduction to Machine Learning")
        topic = st.text_input("Topic", value="Perceptron")
    with col2:
        uploaded_file = st.file_uploader("📂 Upload PDF (Teacher/Admin)", type=["pdf"])
        submit = st.form_submit_button("🚀 Upload & Generate")

if submit:
    if not uploaded_file:
        st.warning("⚠️ Please select a PDF file first.")
        st.stop()

    st.info("📄 Extracting text from PDF...")
    file_bytes = uploaded_file.getvalue()
    text = extract_text_from_pdf_bytes(file_bytes)
    st.success(f"✅ Extracted {len(text)} characters.")

    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    pdf_path = f"pdfs/{class_name}/{subject}/{topic}_{now}.pdf"

    pdf_url = upload_bytes_to_supabase("cbse-resources", pdf_path, file_bytes, content_type="application/pdf")
    if pdf_url:
        st.success(f"📘 **PDF Uploaded Successfully!** [View PDF]({pdf_url})")
    else:
        st.error("❌ PDF upload failed.")
        st.stop()

    st.info("🤖 Generating notes (or using fallback)...")
    notes_json = generate_notes_via_openai(class_name, subject, chapter, topic, text) or generate_notes_fallback(class_name, subject, chapter, topic)
    notes_json["source_pdf"] = pdf_url
    notes_json["uploaded_at"] = now

    notes_bytes = json.dumps(notes_json, ensure_ascii=False, indent=2).encode("utf-8")
    notes_path = f"notes/{class_name}/{subject}/{topic}_{now}.json"
    notes_url = upload_bytes_to_supabase("cbse-resources", notes_path, notes_bytes, content_type="application/json")

    if notes_url:
        st.success(f"🧾 **Notes JSON Saved!** [View JSON]({notes_url})")

    segments = create_narration_segments(notes_json)
    st.info(f"🎙️ Generated {len(segments)} audio segments...")

    audio_urls = []
    for seg in segments:
        audio_bytes = synthesize_placeholder_audio(seg)
        seg_path = f"audio/{class_name}/{subject}/{seg['segment_id']}.mp3"
        audio_url = upload_bytes_to_supabase("cbse-resources", seg_path, audio_bytes, content_type="audio/mpeg")
        audio_urls.append({"segment_id": seg["segment_id"], "url": audio_url})

    st.success("🔊 **Audio Segments Uploaded Successfully!**")
    for seg in audio_urls:
        st.markdown(f"- {seg['segment_id']} → [🎧 Play Audio]({seg['url']})")

    segs_bytes = json.dumps(segments, ensure_ascii=False, indent=2).encode("utf-8")
    segs_path = f"audio/{class_name}/{subject}/{topic}_{now}_segments.json"
    segs_url = upload_bytes_to_supabase("cbse-resources", segs_path, segs_bytes, content_type="application/json")
    if segs_url:
        st.success(f"📑 **Audio Segments Metadata Stored!** [View JSON]({segs_url})")

    st.balloons()
    st.success("✅ Resource Created! Students can access all content via shared URLs.")

st.markdown("---")
st.caption("© CBSE NotesHub | Streamlit + Supabase + OpenAI | Prototype for AI-integrated education.")
