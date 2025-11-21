import os
from flask import Flask, render_template, request, jsonify
from models import db, Rates
import requests
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime


def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///currency.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app


app = create_app()

def fetch_external_rates():
    
    url = os.environ.get("EXCHANGE_API_URL", "https://open.er-api.com/v6/latest")
    params = {
        "source": "ecb",
        "symbols": "GBP,USD,AUD,CAD,PLN,MXN"
    }

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if "rates" not in data:
        raise ValueError(f"API response missing 'rates'. Full response: {data}")

    rates_eur = data["rates"] 

    if "GBP" not in rates_eur:
        raise ValueError("API did not return GBP rate, cannot convert.")

    eur_to_gbp = float(rates_eur["GBP"])  

    rates_gbp = {}
    for cur, eur_rate in rates_eur.items():
        if cur == "GBP":
            continue
        if eur_rate == 0:
            continue

        one_cur_in_gbp = eur_to_gbp / float(eur_rate)
        rates_gbp[cur] = one_cur_in_gbp

    timestamp = datetime.utcnow()
    if "date" in data:
        try:
            timestamp = datetime.fromisoformat(data["date"])
        except:
            pass

    return "GBP", rates_gbp, timestamp


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/update_rates', methods=['POST'])
def update_rates():
    try:
        base, rates, timestamp = fetch_external_rates()

        with app.app_context():
            existing = Rates.query.first()
            if existing:
                existing.base = base
                existing.rates = rates
                existing.timestamp = timestamp
            else:
                db.session.add(Rates(base=base, rates=rates, timestamp=timestamp))

            db.session.commit()

        return jsonify({
            "status": "ok",
            "base": base,
            "updated": timestamp.isoformat() + "Z"
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/last_update', methods=['GET'])
def last_update():
    r = Rates.query.first()
    if not r:
        return jsonify({"status": "empty", "message": "No rates in database"}), 404

    return jsonify({
        "status": "ok",
        "base": r.base,
        "timestamp": r.timestamp.isoformat() + "Z"
    })

@app.route('/api/convert', methods=['POST'])
def convert():
    data = request.get_json() or {}

    from_curr = (data.get("from") or data.get("from_currency") or "").upper()
    to_curr = (data.get("to") or data.get("to_currency") or "").upper()
    amount_raw = data.get("amount")

    if not from_curr or not to_curr:
        return jsonify({"status": "error", "message": "Both 'from' and 'to' currencies are required."}), 400

    try:
        amount = Decimal(str(amount_raw))
    except (InvalidOperation, TypeError):
        return jsonify({"status": "error", "message": "Invalid amount."}), 400

    if amount < 0:
        return jsonify({"status": "error", "message": "Amount must be non-negative."}), 400

    r = Rates.query.first()
    if not r:
        return jsonify({"status": "error", "message": "Rates not available. Please update rates first."}), 404

    rates = r.rates
    base = r.base.upper()

    if from_curr not in rates and from_curr != base:
        return jsonify({"status": "error", "message": f"Unknown currency: {from_curr}"}), 400

    if to_curr not in rates and to_curr != base:
        return jsonify({"status": "error", "message": f"Unknown currency: {to_curr}"}), 400
    #Тут конвертируем
    try:
        rate_from = Decimal('1') if from_curr == base else Decimal(str(rates[from_curr]))
        rate_to = Decimal('1') if to_curr == base else Decimal(str(rates[to_curr]))

        if rate_from == 0:
            return jsonify({"status": "error", "message": f"Rate for {from_curr} is zero."}), 500

        amount_in_base = amount / rate_from
        result = amount_in_base * rate_to

        quant = Decimal('0.000001')
        result_q = result.quantize(quant, rounding=ROUND_HALF_UP).normalize()

        return jsonify({
            "status": "ok",
            "from": from_curr,
            "to": to_curr,
            "amount": str(amount.normalize()),
            "result": format(result_q, 'f'),
            "base": base,
            "rates_timestamp": r.timestamp.isoformat() + "Z"
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.cli.command("init-db")
def init_db():
    db.create_all()
    print("DB initialized.")



#Запуск приложения
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
