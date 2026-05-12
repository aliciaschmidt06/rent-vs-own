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
    buy_monthly_invest = max(safe_float(params.get('buy_monthly_invest'), 0.0), 0.0)
    invest_sunk_diff = bool(params.get('invest_sunk_diff', False))
    starting_money = max(safe_float(params.get('starting_money'), 0.0), 0.0)

    home_price = max(safe_float(params.get('home_price'), 1000000.0), 0.0)
    down_payment = max(min(safe_float(params.get('down_payment'), 200000.0), home_price), 0.0)
    property_tax_rate = max(safe_float(params.get('property_tax_rate')), 0.0)
    maintenance_rate = max(safe_float(params.get('maintenance_rate')), 0.0)
    years = max(safe_int(params.get('years'), 25), 1)

    plan_to_sell = bool(params.get('plan_to_sell', False))
    sell_year = safe_int(params.get('sell_year', 0), 0)
    sell_price = max(safe_float(params.get('sell_price'), 0.0), 0.0)
    sell_costs_rate = max(safe_float(params.get('sell_costs_rate'), 0.05), 0.0)
    sell_legal_fee = max(safe_float(params.get('sell_legal_fee'), 1500.0), 0.0)
    new_home_price = max(safe_float(params.get('new_home_price'), 0.0), 0.0)
    new_home_ltt_rate = max(safe_float(params.get('new_home_ltt_rate'), 0.015), 0.0)
    new_home_lawyer_cost = max(safe_float(params.get('new_home_lawyer_cost'), 1500.0), 0.0)
    new_home_inspection_cost = max(safe_float(params.get('new_home_inspection_cost'), 500.0), 0.0)
    new_home_title_appraisal = max(safe_float(params.get('new_home_title_appraisal'), 850.0), 0.0)
    new_home_gst_hst_rate = max(safe_float(params.get('new_home_gst_hst_rate'), 0.0), 0.0)

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

    original_mortgage_payment = mortgage_payment

    include_closing_costs = bool(params.get('include_closing_costs', True))
    closing_costs = max(safe_float(params.get('closing_costs_amount'), 0.0), 0.0) if include_closing_costs else 0.0

    rent_insurance = max(safe_float(params.get('rent_insurance'), 20.0), 0.0)
    home_insurance = max(safe_float(params.get('home_insurance'), 100.0), 0.0)

    balance = loan_amount
    home_value = home_price
    rent_payment = max(safe_float(params.get('monthly_rent'), 3000.0), 0.0)
    invest_balance = starting_money * 0.80
    buy_invest_balance = max(starting_money - down_payment, 0.0)

    cumulative_buy_spending = down_payment + closing_costs
    cumulative_buy_sunk = closing_costs
    cumulative_interest = 0.0
    cumulative_property_tax = 0.0
    cumulative_maintenance = 0.0
    cumulative_home_insurance = 0.0
    cumulative_rent_spending = 0.0
    cumulative_rent_insurance = 0.0

    new_cmhc_premium = 0.0
    sell_transition = None

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
            buy_invest_balance *= 1 + stock_monthly_rate
            buy_invest_balance += buy_monthly_invest

            if invest_sunk_diff:
                rent_monthly_sunk = rent_payment + rent_insurance
                buy_monthly_sunk = interest + property_tax + maintenance_cost + home_insurance
                sunk_diff = rent_monthly_sunk - buy_monthly_sunk
                if sunk_diff > 0:
                    buy_invest_balance += sunk_diff
                else:
                    invest_balance += -sunk_diff

        final_monthly_rent = rent_payment
        if rent_increase:
            rent_payment *= 1 + rent_inflation

        equity = max(home_value - balance, 0.0)
        spending_buy.append(round(cumulative_buy_spending, 2))
        sunk_buy.append(round(cumulative_buy_sunk, 2))
        spending_rent.append(round(cumulative_rent_spending, 2))
        wealth_buy.append(round(equity + buy_invest_balance, 2))
        wealth_rent.append(round(invest_balance, 2))

        if plan_to_sell and _year == sell_year and new_home_price > 0 and sell_price > 0:
            # --- Selling costs ---
            sell_commission = sell_price * sell_costs_rate
            total_sell_costs = sell_commission + sell_legal_fee
            gross_proceeds = sell_price - total_sell_costs - balance  # remaining mortgage paid off here

            # --- New home closing costs (paid from proceeds) ---
            new_ltt = new_home_price * new_home_ltt_rate
            new_gst_hst = new_home_price * new_home_gst_hst_rate
            new_misc = new_home_lawyer_cost + new_home_inspection_cost + new_home_title_appraisal
            total_buy_closing = new_ltt + new_gst_hst + new_misc

            net_after_all_costs = gross_proceeds - total_buy_closing
            new_down = max(net_after_all_costs, 0.0)
            extra_cash = max(net_after_all_costs - new_home_price, 0.0)
            buy_invest_balance += extra_cash

            # --- CMHC insurance (required if LTV >= 80%, added to mortgage) ---
            new_loan_pre_cmhc = max(new_home_price - new_down, 0.0)
            ltv = new_loan_pre_cmhc / new_home_price if new_home_price > 0 else 0.0
            if ltv >= 0.90:
                cmhc_rate = 0.040
            elif ltv >= 0.85:
                cmhc_rate = 0.031
            elif ltv >= 0.80:
                cmhc_rate = 0.028
            else:
                cmhc_rate = 0.0
            new_cmhc_premium = new_loan_pre_cmhc * cmhc_rate
            new_loan = new_loan_pre_cmhc + new_cmhc_premium

            # All sunk costs from the transaction
            transition_sunk = total_sell_costs + total_buy_closing + new_cmhc_premium
            cumulative_buy_sunk += transition_sunk
            cumulative_buy_spending += transition_sunk

            balance = new_loan
            home_value = new_home_price
            if new_loan <= 0:
                mortgage_payment = 0.0
            elif monthly_rate > 0:
                mortgage_payment = new_loan * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
            else:
                mortgage_payment = new_loan / num_payments

            sell_transition = {
                'sell_costs': round(total_sell_costs, 2),
                'buy_closing': round(total_buy_closing, 2),
                'cmhc_premium': round(new_cmhc_premium, 2),
                'gross_proceeds': round(gross_proceeds, 2),
                'new_down': round(new_down, 2),
                'new_loan': round(new_loan, 2),
            }

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
        'original_mortgage_payment': round(original_mortgage_payment, 2),
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
        'new_cmhc_premium': round(new_cmhc_premium, 2),
        'sell_transition': sell_transition,
    }


