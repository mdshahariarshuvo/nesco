from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import logging

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://localhost/nesco_bot')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    telegram_user_id = db.Column(db.BigInteger, unique=True, nullable=False)
    username = db.Column(db.String(100))
    daily_reminder_enabled = db.Column(db.Boolean, default=True)
    reminder_time = db.Column(db.String(5), default='11:00')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    meters = db.relationship('Meter', backref='user', lazy=True, cascade='all, delete-orphan')

class Meter(db.Model):
    __tablename__ = 'meters'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    meter_number = db.Column(db.String(20), nullable=False)
    meter_name = db.Column(db.String(100), nullable=False)
    min_balance = db.Column(db.Float, default=50.0)
    last_balance = db.Column(db.Float)
    last_checked = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    history = db.relationship('BalanceHistory', backref='meter', lazy=True, cascade='all, delete-orphan')

class BalanceHistory(db.Model):
    __tablename__ = 'balance_history'
    id = db.Column(db.Integer, primary_key=True)
    meter_id = db.Column(db.Integer, db.ForeignKey('meters.id'), nullable=False)
    balance = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

# NESCO Scraping Function
def scrape_nesco_balance(meter_number):
    """Scrape balance from NESCO website"""
    try:
        url = "https://prepaid.nescopower.com/pp_panel_gui/search_mobile.php"
        payload = {
            'search': meter_number,
            'from': 'mob'
        }
        
        response = requests.post(url, data=payload, timeout=30)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find balance in the response
            balance_element = soup.find('td', string=lambda text: text and 'Balance' in text)
            if balance_element:
                balance_row = balance_element.find_parent('tr')
                if balance_row:
                    balance_value = balance_row.find_all('td')[1].text.strip()
                    # Extract numeric value
                    balance = float(''.join(filter(lambda x: x.isdigit() or x == '.', balance_value)))
                    return {'success': True, 'balance': balance}
            
            return {'success': False, 'error': 'Balance not found in response'}
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}'}
    except Exception as e:
        logger.error(f"Scraping error for {meter_number}: {str(e)}")
        return {'success': False, 'error': str(e)}

# API Endpoints
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

@app.route('/webhook/telegram', methods=['POST'])
def telegram_webhook():
    """Main webhook for Telegram bot commands"""
    data = request.json
    command = data.get('command')
    telegram_user_id = data.get('telegram_user_id')
    
    if command == 'start':
        user = User.query.filter_by(telegram_user_id=telegram_user_id).first()
        if not user:
            user = User(telegram_user_id=telegram_user_id)
            db.session.add(user)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '🎉 Welcome to NESCO Meter Helper!\n\nCommands:\n/add - Add a meter\n/list - List your meters\n/check - Check all balances\n/remove - Remove a meter\n/minbalance - Set minimum balance alert\n/reminder - Toggle daily reminder'
        })
    
    return jsonify({'success': False, 'error': 'Unknown command'})

@app.route('/api/add-meter', methods=['POST'])
def add_meter():
    """Add a new meter for a user"""
    data = request.json
    telegram_user_id = data.get('telegram_user_id')
    meter_number = data.get('meter_number')
    meter_name = data.get('meter_name')
    
    if not all([telegram_user_id, meter_number, meter_name]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    user = User.query.filter_by(telegram_user_id=telegram_user_id).first()
    if not user:
        user = User(telegram_user_id=telegram_user_id)
        db.session.add(user)
        db.session.commit()
    
    # Check if meter already exists
    existing = Meter.query.filter_by(user_id=user.id, meter_number=meter_number).first()
    if existing:
        return jsonify({'success': False, 'error': 'Meter already exists'}), 400
    
    # Verify meter by scraping
    result = scrape_nesco_balance(meter_number)
    if not result['success']:
        return jsonify({'success': False, 'error': f"Cannot verify meter: {result['error']}"}), 400
    
    meter = Meter(
        user_id=user.id,
        meter_number=meter_number,
        meter_name=meter_name,
        last_balance=result['balance'],
        last_checked=datetime.utcnow()
    )
    db.session.add(meter)
    
    # Add to history
    history = BalanceHistory(meter=meter, balance=result['balance'])
    db.session.add(history)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f"✅ Added meter: {meter_name} ({meter_number})\nCurrent balance: {result['balance']} BDT"
    })

@app.route('/api/list-meters', methods=['POST'])
def list_meters():
    """List all meters for a user"""
    data = request.json
    telegram_user_id = data.get('telegram_user_id')
    
    user = User.query.filter_by(telegram_user_id=telegram_user_id).first()
    if not user or not user.meters:
        return jsonify({'success': True, 'meters': [], 'message': 'No meters added yet. Use /add to add one.'})
    
    meters_list = [{
        'id': m.id,
        'name': m.meter_name,
        'number': m.meter_number,
        'min_balance': m.min_balance,
        'last_balance': m.last_balance,
        'last_checked': m.last_checked.isoformat() if m.last_checked else None
    } for m in user.meters]
    
    return jsonify({'success': True, 'meters': meters_list})

