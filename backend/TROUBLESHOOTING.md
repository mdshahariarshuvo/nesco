# Telegram Bot Troubleshooting Guide

This guide helps you diagnose and fix common issues when running the Telegram bot.

## Quick Diagnostic

**First, always run the diagnostic script:**
```bash
cd backend
python test_connection.py
```

This will identify most configuration issues automatically.

## Common Issues and Solutions

### 1. Bot Not Starting - "TELEGRAM_BOT_TOKEN not set!"

**Error:**
```
ERROR:__main__:TELEGRAM_BOT_TOKEN not set!
```

**Cause:** Environment variable not configured.

**Solution:**
```bash
# 1. Create .env file from template
cd backend
cp .env.example .env

# 2. Edit .env and add your bot token from @BotFather
nano .env  # or use your editor

# 3. Make sure you have this line with your actual token:
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# 4. Verify it's set
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('TELEGRAM_BOT_TOKEN'))"
```

### 2. Bot Not Starting - "ModuleNotFoundError: No module named 'telegram'"

**Error:**
```
ModuleNotFoundError: No module named 'telegram'
```

**Cause:** Dependencies not installed.

**Solution:**
```bash
# Install all required packages
cd backend
pip install -r requirements.txt

# Verify python-telegram-bot is installed
pip show python-telegram-bot
```

### 3. Bot Starts But Doesn't Respond to Commands

**Symptoms:**
- Bot shows as "online" in Telegram
- Sending commands like `/start` gets no response
- No errors in console

**Possible Causes & Solutions:**

**A. Wrong bot token:**
```bash
# Test your token
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe

# Should return bot information
# If error, get new token from @BotFather
```

**B. Backend not running:**
```bash
# In Terminal 1 - Start backend first
cd backend
python app.py

# Should see:
# * Running on http://127.0.0.1:5000

# In Terminal 2 - Then start bot
python bot.py
```

**C. Wrong BACKEND_URL:**
```bash
# Check BACKEND_URL in .env
cat backend/.env | grep BACKEND_URL

# For local development, should be:
BACKEND_URL=http://localhost:5000

# Test backend is accessible
curl http://localhost:5000/health
```

### 4. Backend Connection Error

**Error in bot logs:**
```
ERROR:__main__:Backend call failed: Connection refused
```

**Solution:**
```bash
# 1. Make sure backend is running
ps aux | grep "python app.py"

# 2. If not running, start it
cd backend
python app.py

# 3. Test backend health
curl http://localhost:5000/health

# Should return: {"status": "healthy", "timestamp": "..."}
```

### 5. Database Connection Error

**Error:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solution:**

**For Local PostgreSQL:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql
# or
pg_isready

# Start PostgreSQL if needed
sudo systemctl start postgresql

# Create database
createdb nesco_bot

# Initialize tables
cd backend
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

**For SQLite (simpler for testing):**
```bash
# Edit .env to use SQLite instead
DATABASE_URL=sqlite:///nesco_bot.db

# Initialize tables
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### 6. Bot Commands Don't Work After /start

**Symptoms:**
- `/start` works
- Other commands like `/add`, `/list` don't work

**Solution:**
```bash
# The bot might need to be restarted
# Press Ctrl+C to stop bot.py
# Then restart:
python bot.py

# Also check backend logs for errors
# They should show when bot calls endpoints
```

### 7. Heroku Deployment Issues

**Bot not responding on Heroku:**

```bash
# Check if worker dyno is running
heroku ps --app your-app-name

# Should show:
# worker.1: up

# If not, scale it up
heroku ps:scale worker=1

# Check logs
heroku logs --tail --app your-app-name

# Restart if needed
heroku restart --app your-app-name
```

### 8. "Connection timeout" when checking meters

**Error:**
```
Backend call failed: Connection timeout
```

**Cause:** NESCO website might be slow or unreachable.

**Solution:**
- This is normal occasionally - NESCO website can be slow
- Wait a moment and try again
- Check if you can access https://prepaid.nescopower.com in browser

## Step-by-Step Debug Process

If bot is not working, follow these steps:

### Step 1: Check Environment Variables
```bash
cd backend
python -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('TELEGRAM_BOT_TOKEN:', 'SET' if os.getenv('TELEGRAM_BOT_TOKEN') else 'NOT SET')
print('BACKEND_URL:', os.getenv('BACKEND_URL'))
print('DATABASE_URL:', 'SET' if os.getenv('DATABASE_URL') else 'NOT SET')
"
```

### Step 2: Verify Dependencies
```bash
pip install -r requirements.txt
pip show python-telegram-bot flask flask-sqlalchemy
```

### Step 3: Test Backend
```bash
# Start backend
python app.py &

# Test endpoints
curl http://localhost:5000/health
curl http://localhost:5000/

# Stop background process
pkill -f "python app.py"
```

### Step 4: Test Bot Token
```bash
# Replace YOUR_TOKEN with your actual token
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
```

### Step 5: Run Diagnostic Script
```bash
python test_connection.py
```

### Step 6: Check Logs
```bash
# When running bot, watch for these messages:
# ✓ "Bot started successfully!"
# ✗ Any ERROR messages
```

## Getting More Help

### Enable Debug Logging

Edit `bot.py` and change logging level:
```python
# Change this line:
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
```

### Test Individual Commands

Create a test script:
```python
# test_bot_backend.py
import requests

BACKEND_URL = "http://localhost:5000"

# Test start command
response = requests.post(f"{BACKEND_URL}/webhook/telegram", json={
    'command': 'start',
    'telegram_user_id': 123456789
})
print(response.json())
```

### Check Bot with BotFather

1. Open Telegram
2. Search for @BotFather
3. Send `/mybots`
4. Select your bot
5. Check bot settings

## Still Having Issues?

If none of the above solutions work:

1. **Run the diagnostic script and share the output:**
   ```bash
   python test_connection.py > diagnostic_output.txt
   ```

2. **Share bot startup logs:**
   ```bash
   python bot.py 2>&1 | tee bot_logs.txt
   ```

3. **Share backend logs:**
   ```bash
   python app.py 2>&1 | tee backend_logs.txt
   ```

4. **Include your setup:**
   - Operating system
   - Python version: `python --version`
   - Are you running locally or on Heroku?
   - Have you created the bot with @BotFather?

## Quick Fixes Summary

| Issue | Quick Fix |
|-------|-----------|
| Token not set | `cp .env.example .env` and edit |
| Module not found | `pip install -r requirements.txt` |
| Backend not accessible | Start with `python app.py` first |
| Database error | Use SQLite: `DATABASE_URL=sqlite:///nesco_bot.db` |
| Bot online but not responding | Check BACKEND_URL in .env |
| Commands not working | Restart both backend and bot |
| Heroku bot not responding | `heroku ps:scale worker=1` |

---

**Remember:** Always start the backend (`python app.py`) before starting the bot (`python bot.py`)!
