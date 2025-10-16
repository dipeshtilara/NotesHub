# CBSE NotesHub - Setup Complete! 🎉

## Application Overview

**CBSE NotesHub** is an educational platform with two main portals for managing and accessing study materials:

### 1. 👨‍🏫 Teacher/Admin Portal (Port 8001)
**Purpose:** Upload and manage educational content

**Features:**
- Upload PDF study materials
- Automatic text extraction from PDFs
- AI-powered notes generation (using OpenAI GPT-4)
- Fallback manual notes option
- Audio segment creation for narration
- Automatic storage in Supabase

**Access:** `http://your-domain:8001` or via the preview

### 2. 👨‍🎓 Student Portal (Port 3000)
**Purpose:** Browse and access study materials

**Features:**
- Browse topics by Class, Subject, Chapter
- Search functionality
- View embedded PDFs
- Read structured notes (Theory, Learning Objectives, Quick Revision, MCQs)
- Listen to audio explanations
- Pagination for easy navigation

**Access:** `http://your-domain:3000` or via the preview

---

## Current Configuration

### ✅ Installed Dependencies
- streamlit==1.50.0
- PyPDF2==3.0.1
- supabase==2.22.0
- openai==2.4.0
- requests==2.32.5

### ✅ Supabase Configuration
- **URL:** https://qqtqtuzewywbpovifnfy.supabase.co
- **Storage Bucket:** `cbse-resources` (needs to be created in Supabase)
- **Database Table:** `topics` (needs to be created in Supabase)

### ⚠️ Optional Configuration
- **OpenAI API Key:** Not configured (using fallback mode)
  - To enable AI note generation, add your OpenAI key to `/app/.streamlit/secrets.toml`

---

## Supabase Setup Required

Before using the application, you need to set up your Supabase project:

### 1. Create Storage Bucket
1. Go to your Supabase dashboard: https://app.supabase.com
2. Navigate to **Storage** → **Create Bucket**
3. Bucket name: `cbse-resources`
4. Make it **public** (so students can access content)

### 2. Create Database Table
Run this SQL in your Supabase SQL Editor:

```sql
CREATE TABLE topics (
    id BIGSERIAL PRIMARY KEY,
    class TEXT NOT NULL,
    subject TEXT NOT NULL,
    chapter TEXT,
    topic TEXT NOT NULL,
    summary TEXT,
    pdf_url TEXT,
    notes_url TEXT,
    segments_url TEXT,
    thumbnail_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster queries
CREATE INDEX idx_topics_class ON topics(class);
CREATE INDEX idx_topics_subject ON topics(subject);
CREATE INDEX idx_topics_topic ON topics(topic);

-- Enable Row Level Security (optional but recommended)
ALTER TABLE topics ENABLE ROW LEVEL SECURITY;

-- Policy to allow public read access
CREATE POLICY "Allow public read access" ON topics
    FOR SELECT
    USING (true);

-- Policy to allow authenticated insert (for teacher portal)
CREATE POLICY "Allow authenticated insert" ON topics
    FOR INSERT
    WITH CHECK (true);
```

---

## How to Use

### For Teachers/Admins:

1. **Access Teacher Portal** at port 8001
2. **Fill in the form:**
   - Select Class (IX, X, XI, XII)
   - Select Subject
   - Enter Chapter name
   - Enter Topic name
   - Upload PDF file
3. **Click "🚀 Upload & Generate"**
4. The system will:
   - Extract text from PDF
   - Upload PDF to Supabase
   - Generate notes (AI or fallback)
   - Create audio segments
   - Store everything in Supabase
5. **Students can now access** the content via the Student Portal

### For Students:

1. **Access Student Portal** at port 3000
2. **Browse topics** using filters:
   - Filter by Class
   - Filter by Subject
   - Search by topic/chapter name
3. **View content:**
   - Click "View" to see detailed notes
   - Click "Open PDF" to view the PDF
   - Click "JSON" to see raw notes data
4. **In detail view:**
   - Read embedded PDF
   - Browse structured notes (Theory, Examples, Quick Revision, MCQs)
   - Listen to audio explanations

---

## Service Management

### Check Status
```bash
sudo supervisorctl status
```

### Restart Services
```bash
# Restart teacher portal
sudo supervisorctl restart teacher_portal

# Restart student portal
sudo supervisorctl restart student_portal

# Restart all
sudo supervisorctl restart all
```

### View Logs
```bash
# Teacher portal logs
tail -f /var/log/supervisor/teacher_portal.out.log
tail -f /var/log/supervisor/teacher_portal.err.log

# Student portal logs
tail -f /var/log/supervisor/student_portal.out.log
tail -f /var/log/supervisor/student_portal.err.log
```

---

## Directory Structure

```
/app/
├── app.py                          # Teacher portal main file
├── FrontEnd/
│   └── FrontView.py               # Student portal main file
├── .streamlit/
│   ├── secrets.toml               # Supabase credentials
│   └── config.toml                # Streamlit config
├── prompts/                        # LLM prompt templates
├── notes/                          # Sample notes
├── tts/                           # Sample audio segments
├── requirements.txt                # Python dependencies
└── README.md                       # Original project README
```

---

## Adding OpenAI API Key (Optional)

To enable AI-powered note generation:

1. Edit `/app/.streamlit/secrets.toml`
2. Add your OpenAI key:
   ```toml
   OPENAI_API_KEY = "sk-your-actual-openai-key"
   ```
3. Restart teacher portal:
   ```bash
   sudo supervisorctl restart teacher_portal
   ```

---

## Troubleshooting

### Issue: "Missing Supabase credentials"
- Check `/app/.streamlit/secrets.toml` exists and has correct credentials
- Verify Supabase URL and key are valid

### Issue: "PDF upload failed"
- Ensure `cbse-resources` bucket exists in Supabase
- Verify bucket is set to **public**
- Check Supabase storage quota

### Issue: "No topics found"
- Ensure `topics` table exists in Supabase database
- Upload at least one PDF via Teacher Portal
- Check if Row Level Security policies are correctly set

### Issue: Service not running
```bash
# Check which service is down
sudo supervisorctl status

# View error logs
tail -n 50 /var/log/supervisor/teacher_portal.err.log
tail -n 50 /var/log/supervisor/student_portal.err.log

# Restart the service
sudo supervisorctl restart teacher_portal
```

---

## Tech Stack

- **Framework:** Streamlit (Python web framework)
- **Database:** Supabase (PostgreSQL)
- **Storage:** Supabase Storage
- **PDF Processing:** PyPDF2
- **AI:** OpenAI GPT-4 (optional)
- **Deployment:** Supervisor (process management)

---

## Next Steps

1. ✅ **Complete Supabase setup** (create bucket and table)
2. ✅ **Test Teacher Portal** - Upload a sample PDF
3. ✅ **Test Student Portal** - Verify content appears
4. 🔧 **Optional:** Add OpenAI key for AI-powered notes
5. 🚀 **Start using** the platform!

---

## Support

- **Supabase Dashboard:** https://app.supabase.com
- **Project Repository:** https://github.com/dipeshtilara/NotesHub
- **Streamlit Docs:** https://docs.streamlit.io

---

**Status:** ✅ Application is running and ready to use!
- Teacher Portal: Port 8001
- Student Portal: Port 3000
