from flask import Flask, render_template, request, jsonify
from services.calculator import simulate_rent_vs_buy

app = Flask(__name__)

DEFAULTS = {
    'interest_rate': 0.05,
    'stock_return': 0.07,
    'home_return': 0.03,
    'monthly_rent': 3500.0,
    'rent_insurance': 20.0,
    'rent_inflation': 0.03,
    'monthly_invest': 2000.0,
    'starting_money': 200000.0,
    'home_price': 870000.0,
    'down_payment': 200000.0,
    'property_tax_rate': 0.00575,
    'maintenance_rate': 0.2,
    'home_insurance': 100.0,
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
        'starting_money': parse_float(data.get('starting_money'), DEFAULTS['starting_money']),
        'home_price': parse_float(data.get('home_price'), DEFAULTS['home_price']),
        'down_payment': parse_float(data.get('down_payment'), DEFAULTS['down_payment']),
        'property_tax_rate': parse_float(data.get('property_tax_rate'), DEFAULTS['property_tax_rate']),
        'maintenance_rate': parse_float(data.get('maintenance_rate'), DEFAULTS['maintenance_rate']),
        'home_insurance': parse_float(data.get('home_insurance'), DEFAULTS['home_insurance']),
        'invest_sunk_diff': bool(data.get('invest_sunk_diff', False)),
        'plan_to_sell': bool(data.get('plan_to_sell', False)),
        'sell_year': parse_int(data.get('sell_year'), 0),
        'sell_price': parse_float(data.get('sell_price'), 0.0),
        'sell_costs_rate': parse_float(data.get('sell_costs_rate'), 0.05),
        'sell_legal_fee': parse_float(data.get('sell_legal_fee'), 1500.0),
        'new_home_price': parse_float(data.get('new_home_price'), 0.0),
        'new_home_ltt_rate': parse_float(data.get('new_home_ltt_rate'), 0.015),
        'new_home_lawyer_cost': parse_float(data.get('new_home_lawyer_cost'), 1500.0),
        'new_home_inspection_cost': parse_float(data.get('new_home_inspection_cost'), 500.0),
        'new_home_title_appraisal': parse_float(data.get('new_home_title_appraisal'), 850.0),
        'new_home_gst_hst_rate': parse_float(data.get('new_home_gst_hst_rate'), 0.0),
        'include_closing_costs': bool(data.get('include_closing_costs')),
        'closing_costs_amount': parse_float(data.get('closing_costs_amount'), 0.0),
        'years': parse_int(data.get('years'), DEFAULTS['years']),
    }

    result = simulate_rent_vs_buy(payload)
    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True, port=5001)
