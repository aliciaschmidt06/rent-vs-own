def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_rate(rate):
    rate = safe_float(rate, 0.0)
    if rate >= 1:
        return rate / 100.0
    return rate


def simulate_rent_vs_buy(params):
    interest_rate = normalize_rate(params.get('interest_rate', 0.05))
    stock_return = normalize_rate(params.get('stock_return', 0.07))
    home_return = normalize_rate(params.get('home_return', 0.03))

    rent_increase = bool(params.get('rent_increase'))
    rent_inflation = normalize_rate(params.get('rent_inflation', 0.03)) if rent_increase else 0.0
    monthly_invest = max(safe_float(params.get('monthly_invest'), 1000.0), 0.0)
    initial_investment = max(safe_float(params.get('initial_investment'), 0.0), 0.0)

    home_price = max(safe_float(params.get('home_price'), 1000000.0), 0.0)
    down_payment = max(min(safe_float(params.get('down_payment'), 200000.0), home_price), 0.0)
    property_tax_rate = max(safe_float(params.get('property_tax_rate')), 0.0)
    maintenance_rate = max(safe_float(params.get('maintenance_rate')), 0.0)
    years = max(safe_int(params.get('years'), 25), 1)

    loan_amount = home_price - down_payment
    monthly_rate = interest_rate / 12
    stock_monthly_rate = stock_return / 12
    home_monthly_rate = home_return / 12
    num_payments = years * 12

    if loan_amount <= 0:
        mortgage_payment = 0.0
    elif monthly_rate > 0:
        mortgage_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
    else:
        mortgage_payment = loan_amount / num_payments

    include_closing_costs = bool(params.get('include_closing_costs', True))
    closing_costs = max(safe_float(params.get('closing_costs_amount'), 0.0), 0.0) if include_closing_costs else 0.0

    rent_insurance = max(safe_float(params.get('rent_insurance'), 20.0), 0.0)
    home_insurance = max(safe_float(params.get('home_insurance'), 100.0), 0.0)

    balance = loan_amount
    home_value = home_price
    rent_payment = max(safe_float(params.get('monthly_rent'), 3000.0), 0.0)
    invest_balance = initial_investment

    cumulative_buy_spending = down_payment + closing_costs
    cumulative_buy_sunk = closing_costs
    cumulative_interest = 0.0
    cumulative_property_tax = 0.0
    cumulative_maintenance = 0.0
    cumulative_home_insurance = 0.0
    cumulative_rent_spending = 0.0
    cumulative_rent_insurance = 0.0

    spending_buy = []
    sunk_buy = []
    spending_rent = []
    wealth_buy = []
    wealth_rent = []

    for _year in range(1, years + 1):
        for _month in range(1, 13):
            if balance > 0 and mortgage_payment > 0:
                interest = balance * monthly_rate
                principal = mortgage_payment - interest
                if principal > balance:
                    principal = balance
                balance -= principal
            else:
                interest = 0.0
                principal = 0.0

            home_value *= 1 + home_monthly_rate
            property_tax = home_value * property_tax_rate / 12
            maintenance_cost = home_value * maintenance_rate / 12
            monthly_buy_cost = mortgage_payment + property_tax + maintenance_cost + home_insurance

            cumulative_buy_spending += monthly_buy_cost
            cumulative_buy_sunk += interest + property_tax + maintenance_cost + home_insurance
            cumulative_interest += interest
            cumulative_property_tax += property_tax
            cumulative_maintenance += maintenance_cost
            cumulative_home_insurance += home_insurance
            cumulative_rent_spending += rent_payment + rent_insurance
            cumulative_rent_insurance += rent_insurance

            invest_balance *= 1 + stock_monthly_rate
            invest_balance += monthly_invest

        final_monthly_rent = rent_payment
        if rent_increase:
            rent_payment *= 1 + rent_inflation

        equity = max(home_value - balance, 0.0)
        spending_buy.append(round(cumulative_buy_spending, 2))
        sunk_buy.append(round(cumulative_buy_sunk, 2))
        spending_rent.append(round(cumulative_rent_spending, 2))
        wealth_buy.append(round(equity, 2))
        wealth_rent.append(round(invest_balance, 2))

    total_paid = round(mortgage_payment * num_payments, 2)
    total_interest = round(max(total_paid - loan_amount, 0.0), 2)

    return {
        'years': list(range(1, years + 1)),
        'spending_buy': spending_buy,
        'sunk_buy': sunk_buy,
        'spending_rent': spending_rent,
        'wealth_buy': wealth_buy,
        'wealth_rent': wealth_rent,
        'mortgage_payment': round(mortgage_payment, 2),
        'total_paid': total_paid,
        'total_interest': total_interest,
        'final_home_value': round(home_value, 2),
        'final_equity': round(equity, 2),
        'rent_investment_value': round(invest_balance, 2),
        'final_rent': round(final_monthly_rent, 2),
        'closing_costs': round(closing_costs, 2),
        'total_interest_paid': round(cumulative_interest, 2),
        'total_property_tax_paid': round(cumulative_property_tax, 2),
        'total_maintenance_paid': round(cumulative_maintenance, 2),
        'total_home_insurance_paid': round(cumulative_home_insurance, 2),
        'total_rent_insurance_paid': round(cumulative_rent_insurance, 2),
    }