@app.route('/api/check-balances', methods=['POST'])
def check_balances():
    """Check balances for all user meters"""
    data = request.json
    telegram_user_id = data.get('telegram_user_id')
    
    user = User.query.filter_by(telegram_user_id=telegram_user_id).first()
    if not user or not user.meters:
        return jsonify({'success': False, 'error': 'No meters found'}), 404
    
    results = []
    yesterday = datetime.utcnow() - timedelta(days=1)
    
    for meter in user.meters:
        # Scrape current balance
        scrape_result = scrape_nesco_balance(meter.meter_number)
        
        if scrape_result['success']:
            current_balance = scrape_result['balance']
            
            # Get yesterday's balance
            yesterday_record = BalanceHistory.query.filter(
                BalanceHistory.meter_id == meter.id,
                BalanceHistory.recorded_at >= yesterday
            ).order_by(BalanceHistory.recorded_at.desc()).first()
            
            yesterday_usage = None
            if yesterday_record:
                yesterday_usage = yesterday_record.balance - current_balance
            
            # Update meter
            meter.last_balance = current_balance
            meter.last_checked = datetime.utcnow()
            
            # Add to history
            history = BalanceHistory(meter_id=meter.id, balance=current_balance)
            db.session.add(history)
            
            # Check min balance alert
            alert = current_balance < meter.min_balance
            
            results.append({
                'name': meter.meter_name,
                'number': meter.meter_number,
                'balance': current_balance,
                'yesterday_usage': yesterday_usage,
                'alert': alert,
                'min_balance': meter.min_balance
            })
        else:
            results.append({
                'name': meter.meter_name,
                'number': meter.meter_number,
                'error': scrape_result['error']
            })
    
    db.session.commit()
    
    return jsonify({'success': True, 'results': results, 'timestamp': datetime.utcnow().isoformat()})

@app.route('/api/remove-meter', methods=['POST'])
def remove_meter():
    """Remove a meter"""
    data = request.json
    telegram_user_id = data.get('telegram_user_id')
    meter_id = data.get('meter_id')
    
    user = User.query.filter_by(telegram_user_id=telegram_user_id).first()
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    meter = Meter.query.filter_by(id=meter_id, user_id=user.id).first()
    if not meter:
        return jsonify({'success': False, 'error': 'Meter not found'}), 404
    
    meter_name = meter.meter_name
    db.session.delete(meter)
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'✅ Removed meter: {meter_name}'})

@app.route('/api/set-min-balance', methods=['POST'])
def set_min_balance():
    """Set minimum balance threshold"""
    data = request.json
    telegram_user_id = data.get('telegram_user_id')
    meter_id = data.get('meter_id')
    min_balance = data.get('min_balance')
    
    user = User.query.filter_by(telegram_user_id=telegram_user_id).first()
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    meter = Meter.query.filter_by(id=meter_id, user_id=user.id).first()
    if not meter:
        return jsonify({'success': False, 'error': 'Meter not found'}), 404
    
    meter.min_balance = float(min_balance)
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'✅ Min balance set to {min_balance} BDT for {meter.meter_name}'})

@app.route('/api/toggle-reminder', methods=['POST'])
def toggle_reminder():
    """Toggle daily reminder"""
    data = request.json
    telegram_user_id = data.get('telegram_user_id')
    
    user = User.query.filter_by(telegram_user_id=telegram_user_id).first()
    if not user:
        user = User(telegram_user_id=telegram_user_id)
        db.session.add(user)
    
    user.daily_reminder_enabled = not user.daily_reminder_enabled
    db.session.commit()
    
    status = 'enabled' if user.daily_reminder_enabled else 'disabled'
    return jsonify({'success': True, 'message': f'✅ Daily reminder {status}'})

@app.route('/api/daily-reminder', methods=['GET'])
def daily_reminder():
    """Cron endpoint for daily reminders"""
    users_with_reminders = User.query.filter_by(daily_reminder_enabled=True).all()
    
    reminders_sent = 0
    for user in users_with_reminders:
        if user.meters:
            reminders_sent += 1
            logger.info(f"Reminder triggered for user {user.telegram_user_id}")
    
    return jsonify({'success': True, 'reminders_sent': reminders_sent})

@app.route('/api/scrape-nesco', methods=['POST'])
def scrape_endpoint():
    """Direct scraping endpoint for testing"""
    data = request.json
    meter_number = data.get('meter_number')
    
    if not meter_number:
        return jsonify({'success': False, 'error': 'meter_number required'}), 400
    
    result = scrape_nesco_balance(meter_number)
    return jsonify(result)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
