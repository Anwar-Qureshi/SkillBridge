# 📦 Installation & Setup Guide

Complete step-by-step instructions to get SkillsBridge running on your machine.

## Prerequisites

- **Python**: 3.10 or higher ([Download](https://www.python.org/downloads/))
- **Git**: For cloning the repository ([Download](https://git-scm.com/))
- **Google Gemini API Key**: Free account ([Get Here](https://makersuite.google.com/app/apikey))

## Step-by-Step Installation

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/yourusername/skillbridge.git
cd skillbridge
```

### 2️⃣ Create Python Virtual Environment

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt after activation.

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- streamlit (UI framework)
- google-generativeai (Gemini API client)
- python-dotenv (environment variable management)
- Other utilities

**Expected time**: 2-5 minutes depending on internet speed

### 4️⃣ Configure Environment Variables

**Copy the example file:**
```bash
cp .env.example .env
```

**Edit `.env` file:**

Open `.env` in your text editor and replace:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

With your actual API key from [Google AI Studio](https://makersuite.google.com/app/apikey).

**⚠️ Important Security Notes:**
- Never commit `.env` to version control
- Never share your API key publicly
- Keep `.env` in `.gitignore` (already configured)

### 5️⃣ Verify Installation

Test if everything is set up correctly:

```bash
# Verify Python version
python --version        # Should be 3.10+

# Verify dependencies installed
pip list | grep streamlit

# Test Streamlit
streamlit hello
```

If you see the Streamlit demo app in your browser, you're good to go! ✅

### 6️⃣ Run SkillsBridge

```bash
streamlit run app.py
```

The application will automatically open at `http://localhost:8501`

**Expected output:**
```
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

---

## 🔧 Troubleshooting

### "Python not found" Error

**Problem:** Command `python` not recognized

**Solutions:**
- Install Python from [python.org](https://www.python.org/downloads/)
- Make sure to check "Add Python to PATH" during installation
- Try `python3` instead of `python`
- Restart your terminal after installing Python

### "GEMINI_API_KEY not found" Error

**Problem:** App crashes with API key error

**Solutions:**
1. Verify `.env` file exists in project root
2. Check that `GEMINI_API_KEY=` is in the file
3. Ensure your API key is valid ([Generate new one here](https://makersuite.google.com/app/apikey))
4. Restart the app after updating `.env`

### "Module not found: streamlit" Error

**Problem:** Dependencies not installed

**Solutions:**
1. Activate virtual environment: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
2. Install dependencies: `pip install -r requirements.txt`
3. Verify installation: `pip list`

### "Port 8501 already in use" Error

**Problem:** Another app is using Streamlit's default port

**Solutions:**
1. Stop the other Streamlit process
2. Or run on a different port: `streamlit run app.py --server.port 8502`

### "Connection refused" or "API Error"

**Problem:** Gemini API not responding

**Solutions:**
1. Check internet connection
2. Verify API key is valid and has quota remaining
3. Check Google's status page for API outages
4. Try again in a few minutes

### "Session keeps disconnecting"

**Problem:** App loses connection frequently

**Solutions:**
1. Check network stability
2. Increase session timeout: Add to `~/.streamlit/config.toml`:
   ```toml
   [client]
   showErrorDetails = true
   
   [logger]
   level = "debug"
   ```
2. Try running on localhost instead of network IP

---

## 📋 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.10 | 3.11 or 3.12 |
| RAM | 2GB | 4GB+ |
| Storage | 500MB | 1GB |
| Internet | Required | Broadband |

---

## 🚀 Quick Start Commands

```bash
# One-time setup
git clone https://github.com/yourusername/skillbridge.git
cd skillbridge
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your API key

# Run app
streamlit run app.py
```

---

## 📚 Post-Installation

After successful installation:

1. **Read the README**: Understand project features
2. **Check FEATURES.md**: See all capabilities
3. **Start a session**: Enter your name and click "Start Session"
4. **Take a test question**: Try "Get Next Question"
5. **Review feedback**: Check your scores and coaching

---

## 🆘 Still Having Issues?

1. **Check existing issues**: GitHub Issues
2. **Review common problems**: Section above
3. **Verify all prerequisites**: Python 3.10+, API key, dependencies
4. **Clear cache**: Remove `__pycache__` and `.streamlit/cache`
5. **Reinstall dependencies**: 
   ```bash
   pip uninstall -r requirements.txt
   pip install -r requirements.txt
   ```

---

## ✅ You're All Set!

Once you see the SkillsBridge app at `http://localhost:8501`, you're ready to start practicing! 🎯

**Next Steps:**
- 📖 Read [FEATURES.md](./FEATURES.md) to explore all capabilities
- 💡 Check [README.md](./README.md) for tips and tricks
- 🎓 Start with easy questions first
- 📊 Track your progress in the Session Report

Happy practicing! 🚀
