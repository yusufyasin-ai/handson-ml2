# 🏌️ GreenReader — Beginner's Setup Guide

This guide assumes you've **never run a web app before**. Follow it top to bottom.
Every command is copy-paste. If something breaks, jump to **Troubleshooting** at the bottom.

---

## 🧠 What you're about to do (the big picture)

This app has **two parts** that run at the same time:

1. **Backend** (the "brain") — a Python program that looks at the photo and figures out the slopes.
2. **Frontend** (the "face") — the website you click around in, in your browser.

You'll open **two terminal windows**: one runs the brain, one runs the face.
Then you visit a web page and upload a golf-green photo.

> A "terminal" is the black text window where you type commands.
> - **Mac:** press `Cmd + Space`, type **Terminal**, press Enter.
> - **Windows:** press the Start button, type **PowerShell**, press Enter.

---

## ✅ Step 0 — Install the two tools you need

You need **Python** (for the brain) and **Node.js** (for the face).

### Check if you already have them
In your terminal, type these two commands (press Enter after each):

```bash
python3 --version
node --version
```

- If each prints a version number (like `Python 3.11.5` and `v20.x.x`), you're set — **skip to Step 1**.
- If you get "command not found", install the missing one below.

### Install Python (if needed)
- **Mac/Windows:** Go to <https://www.python.org/downloads/> → click the big yellow **Download** button → run the installer.
  - ⚠️ **Windows only:** on the first installer screen, **tick the box "Add Python to PATH"** before clicking Install. This is important.

### Install Node.js (if needed)
- Go to <https://nodejs.org/> → download the **LTS** version → run the installer → click Next through all screens.

After installing, **close and reopen your terminal**, then re-run the `--version` checks above.

---

## 📥 Step 1 — Download the app code

The code lives on GitHub on a branch called `claude/golf-putting-gradient-app-mOJKE`.

In your terminal, run these one at a time:

```bash
git clone https://github.com/yusufyasin-ai/handson-ml2.git
cd handson-ml2
git checkout claude/golf-putting-gradient-app-mOJKE
cd golf-putting-app
```

> If `git` is "not found", install it from <https://git-scm.com/downloads> first, then retry.

You are now **inside the app folder**. Keep this terminal open.

---

## 🧠 Step 2 — Start the Backend (the brain)

### 2a. Install the brain's building blocks
```bash
cd backend
pip3 install -r requirements.txt
```
This downloads the image-processing libraries. It may take a minute or two. Wait for it to finish.

### 2b. (Optional but recommended) Add your AI key
The app works **without** this — you'll still get the computer-vision slope arrows.
Adding a key unlocks the smarter **AI analysis + putting advice**.

1. Get a key at <https://console.anthropic.com/> (sign up → API Keys → Create Key). It starts with `sk-ant-...`.
2. Tell the terminal about it:

   **Mac:**
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-paste-your-key-here"
   ```
   **Windows (PowerShell):**
   ```powershell
   $env:ANTHROPIC_API_KEY="sk-ant-paste-your-key-here"
   ```

### 2c. Turn the brain on
```bash
uvicorn main:app --port 8000
```

✅ **Success looks like:** `Uvicorn running on http://127.0.0.1:8000`

**Leave this window running.** Closing it turns off the brain. Don't type anything else here.

---

## 🖥️ Step 3 — Start the Frontend (the face)

Open a **SECOND terminal window** (don't close the first one!).

Navigate back into the app and into the frontend folder:

```bash
cd handson-ml2/golf-putting-app/frontend
npm install
```
`npm install` downloads the website's parts. First time takes a couple minutes. Wait for it to finish.

Then start it:
```bash
npm run dev
```

✅ **Success looks like:** `Local: http://localhost:3000`

**Leave this window running too.**

---

## 🎉 Step 4 — Use the app!

1. Open your web browser (Chrome, Safari, Edge…).
2. Go to: **http://localhost:3000**
3. You'll see the GreenReader page. Now either:
   - **Drag a photo** of a putting green onto the box, **or**
   - Click **Upload photo** to pick one, **or**
   - Click **Use camera** to take one live (your browser will ask permission — click Allow).
4. Wait a few seconds. You'll see:
   - **Colored arrows** showing slope direction (blue = flat, red = steep)
   - An **orange heatmap** of where the slopes are strongest
   - A **side panel** with the analysis and putting advice
5. Use the **Heatmap / CV Gradients / AI Arrows** buttons to turn each layer on and off.

---

## 🛑 How to stop everything

In each of the two terminal windows, press **`Ctrl + C`** (hold Control, tap C). That shuts each part down cleanly.

To run it again later, just repeat **Step 2c** and **Step 3** (`npm run dev`) — you don't need to reinstall.

---

## 🆘 Troubleshooting

| What you see | What it means | Fix |
|---|---|---|
| `command not found: python3` | Python isn't installed or not on PATH | Reinstall Python; on Windows tick "Add to PATH" |
| `command not found: pip3` | Same as above | Try `python3 -m pip install -r requirements.txt` |
| `pip3 ... externally-managed-environment` | Your OS protects system Python | Run `pip3 install --user -r requirements.txt` |
| Browser says "can't connect" at localhost:3000 | Frontend isn't running | Make sure Step 3's `npm run dev` window is still open |
| Analysis says "ANTHROPIC_API_KEY not set" | No AI key added | That's fine — CV arrows still work. Add a key (Step 2b) for AI advice |
| "Analysis failed" in the app | Backend (brain) isn't running | Check Step 2c window is still open and shows no errors |
| `port 8000 already in use` | Something else is using that port | Stop it, or run `uvicorn main:app --port 8001` (then it won't match the frontend — easier to just free port 8000) |
| Photo gives few/no arrows | Photo wasn't mostly green grass | Use a photo where the putting surface fills most of the frame |

---

## 🐳 Shortcut for the brave: one command with Docker

If you'd rather not install Python and Node separately, and you have **Docker Desktop** installed
(<https://www.docker.com/products/docker-desktop/>):

```bash
cd handson-ml2/golf-putting-app
cp .env.example .env        # then open .env in a text editor and paste your API key
docker compose up --build
```

Then visit **http://localhost:3000**. Press `Ctrl + C` to stop.

---

That's it. The two things to remember: **two terminals, both stay open**, then **http://localhost:3000**. 🏌️‍♂️