def simulate_rent_then_buy_comparison(params):
    interest_rate = normalize_rate(params.get('interest_rate', 0.05))
    stock_return = normalize_rate(params.get('stock_return', 0.07))
    home_return = normalize_rate(params.get('home_return', 0.03))
    total_years = max(safe_int(params.get('total_years'), 25), 2)
    starting_money = max(safe_float(params.get('starting_money'), 0.0), 0.0)

    monthly_rate = interest_rate / 12
    stock_monthly_rate = stock_return / 12
    home_monthly_rate = home_return / 12

    # --- Scenario 1: Buy Now ---
    home_price_now = max(safe_float(params.get('home_price_now'), 870_000.0), 0.0)
    down_now = max(min(safe_float(params.get('down_payment_now'), 200_000.0), home_price_now), 0.0)
    invest_owning_now = max(safe_float(params.get('invest_while_owning_now'), 2000.0), 0.0)

    loan_now = home_price_now - down_now
    num_p_now = total_years * 12
    if loan_now <= 0:
        mortgage_now = 0.0
    elif monthly_rate > 0:
        mortgage_now = loan_now * (monthly_rate * (1 + monthly_rate) ** num_p_now) / ((1 + monthly_rate) ** num_p_now - 1)
    else:
        mortgage_now = loan_now / num_p_now

    # --- Scenario 2: Rent Then Buy ---
    rent_years = max(min(safe_int(params.get('rent_years'), 3), total_years - 1), 1)
    invest_renting = max(safe_float(params.get('invest_while_renting'), 2000.0), 0.0)
    invest_owning_later = max(safe_float(params.get('invest_while_owning_later'), 2000.0), 0.0)
    future_home_price = max(safe_float(params.get('future_home_price'), 1_200_000.0), 0.0)
    future_mortgage_years = max(safe_int(params.get('future_mortgage_years'), 25), 1)

    # --- Initial state ---
    b1_balance = loan_now
    b1_home = home_price_now
    b1_invest = max(starting_money - down_now, 0.0)

    b2_invest = starting_money * 0.80
    b2_balance = 0.0
    b2_home = 0.0
    b2_mortgage = 0.0
    b2_bought = False
    b2_down_used = 0.0

    wealth_buy_now = []
    wealth_rent_then_buy = []

    for year in range(1, total_years + 1):
        for month in range(1, 13):
            # Scenario 1: Buy Now — monthly mortgage + invest
            if b1_balance > 0 and mortgage_now > 0:
                interest = b1_balance * monthly_rate
                principal = min(mortgage_now - interest, b1_balance)
                b1_balance = max(b1_balance - principal, 0.0)
            b1_home *= (1 + home_monthly_rate)
            b1_invest = b1_invest * (1 + stock_monthly_rate) + invest_owning_now

            # Scenario 2: Rent Then Buy
            if not b2_bought:
                b2_invest = b2_invest * (1 + stock_monthly_rate) + invest_renting
                if year == rent_years and month == 12:
                    # Purchase the future home using all accumulated savings as down payment
                    b2_down_used = min(b2_invest, future_home_price)
                    new_loan = max(future_home_price - b2_down_used, 0.0)
                    b2_invest = max(b2_invest - future_home_price, 0.0)
                    b2_home = future_home_price
                    b2_balance = new_loan
                    num_p_later = future_mortgage_years * 12
                    if new_loan <= 0:
                        b2_mortgage = 0.0
                    elif monthly_rate > 0:
                        b2_mortgage = new_loan * (monthly_rate * (1 + monthly_rate) ** num_p_later) / ((1 + monthly_rate) ** num_p_later - 1)
                    else:
                        b2_mortgage = new_loan / num_p_later
                    b2_bought = True
            else:
                if b2_balance > 0 and b2_mortgage > 0:
                    interest = b2_balance * monthly_rate
                    principal = min(b2_mortgage - interest, b2_balance)
                    b2_balance = max(b2_balance - principal, 0.0)
                b2_home *= (1 + home_monthly_rate)
                b2_invest = b2_invest * (1 + stock_monthly_rate) + invest_owning_later

        b1_equity = max(b1_home - b1_balance, 0.0)
        wealth_buy_now.append(round(b1_equity + b1_invest, 2))

        if b2_bought:
            b2_equity = max(b2_home - b2_balance, 0.0)
            wealth_rent_then_buy.append(round(b2_equity + b2_invest, 2))
        else:
            wealth_rent_then_buy.append(round(b2_invest, 2))

    return {
        'years': list(range(1, total_years + 1)),
        'wealth_buy_now': wealth_buy_now,
        'wealth_rent_then_buy': wealth_rent_then_buy,
        'mortgage_buy_now': round(mortgage_now, 2),
        'mortgage_rent_then_buy': round(b2_mortgage, 2),
        'down_used_rent_then_buy': round(b2_down_used, 2),
        'rent_years': rent_years,
    }
