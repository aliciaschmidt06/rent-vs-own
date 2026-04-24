from flask import Flask, render_template, request, jsonify
from services.calculator import simulate_rent_vs_buy

app = Flask(__name__)

DEFAULTS = {
    'interest_rate': 0.05,
    'stock_return': 0.07,
    'home_return': 0.03,
    'monthly_rent': 3000.0,
    'rent_insurance': 20.0,
    'rent_inflation': 0.03,
    'monthly_invest': 1000.0,
    'initial_investment': 0.0,
    'home_price': 1000000.0,
    'down_payment': 200000.0,
    'property_tax_rate': 0.01,
    'maintenance_rate': 0.005,
    'home_insurance': 1000.0,
    'include_closing_costs': True,
    'years': 25,
}


def parse_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json or {}

    payload = {
        'interest_rate': parse_float(data.get('interest_rate'), DEFAULTS['interest_rate']),
        'stock_return': parse_float(data.get('stock_return'), DEFAULTS['stock_return']),
        'home_return': parse_float(data.get('home_return'), DEFAULTS['home_return']),
        'monthly_rent': parse_float(data.get('monthly_rent'), DEFAULTS['monthly_rent']),
        'rent_insurance': parse_float(data.get('rent_insurance'), DEFAULTS['rent_insurance']),
        'rent_increase': bool(data.get('rent_increase')),
        'rent_inflation': parse_float(data.get('rent_inflation'), DEFAULTS['rent_inflation']),
        'monthly_invest': parse_float(data.get('monthly_invest'), DEFAULTS['monthly_invest']),
        'initial_investment': parse_float(data.get('initial_investment'), DEFAULTS['initial_investment']),
        'home_price': parse_float(data.get('home_price'), DEFAULTS['home_price']),
        'down_payment': parse_float(data.get('down_payment'), DEFAULTS['down_payment']),
        'property_tax_rate': parse_float(data.get('property_tax_rate'), DEFAULTS['property_tax_rate']),
        'maintenance_rate': parse_float(data.get('maintenance_rate'), DEFAULTS['maintenance_rate']),
        'home_insurance': parse_float(data.get('home_insurance'), DEFAULTS['home_insurance']),
        'include_closing_costs': bool(data.get('include_closing_costs')),
        'closing_costs_amount': parse_float(data.get('closing_costs_amount'), 0.0),
        'years': parse_int(data.get('years'), DEFAULTS['years']),
    }

    result = simulate_rent_vs_buy(payload)
    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True, port=5001)
