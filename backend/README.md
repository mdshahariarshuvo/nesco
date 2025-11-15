# NESCO Telegram Bot - Backend

Complete Flask backend for NESCO prepaid meter monitoring via Telegram.

## 🚀 Quick Start

**New to this project? Start here:**

👉 **[Complete Setup Guide](SETUP.md)** - Step-by-step instructions to connect the Telegram bot to the backend

### TL;DR - Fast Setup

1. **Create a Telegram bot** with [@BotFather](https://t.me/BotFather)
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your bot token and database URL
   ```
4. **Initialize database:**
   ```bash
   python -c "from app import app, db; app.app_context().push(); db.create_all()"
   ```
5. **Run backend:**
   ```bash
   python app.py
   ```
6. **Run bot (in another terminal):**
   ```bash
   python bot.py
   ```

That's it! Open Telegram and test your bot with `/start`

## 📚 Documentation

- **[SETUP.md](SETUP.md)** - Complete setup instructions
- **[README.md](#)** (this file) - Quick reference and API documentation

## 🚀 Quick Deploy to Heroku

### Prerequisites
1. Heroku account
2. Heroku CLI installed
3. PostgreSQL add-on (automatically provisioned)

### Deployment Steps

```bash
# 1. Clone/navigate to project
cd backend

# 2. Login to Heroku
heroku login

# 3. Create Heroku app
heroku create your-nesco-bot

# 4. Add PostgreSQL
heroku addons:create heroku-postgresql:essential-0

# 5. Deploy
git init
git add .
git commit -m "Initial commit"
heroku git:remote -a your-nesco-bot
git push heroku main

# 6. Initialize database
heroku run python -c "from app import app, db; app.app_context().push(); db.create_all()"

# 7. Check logs
heroku logs --tail
```

### Environment Variables

Set these in Heroku dashboard or CLI:

```bash
# Database URL (auto-set by Heroku PostgreSQL)
DATABASE_URL=postgresql://...

# Optional: For bot script
TELEGRAM_BOT_TOKEN=your_token_here
```

## 🤖 Running the Telegram Bot

### Option 1: Run on Same Heroku Dyno (Recommended for testing)

Add to `Procfile`:
```
web: gunicorn app:app
worker: python bot.py
```

Then scale worker:
```bash
heroku ps:scale worker=1
```

### Option 2: Run Locally

```bash
pip install -r requirements.txt
export BACKEND_URL=https://your-app.herokuapp.com
export TELEGRAM_BOT_TOKEN=your_token
python bot.py
```

### Option 3: Separate Heroku App for Bot

```bash
heroku create your-nesco-bot-worker
# Add bot.py and requirements.txt
# Set BACKEND_URL to your API dyno
```

## 📡 API Endpoints

### Health Check
```bash
GET /health
```

### Add Meter
```bash
POST /api/add-meter
{
  "telegram_user_id": 123456789,
  "meter_number": "31041051783",
  "meter_name": "Home"
}
```

### Check Balances
```bash
POST /api/check-balances
{
  "telegram_user_id": 123456789
}
```

### List Meters
```bash
POST /api/list-meters
{
  "telegram_user_id": 123456789
}
```

### Remove Meter
```bash
POST /api/remove-meter
{
  "telegram_user_id": 123456789,
  "meter_id": 1
}
```

### Set Minimum Balance
```bash
POST /api/set-min-balance
{
  "telegram_user_id": 123456789,
  "meter_id": 1,
  "min_balance": 50.0
}
```

### Toggle Daily Reminder
```bash
POST /api/toggle-reminder
{
  "telegram_user_id": 123456789
}
```

### Daily Reminder (Cron)
```bash
GET /api/daily-reminder
```

### Direct NESCO Scraping (Testing)
```bash
POST /api/scrape-nesco
{
  "meter_number": "31041051783"
}
```

## 🕐 Setting Up Daily Reminders (11 AM)

### Option 1: Heroku Scheduler (Free Add-on)

```bash
heroku addons:create scheduler:standard
heroku addons:open scheduler
```

Add job:
- Command: `curl https://your-app.herokuapp.com/api/daily-reminder`
- Frequency: Daily at 11:00 AM (your timezone)

### Option 2: External Cron (cron-job.org)

1. Go to cron-job.org
2. Create free account
3. Add cron job:
   - URL: `https://your-app.herokuapp.com/api/daily-reminder`
   - Schedule: `0 11 * * *`
   - Timezone: Your timezone

## 🧪 Testing

### Test API locally
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment
export DATABASE_URL=postgresql://localhost/nesco_bot
export FLASK_APP=app.py

# Run migrations
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Run server
python app.py
```

### Test scraping
```bash
curl -X POST https://your-app.herokuapp.com/api/scrape-nesco \
  -H "Content-Type: application/json" \
  -d '{"meter_number": "31041051783"}'
```

### Test bot locally
```bash
export BACKEND_URL=http://localhost:5000
export TELEGRAM_BOT_TOKEN=your_token
python bot.py
```

## 📊 Database Schema

### users
- id (PK)
- telegram_user_id (unique)
- username
- daily_reminder_enabled
- reminder_time
- created_at

### meters
- id (PK)
- user_id (FK)
- meter_number
- meter_name
- min_balance
- last_balance
- last_checked
- created_at

### balance_history
- id (PK)
- meter_id (FK)
- balance
- recorded_at

## 🐛 Troubleshooting

### Database connection error
```bash
# Check DATABASE_URL
heroku config:get DATABASE_URL

# Reset database
heroku pg:reset DATABASE_URL
heroku run python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### Bot not responding
```bash
# Check logs
heroku logs --tail --app your-bot-app

# Restart
heroku restart
```

### Scraping fails
- Check NESCO website is accessible
- Verify meter number format
- Check response in logs

## 📝 Telegram Bot Commands

- `/start` - Welcome message
- `/add` - Add new meter (conversational)
- `/list` - List all your meters
- `/check` - Check balances + yesterday usage
- `/remove` - Remove a meter
- `/minbalance` - Set minimum balance alert
- `/reminder` - Toggle daily reminder (11 AM)
- `/help` - Show help

## 💰 Cost Estimate

- **Heroku Eco Dyno**: $5/month (or free 1000 hours/month)
- **PostgreSQL**: Included with Essential-0
- **Scheduler**: Free add-on
- **Total**: $0-5/month

## 🎓 GitHub Student Pack

With student pack, you get:
- **$13/month Heroku credits** = Free hosting
- **DigitalOcean** = Alternative hosting
- Deploy to either platform at no cost!

## 📚 Resources

- [Heroku Python Docs](https://devcenter.heroku.com/articles/getting-started-with-python)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [NESCO Prepaid Portal](https://prepaid.nescopower.com)

## 🔒 Security Notes

- Never commit `.env` file
- Use Heroku config vars for secrets
- DATABASE_URL is auto-managed by Heroku
- Bot token should be kept private

## ✅ Deployment Checklist

- [ ] Create Heroku app
- [ ] Add PostgreSQL addon
- [ ] Deploy code
- [ ] Initialize database
- [ ] Set environment variables
- [ ] Create Telegram bot with @BotFather
- [ ] Configure bot token
- [ ] Test all commands
- [ ] Set up daily reminder (Scheduler or cron-job.org)
- [ ] Monitor logs

---

**Ready to deploy!** Follow the steps above and your bot will be live in 15 minutes.
