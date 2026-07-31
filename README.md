---
title: YC Daily Top10
emoji: "🚀"
colorFrom: blue
colorTo: purple
sdk: streamlit
sdk_version: "1.35.0"
app_file: app.py
pinned: false
---
# 🔥 YC Hacker News Daily Scraper

A Python project that scrapes [Hacker News](https://news.ycombinator.com) (by Y Combinator), ranks articles by upvotes, displays them in a Streamlit dashboard, and emails you a daily Top 10 newsletter.

---

## 📁 Project Structure

```
your_project/
├── scraper.py                ← Core scraping logic
├── app.py                    ← Streamlit dashboard (2 pages)
├── mailer.py                 ← Daily newsletter emailer
├── hn_daily_archive.json     ← Auto-created when you save articles
└── README.md                 ← You are here
```

---

## ⚙️ Requirements

- Python 3.8 or above
- A Gmail account with **2-Step Verification** enabled
- A Gmail **App Password** (16 characters)

---

## 🚀 Setup & Installation

### Step 1 — Clone or download the project

Place all three files (`scraper.py`, `app.py`, `mailer.py`) in the same folder on your machine.

### Step 2 — Install dependencies

Open your terminal/command prompt inside the project folder and run:

```bash
pip install requests beautifulsoup4 streamlit
```

### Step 3 — Get your Gmail App Password

Gmail requires an App Password to let scripts send email on your behalf.

1. Go to 👉 [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   - *(You must have 2-Step Verification turned on — enable it at [myaccount.google.com/security](https://myaccount.google.com/security) first)*
2. Under "Select app" → choose **Mail**
3. Under "Select device" → choose **Windows Computer**
4. Click **Generate**
5. Copy the 16-character password shown (e.g. `abcd efgh ijkl mnop`)

### Step 4 — Configure mailer.py

Open `mailer.py` and fill in the CONFIG block at the top:

```python
SENDER_EMAIL   = "your_email@gmail.com"    # Your Gmail address
RECEIVER_EMAIL = "your_email@gmail.com"    # Where to receive the newsletter
APP_PASSWORD   = "abcdefghijklmnop"        # 16-char App Password WITHOUT spaces
```

> ⚠️ **Important:** Remove all spaces from the App Password before pasting it in.

---

## ▶️ Running the Project

### Run the Streamlit Dashboard

```bash
streamlit run app.py
```

This opens a browser at `http://localhost:8501` with two pages:

| Page | What it does |
|------|-------------|
| 🔥 Live Rankings | Scrapes HN live and shows articles ranked by upvotes |
| 📅 Daily Archive | Shows all previously saved Top 10 lists by date |

**Dashboard features:**
- **⟳ Refresh Now** — re-scrapes Hacker News for latest articles
- **💾 Save Today's Top 10** — saves current top 10 to `hn_daily_archive.json`
- **⬇ Download Full Archive** — exports archive as JSON file

### Send the Newsletter Manually

```bash
python mailer.py
```

Expected output:
```
🔍 Scraping Hacker News...
✅ Saved 2026-04-26 to archive.
📧 Building email...
📤 Connecting to Gmail SMTP...
✅ Newsletter sent to your_email@gmail.com!
```

> 📬 Check your **spam folder** the first time — click "Not spam" so future emails land in inbox.

---

## ⏰ Automating Daily Email (Windows Task Scheduler)

Set up Windows Task Scheduler to run `mailer.py` automatically every day.

1. Press `Win + S` → search **Task Scheduler** → Open it
2. Click **"Create Basic Task"** in the right panel
3. Fill in the details:

| Field | Value |
|-------|-------|
| **Name** | HN Daily Newsletter |
| **Trigger** | Daily |
| **Time** | 8:00 AM (or your preferred time) |
| **Action** | Start a Program |
| **Program/script** | `C:\Users\YourName\AppData\Local\Programs\Python\Python312\python.exe` |
| **Add arguments** | `mailer.py` |
| **Start in** | Full path to your project folder e.g. `D:\data_projects\hn-scraper` |

4. Click **Finish** ✅

From that point on, Python runs `mailer.py` automatically every day at your chosen time — no manual steps needed.

---

## 🛠️ How It Works

```
scraper.py
│
├── Fetches https://news.ycombinator.com/news
├── Parses HTML with BeautifulSoup
├── Finds all <span class="titleline"> for titles + links
├── Finds all <span class="score"> for upvote counts
├── Zips them together (excludes job posts with no score)
└── Returns list sorted by upvotes (highest first)

app.py  (Streamlit)
│
├── Page 1: Calls scraper.py → displays ranked cards in browser
└── Page 2: Reads hn_daily_archive.json → displays saved days

mailer.py
│
├── Calls scraper.py → gets ranked articles
├── Saves top 10 to hn_daily_archive.json
├── Builds a styled HTML email
└── Sends via Gmail SMTP on port 465
```

---

## ❓ Troubleshooting

| Problem | Fix |
|---------|-----|
| `SMTPAuthenticationError` | Make sure App Password has no spaces and 2FA is enabled |
| `ModuleNotFoundError` | Run `pip install requests beautifulsoup4 streamlit` |
| Empty article list | HN may have changed their HTML — check class names in `scraper.py` |
| Email goes to spam | Open the email → click "Not spam" → future emails go to inbox |
| App Password page not found | Your account may be a Workspace/school account — admin controls access |

---

## 📦 Dependencies

| Library | Purpose | Install |
|---------|---------|---------|
| `requests` | Fetch live webpage | `pip install requests` |
| `beautifulsoup4` | Parse HTML | `pip install beautifulsoup4` |
| `streamlit` | Web dashboard UI | `pip install streamlit` |
| `smtplib` | Send email via Gmail | Built into Python (no install needed) |
| `json` | Read/write archive file | Built into Python (no install needed) |

---

*Data source: [news.ycombinator.com](https://news.ycombinator.com) by Y Combinator*


IN TERMINAL:
1) python mailer.py --> sends mail from sender to reciever
2) streamlit run app.py --> shows display of website by webscraping the articles on website on daily basis

