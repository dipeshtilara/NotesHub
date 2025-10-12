# app.py (corrected)
import streamlit as st
from io import BytesIO
from datetime import datetime
import json
import base64
import os
import tempfile
import traceback

# PDF text extraction
from PyPDF2 import PdfReader

# Supabase client
from supabase import create_client, Client

# Optional OpenAI
try:
    import openai
except Exception:
    openai = None

st.set_page_config(page_title="CBSE NotesHub — Teacher Upload", layout="wide")

# ---------- CONFIG from Streamlit secrets or ENV ----------
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE = st.secrets.get("SUPABASE_SERVICE_ROLE") or os.getenv("SUPABASE_SERVICE_ROLE")
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
NOTEBOOKLM_KEY = st.secrets.get("NOTEBOOKLM_API_KEY") or os.getenv("NOTEBOOKLM_API_KEY")
TTS_KEY = st.secrets.get("TTS_API_KEY") or os.getenv("TTS_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("SUPABASE_URL and SUPABASE_KEY are required. Set them in Streamlit secrets.")
    st.stop()

# create two clients:
#  - anon client (used for reads / DB insert attempts with anon key)
#  - admin client (used for uploads if service_role key is present)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin = None
if SUPABASE_SERVICE_ROLE:
    try:
        supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)
    except Exception as e:
        st.warning(f"Could not create admin client: {e}")

# ---------- Helper utilities ----------
PLACEHOLDER_MP3_B64 = (
    # a tiny 1-second silent mp3 base64 (keeps audio player happy)
    "SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU2LjExLjEwMAAAAAAAAAAAAAAA//tQxAADB"
    "AAAAAABP/7UMQAAEwAAAAAAAE8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
)

def upload_bytes_to_supabase(bucket: str, path: str, data: bytes, content_type="application/octet-stream"):
    """
    Uploads bytes to Supabase Storage.
    Uses service role client if available (recommended). Writes bytes to a temporary file
    because storage3 expects a file path.
    Returns public URL on success, or None.
    """
    st.write("DEBUG: Using admin client?" , bool(supabase_admin))

    client = supabase_admin if supabase_admin is not None else supabase

    # ensure bucket exists (safe to ignore errors)
    try:
        client.storage.create_bucket(bucket)
    except Exception:
        pass

    # write bytes to a temporary file and upload via path (storage3 expects path)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(path)[1] or "") as tmp:
            tmp.write(data)
            tmp.flush()
            tmp_path = tmp.name

        # upload using file path (required by installed storage3)
        try:
            resp = client.storage.from_(bucket).upload(path=path, file=tmp_path, file_options={"content-type": content_type})
        except Exception as e:
            # surface readable error in streamlit and logs
            st.error("Upload failed; check logs for details.")
            st.write("Upload exception:", repr(e))
            # re-raise so full traceback lands in Streamlit logs (helpful for debugging)
            raise

                # get public url (handle all possible return shapes)
        try:
            public = client.storage.from_(bucket).get_public_url(path)
            st.write("DEBUG: get_public_url() returned:", public, type(public))

            # --- handle all Supabase SDK return variants ---
            if isinstance(public, dict):
                return public.get("publicURL") or public.get("public_url")
            if hasattr(public, "public_url"):
                return getattr(public, "public_url")
            if isinstance(public, str):
                # some SDK builds return a plain string
                return public

            # fallback for any other type
            return None

        except Exception as e:
            st.warning(f"Could not fetch public URL: {e}")
            return None


    finally:
        # cleanup temp file if created
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    return None


def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    texts = []
    for p in reader.pages:
        try:
            t = p.extract_text() or ""
            texts.append(t)
        except Exception:
            texts.append("")
    return "\n\n".join(texts)

def generate_notes_via_openai(class_name, subject, chapter, topic, resource_text):
    if not openai or not OPENAI_KEY:
        return None
    openai.api_key = OPENAI_KEY
    prompt = open("prompts/llm_generate_notes.txt").read().format(class_name=class_name, subject=subject, chapter=chapter, topic=topic)
    # Append resource text (trim if huge)
    prompt += "\n\nRESOURCE_TEXT:\n" + (resource_text[:30000])
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # change if you prefer another model
            messages=[{"role":"user","content":prompt}],
            max_tokens=1000,
            temperature=0.0
        )
        content = resp["choices"][0]["message"]["content"]
        # Expect JSON output — try parse
        return json.loads(content)
    except Exception as e:
        st.warning(f"OpenAI call failed: {e}")
        return None

def generate_notes_fallback(class_name, subject, chapter, topic):
    # returns the sample perceptron JSON as fallback
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
            "learning_objectives": [],
            "examples": [],
            "quick_revision": [],
            "5_mcq": []
        }

def create_narration_segments(notes_json):
    # Use NotebookLM prompt template if you want real integration.
    # For prototype, produce simple segments from theory sections.
    segments = []
    for idx, sec in enumerate(notes_json.get("theory", []), start=1):
        seg = {
            "segment_id": f"{notes_json.get('topic','topic')}_sec{idx}",
            "text": sec.get("text", "")[:600] + " ...",
            "approx_duration_seconds": min(90, max(20, int(len(sec.get("text",""))/5)))
        }
        segments.append(seg)
    # quick revisions as short segments
    for i, q in enumerate(notes_json.get("quick_revision", [])[:3], start=len(segments)+1):
        segments.append({
            "segment_id": f"{notes_json.get('topic','topic')}_qr{i}",
            "text": q,
            "approx_duration_seconds": 20
        })
    return segments

