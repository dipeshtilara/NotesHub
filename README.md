# CBSE-NotesHub — Streamlit Prototype (Teacher Admin)

This is a minimal Streamlit prototype for teachers to upload PDFs, generate/extract notes, create audio segments, and store everything in Supabase Storage.

## Files
- `app.py` — main Streamlit app
- `requirements.txt` — pip requirements
- `prompts/` — LLM prompt templates
- `notes/n_perceptron.json` — sample notes JSON
- `tts/perceptron_segments.json` — sample segments

## Requirements
- A Supabase project (for Storage & optional DB)
- Streamlit Cloud account (https://streamlit.io/cloud)
- (Optional) OpenAI API key for real notes generation

## Setup (Supabase)
1. Create a free Supabase project: https://app.supabase.com
2. Create a Storage bucket named `cbse-resources` (public).
3. Copy Project URL and anon/service role key.

## Deploy to Streamlit Cloud
1. Push this repo to GitHub.
2. In Streamlit Cloud, create a new app linked to the repo.
3. In Streamlit app settings → Secrets, add:
   - SUPABASE_URL = your supabase url
   - SUPABASE_KEY = your supabase anon or service key
   - OPENAI_API_KEY = (optional) your OpenAI key
   - NOTEBOOKLM_API_KEY = (optional)
   - TTS_API_KEY = (optional)
4. Deploy. Open app. Upload a PDF and follow flows.

## Local dev (optional)
You can run locally with:
```bash
pip install -r requirements.txt
streamlit run app.py
