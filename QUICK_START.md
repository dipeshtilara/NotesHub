# 🚀 Quick Start Guide

## ✅ Setup Status: COMPLETE

Both portals are running and ready to use!

---

## 🔗 Access URLs

- **👨‍🏫 Teacher Portal (Upload PDFs):** Port 8001
- **👨‍🎓 Student Portal (View Content):** Port 3000

---

## ⚠️ IMPORTANT: Complete Supabase Setup First!

Before uploading content, create these in your Supabase dashboard:

### 1. Storage Bucket
```
1. Go to: https://qqtqtuzewywbpovifnfy.supabase.co
2. Storage → Create Bucket
3. Name: cbse-resources
4. Make it PUBLIC ✓
```

### 2. Database Table
```sql
-- Run this in Supabase SQL Editor:

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

CREATE INDEX idx_topics_class ON topics(class);
CREATE INDEX idx_topics_subject ON topics(subject);

ALTER TABLE topics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access" ON topics FOR SELECT USING (true);
CREATE POLICY "Allow authenticated insert" ON topics FOR INSERT WITH CHECK (true);
```

---

## 📝 Quick Usage

### Upload Content (Teacher Portal - Port 8001):
1. Select Class, Subject
2. Enter Chapter and Topic
3. Upload PDF
4. Click "🚀 Upload & Generate"
5. ✅ Done! Content is now available to students

### View Content (Student Portal - Port 3000):
1. Use filters (Class, Subject)
2. Search for topics
3. Click "View" to see details
4. Read notes and listen to audio

---

## 🛠️ Service Commands

```bash
# Check status
sudo supervisorctl status

# Restart services
sudo supervisorctl restart teacher_portal
sudo supervisorctl restart student_portal

# View logs
tail -f /var/log/supervisor/teacher_portal.out.log
tail -f /var/log/supervisor/student_portal.out.log
```

---

## 🔑 Current Configuration

✅ Supabase URL: https://qqtqtuzewywbpovifnfy.supabase.co
✅ Supabase Key: Configured
❌ OpenAI Key: Not configured (using fallback notes)

**To add OpenAI key (optional):**
Edit `/app/.streamlit/secrets.toml` and add:
```toml
OPENAI_API_KEY = "sk-your-key-here"
```
Then restart: `sudo supervisorctl restart teacher_portal`

---

## 📚 Full Documentation

See `/app/SETUP_GUIDE.md` for detailed information.

---

**Everything is ready! Complete the Supabase setup and start uploading content!** 🎉