def synthesize_placeholder_audio(segment):
    # decode base64 placeholder and return as bytes
    b = base64.b64decode(PLACEHOLDER_MP3_B64)
    return b

# ---------- Streamlit UI ----------
st.title("CBSE NotesHub — Teacher Upload (Prototype)")
st.markdown("Upload a PDF, generate notes (OpenAI optional) and create audio segments. Files are stored in Supabase Storage.")

with st.form("upload_form"):
    col1, col2 = st.columns([2,1])
    with col1:
        class_name = st.selectbox("Class", ["IX", "X", "XI", "XII"], index=2)
        subject = st.selectbox("Subject", ["Artificial Intelligence", "Informatics Practices", "Mathematics", "Computer Science"])
        chapter = st.text_input("Chapter", value="Introduction to Machine Learning")
        topic = st.text_input("Topic", value="Perceptron")
    with col2:
        uploaded_file = st.file_uploader("Upload PDF (teacher/admin)", type=["pdf"], accept_multiple_files=False)
        submit = st.form_submit_button("Upload & Create Resource")
if submit:
    if not uploaded_file:
        st.warning("Please select a PDF to upload.")
    else:
        file_bytes = uploaded_file.getvalue()
        st.info("Extracting text from PDF...")
        text = extract_text_from_pdf_bytes(file_bytes)
        st.success(f"Extracted {len(text)} characters.")

        # store PDF in Supabase Storage
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        pdf_path = f"pdfs/{class_name}/{subject}/{topic}_{now}.pdf"
        try:
            pdf_url = upload_bytes_to_supabase("cbse-resources", pdf_path, file_bytes, content_type="application/pdf")
        except Exception as e:
            st.error("PDF upload failed. See logs.")
            st.write(traceback.format_exc())
            pdf_url = None

        st.write("PDF uploaded:", pdf_url)

        # create topic metadata in Supabase DB table 'topics' (create table manually or allow failure)
        topic_row = {
            "class": class_name,
            "subject": subject,
            "chapter": chapter,
            "topic": topic,
            "pdf_url": pdf_url,
            "created_at": str(datetime.utcnow())
        }
        try:
            supabase.table("topics").insert(topic_row).execute()
        except Exception:
            # it's okay if table doesn't exist on first run
            pass

        st.info("Generating notes (OpenAI if key is set) ...")
        notes_json = None
        if OPENAI_KEY and openai:
            notes_json = generate_notes_via_openai(class_name, subject, chapter, topic, text)
        if not notes_json:
            st.info("Using fallback sample notes JSON.")
            notes_json = generate_notes_fallback(class_name, subject, chapter, topic)

        # attach metadata
        notes_json["source_pdf"] = pdf_url
        notes_json["uploaded_at"] = now

        # save notes JSON to Supabase and get URL
        notes_bytes = json.dumps(notes_json, ensure_ascii=False, indent=2).encode("utf-8")
        notes_path = f"notes/{class_name}/{subject}/{topic}_{now}.json"
        try:
            notes_url = upload_bytes_to_supabase("cbse-resources", notes_path, notes_bytes, content_type="application/json")
        except Exception as e:
            st.error("Notes upload failed. See logs.")
            st.write(traceback.format_exc())
            notes_url = None
        st.write("Notes JSON stored:", notes_url)

        # generate narration segments
        segments = create_narration_segments(notes_json)
        st.write("Created", len(segments), "segments.")

        # synthesize placeholder audio for each segment and upload
        audio_urls = []
        for seg in segments:
            audio_bytes = synthesize_placeholder_audio(seg)
            seg_path = f"audio/{class_name}/{subject}/{seg['segment_id']}.mp3"
            try:
                audio_url = upload_bytes_to_supabase("cbse-resources", seg_path, audio_bytes, content_type="audio/mpeg")
            except Exception:
                st.write("Audio upload failed for segment:", seg.get("segment_id"))
                audio_url = None
            audio_urls.append({"segment_id": seg["segment_id"], "url": audio_url})
        st.write("Audio files uploaded:", audio_urls)

        # Save mapping file (segments JSON)
        segments_bytes = json.dumps(segments, ensure_ascii=False, indent=2).encode("utf-8")
        segs_path = f"audio/{class_name}/{subject}/{topic}_{now}_segments.json"
        try:
            segs_url = upload_bytes_to_supabase("cbse-resources", segs_path, segments_bytes, content_type="application/json")
        except Exception:
            st.write("Segments JSON upload failed.")
            segs_url = None
        st.write("Segments JSON stored:", segs_url)

        st.success("Resource created. You can share the PDF and notes URLs with students.")

st.markdown("---")
st.header("Preview seeded Perceptron topic (sample)")
col1, col2 = st.columns([1,2])
with col1:
    if st.button("Show sample perceptron note"):
        try:
            with open("notes/n_perceptron.json","r", encoding="utf-8") as f:
                sample = json.load(f)
            st.json(sample)
        except Exception as e:
            st.error("notes/n_perceptron.json missing. Add sample file as provided in repository.")
with col2:
    st.info("If you have deployed with Supabase, uploaded files will be accessible via public URL(s).")

st.markdown("## How to use")
st.markdown("""
1. Upload PDF → Extract text → Generate notes → Create audio segments.  
2. Use `notes_url`, `pdf_url` and `audio_urls` to present topic pages to students (example student site can fetch these).
""")
