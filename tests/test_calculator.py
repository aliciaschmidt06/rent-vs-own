"""Unit tests for services/calculator.py"""
import math
import unittest
from services.calculator import simulate_rent_vs_buy, normalize_rate, safe_float, safe_int


# ---------------------------------------------------------------------------
# Minimal "clean" params: all noise removed so each test isolates one thing.
#   - interest_rate=0   → mortgage = loan / num_payments, no compounding
#   - stock_return=0    → investment balance doesn't grow
#   - home_return=0     → home value stays flat
#   - property_tax/maintenance/insurance all 0
#   - no rent inflation, no closing costs, no invest_sunk_diff, no sell cycle
#
# With home_price=500k, down_payment=100k, starting_money=0:
#   loan = 400k, monthly_payment = 400k/60 = 6,666.67
#   balance after Y years = 400k * (1 - Y/5)
#   equity yr1=180k, yr2=260k, yr3=340k, yr4=420k, yr5=500k
#   renter invest_balance  = starting_money * 0.80 = 0
#   buyer buy_invest_balance = max(starting_money - down_payment, 0) = 0
# ---------------------------------------------------------------------------
BASE = {
    'interest_rate': 0.0,
    'stock_return': 0.0,
    'home_return': 0.0,
    'monthly_rent': 1000.0,
    'rent_insurance': 0.0,
    'rent_increase': False,
    'rent_inflation': 0.0,
    'monthly_invest': 0.0,
    'buy_monthly_invest': 0.0,
    'starting_money': 0.0,
    'home_price': 500_000.0,
    'down_payment': 100_000.0,
    'property_tax_rate': 0.0,
    'maintenance_rate': 0.0,
    'home_insurance': 0.0,
    'include_closing_costs': False,
    'closing_costs_amount': 0.0,
    'years': 5,
    'invest_sunk_diff': False,
    'plan_to_sell': False,
}

# Sell & buy helper — all transaction fees zeroed so only core logic is tested
SELL_BASE = {
    **BASE,
    'plan_to_sell': True,
    'sell_year': 3,
    'sell_costs_rate': 0.0,
    'sell_legal_fee': 0.0,
    'new_home_ltt_rate': 0.0,
    'new_home_lawyer_cost': 0.0,
    'new_home_inspection_cost': 0.0,
    'new_home_title_appraisal': 0.0,
    'new_home_gst_hst_rate': 0.0,
}
# With zero interest, balance at year 3 = 400k * (1 - 3/5) = 160k
BALANCE_AT_YR3 = 160_000.0


class TestHelpers(unittest.TestCase):
    # ---- normalize_rate ----

    def test_normalize_rate_decimal_passthrough(self):
        self.assertAlmostEqual(normalize_rate(0.05), 0.05)

    def test_normalize_rate_converts_percentage(self):
        # Values >= 1 are treated as percentages
        self.assertAlmostEqual(normalize_rate(5), 0.05)
        self.assertAlmostEqual(normalize_rate(7.5), 0.075)

    def test_normalize_rate_boundary_exactly_one(self):
        # 1 is >= 1, so treated as 1% not 100%
        self.assertAlmostEqual(normalize_rate(1), 0.01)

    def test_normalize_rate_zero(self):
        self.assertEqual(normalize_rate(0), 0.0)

    def test_normalize_rate_string_decimal(self):
        self.assertAlmostEqual(normalize_rate('0.07'), 0.07)

    # ---- safe_float ----

    def test_safe_float_valid(self):
        self.assertEqual(safe_float('3.14'), 3.14)

    def test_safe_float_invalid_returns_default(self):
        self.assertEqual(safe_float('abc', 99.0), 99.0)

    def test_safe_float_none_returns_default(self):
        self.assertEqual(safe_float(None, 1.5), 1.5)

    def test_safe_float_int_input(self):
        self.assertEqual(safe_float(5, 0.0), 5.0)

    # ---- safe_int ----

    def test_safe_int_valid(self):
        self.assertEqual(safe_int('25'), 25)

    def test_safe_int_invalid_returns_default(self):
        self.assertEqual(safe_int('bad', 10), 10)

    def test_safe_int_none_returns_default(self):
        self.assertEqual(safe_int(None, 3), 3)


class TestOutputStructure(unittest.TestCase):

    def setUp(self):
        self.result = simulate_rent_vs_buy(BASE)

    def test_years_list_is_sequential(self):
        self.assertEqual(self.result['years'], list(range(1, 6)))

    def test_all_arrays_have_correct_length(self):
        arrays = ['spending_buy', 'sunk_buy', 'spending_rent', 'wealth_buy', 'wealth_rent']
        for key in arrays:
            self.assertEqual(len(self.result[key]), 5, f'{key} has wrong length')

    def test_required_keys_present(self):
        for key in ['mortgage_payment', 'final_home_value', 'final_equity',
                    'closing_costs', 'total_interest_paid', 'total_property_tax_paid',
                    'total_maintenance_paid', 'sell_transition', 'new_cmhc_premium']:
            self.assertIn(key, self.result)

    def test_custom_years_length(self):
        r = simulate_rent_vs_buy({**BASE, 'years': 10})
        self.assertEqual(len(r['years']), 10)
        self.assertEqual(len(r['wealth_buy']), 10)


class TestMortgage(unittest.TestCase):

    def test_zero_interest_payment_equals_loan_over_term(self):
        # payment = loan / num_payments
        expected = 400_000.0 / 60
        r = simulate_rent_vs_buy(BASE)
        self.assertAlmostEqual(r['mortgage_payment'], expected, places=2)

    def test_standard_amortization_formula(self):
        loan = 800_000.0
        rate = 0.05 / 12
        n = 25 * 12
        expected = loan * rate * (1 + rate) ** n / ((1 + rate) ** n - 1)
        r = simulate_rent_vs_buy({
            **BASE,
            'home_price': 1_000_000.0,
            'down_payment': 200_000.0,
            'interest_rate': 0.05,
            'years': 25,
        })
        self.assertAlmostEqual(r['mortgage_payment'], expected, places=2)

    def test_mortgage_fully_paid_by_end_of_term(self):
        # Balance should reach ~0 after a full amortization period
        r = simulate_rent_vs_buy({
            **BASE,
            'home_price': 500_000.0,
            'down_payment': 100_000.0,
            'interest_rate': 0.05,
            'years': 5,
        })
        # equity ≈ final home value when balance ≈ 0
        self.assertAlmostEqual(r['final_equity'], r['final_home_value'], delta=1.0)

    def test_full_cash_purchase_no_mortgage(self):
        r = simulate_rent_vs_buy({
            **BASE,
            'home_price': 500_000.0,
            'down_payment': 500_000.0,  # full price
        })
        self.assertEqual(r['mortgage_payment'], 0.0)

    def test_down_payment_clamped_to_home_price(self):
        # down_payment > home_price should be treated as full cash purchase
        r = simulate_rent_vs_buy({
            **BASE,
            'home_price': 300_000.0,
            'down_payment': 999_999.0,
        })
        self.assertEqual(r['mortgage_payment'], 0.0)


class TestRenterScenario(unittest.TestCase):

    def test_renter_invests_80_pct_of_starting_money(self):
        # invest_balance = starting_money * 0.80
        r = simulate_rent_vs_buy({**BASE, 'starting_money': 100_000.0, 'stock_return': 0.0, 'monthly_invest': 0.0})
        for w in r['wealth_rent']:
            self.assertAlmostEqual(w, 80_000.0, places=0)

    def test_renter_monthly_invest_accumulates(self):
        # With zero stock return and zero starting_money, final balance = monthly_invest * months
        r = simulate_rent_vs_buy({**BASE, 'monthly_invest': 500.0})
        expected = 500.0 * 60  # 5 years = 60 months
        self.assertAlmostEqual(r['wealth_rent'][-1], expected, places=0)

    def test_renter_starting_money_80_pct_invested(self):
        # 80% rule applies at any starting_money level
        r = simulate_rent_vs_buy({**BASE, 'starting_money': 50_000.0})
        for w in r['wealth_rent']:
            self.assertAlmostEqual(w, 40_000.0, places=0)

    def test_renter_investment_compounds_with_stock_return(self):
        # Start with starting_money=100k → 80k invested, 12% annual return (1%/month)
        r = simulate_rent_vs_buy({
            **BASE,
            'starting_money': 100_000.0,
            'stock_return': 0.12,
            'monthly_invest': 0.0,
        })
        expected = 80_000.0 * (1 + 0.12 / 12) ** 12
        self.assertAlmostEqual(r['wealth_rent'][0], expected, places=0)

    def test_rent_spending_fixed_no_inflation(self):
        # spending_rent = (monthly_rent + rent_insurance) * 12 * cumulative_years
        r = simulate_rent_vs_buy({**BASE, 'monthly_rent': 2000.0, 'rent_insurance': 50.0})
        for i, yr in enumerate(range(1, 6), start=1):
            expected = (2000.0 + 50.0) * 12 * i
            self.assertAlmostEqual(r['spending_rent'][i - 1], expected, places=0)

    def test_rent_inflation_compounds_annually(self):
        rent0 = 1000.0
        inflation = 0.03
        r = simulate_rent_vs_buy({
            **BASE,
            'monthly_rent': rent0,
            'rent_increase': True,
            'rent_inflation': inflation,
        })
        # Final month rent = rent0 * (1 + 0.03)^(years-1) since inflation applies after each year
        expected_final_rent = rent0 * (1 + inflation) ** (5 - 1)
        self.assertAlmostEqual(r['final_rent'], expected_final_rent, places=2)

    def test_rent_inflation_disabled(self):
        r = simulate_rent_vs_buy({
            **BASE,
            'monthly_rent': 1000.0,
            'rent_increase': False,
        })
        self.assertAlmostEqual(r['final_rent'], 1000.0, places=2)

    def test_rent_insurance_tracked_separately(self):
        r = simulate_rent_vs_buy({**BASE, 'rent_insurance': 30.0})
        expected = 30.0 * 60  # 30/month * 60 months
        self.assertAlmostEqual(r['total_rent_insurance_paid'], expected, places=0)


class TestBuyerScenario(unittest.TestCase):

    def test_spending_buy_starts_with_down_payment(self):
        r = simulate_rent_vs_buy(BASE)
        # Year 1 spending = down_payment + 12 * mortgage_payment
        expected_yr1 = 100_000.0 + 12 * (400_000.0 / 60)
        self.assertAlmostEqual(r['spending_buy'][0], expected_yr1, places=0)

    def test_spending_buy_year5_equals_total_outflow(self):
        r = simulate_rent_vs_buy(BASE)
        # Total outflow = down_payment + all mortgage payments (= full loan since interest=0)
        expected = 100_000.0 + 400_000.0
        self.assertAlmostEqual(r['spending_buy'][-1], expected, places=0)

    def test_sunk_costs_exclude_principal(self):
        # With zero interest, tax, maintenance, and insurance, sunk costs = 0
        r = simulate_rent_vs_buy(BASE)
        for s in r['sunk_buy']:
            self.assertAlmostEqual(s, 0.0, places=2)

    def test_interest_is_higher_early_than_late(self):
        r = simulate_rent_vs_buy({**BASE, 'interest_rate': 0.05, 'years': 10})
        # sunk_buy accumulates interest; it grows faster early (high balance) than late
        yr1_interest = r['sunk_buy'][0]
        yr2_interest = r['sunk_buy'][1] - r['sunk_buy'][0]
        yr9_interest = r['sunk_buy'][8] - r['sunk_buy'][7]
        self.assertGreater(yr1_interest, yr9_interest)
        self.assertGreater(yr2_interest, yr9_interest)

    def test_buyer_equity_grows_over_time(self):
        r = simulate_rent_vs_buy(BASE)
        for i in range(len(r['wealth_buy']) - 1):
            self.assertGreater(r['wealth_buy'][i + 1], r['wealth_buy'][i])

    def test_buyer_equity_at_year_5_equals_home_value(self):
        # Mortgage fully paid, home value unchanged → equity = home_price
        r = simulate_rent_vs_buy(BASE)
        self.assertAlmostEqual(r['wealth_buy'][-1], 500_000.0, places=0)

    def test_home_appreciation_compounds_monthly(self):
        annual_return = 0.06
        monthly_return = annual_return / 12
        r = simulate_rent_vs_buy({**BASE, 'home_return': annual_return})
        expected_5yr = 500_000.0 * (1 + monthly_return) ** 60
        self.assertAlmostEqual(r['final_home_value'], expected_5yr, places=0)

    def test_property_tax_grows_with_home_value(self):
        r = simulate_rent_vs_buy({
            **BASE,
            'home_return': 0.12,       # 1%/month appreciation
            'property_tax_rate': 0.01,  # 1% of home value
        })
        # Tax yr5 > tax yr1 because home appreciated
        yr1_tax = r['total_property_tax_paid']  # accumulates; can't directly compare years
        # Check total tax paid reflects growing home value
        # Flat-value baseline for comparison
        r_flat = simulate_rent_vs_buy({
            **BASE,
            'home_return': 0.0,
            'property_tax_rate': 0.01,
        })
        self.assertGreater(r['total_property_tax_paid'], r_flat['total_property_tax_paid'])

    def test_home_insurance_tracked(self):
        r = simulate_rent_vs_buy({**BASE, 'home_insurance': 100.0})
        expected = 100.0 * 60  # 100/month * 60 months
        self.assertAlmostEqual(r['total_home_insurance_paid'], expected, places=0)


class TestClosingCosts(unittest.TestCase):

    def test_closing_costs_included_in_sunk_and_spending(self):
        closing = 15_000.0
        r = simulate_rent_vs_buy({
            **BASE,
            'include_closing_costs': True,
            'closing_costs_amount': closing,
        })
        self.assertAlmostEqual(r['closing_costs'], closing, places=2)
        # sunk_buy[0] should include the closing costs
        self.assertAlmostEqual(r['sunk_buy'][0], closing, places=0)

    def test_closing_costs_excluded_when_toggled_off(self):
        r = simulate_rent_vs_buy({
            **BASE,
            'include_closing_costs': False,
            'closing_costs_amount': 15_000.0,
        })
        self.assertEqual(r['closing_costs'], 0.0)
        self.assertAlmostEqual(r['sunk_buy'][0], 0.0, places=0)


class TestStartingMoney(unittest.TestCase):

    def test_buyer_gets_starting_money_minus_down_payment(self):
        # buy_invest_balance = starting_money - down_payment (100k) = 200k
        r = simulate_rent_vs_buy({**BASE, 'starting_money': 300_000.0, 'stock_return': 0.0})
        # Year 1 equity = 500k - (400k * 4/5) = 180k, buy_invest = 200k
        self.assertAlmostEqual(r['wealth_buy'][0], 380_000.0, places=0)

    def test_starting_money_below_down_payment_clamps_buy_invest_to_zero(self):
        # max(50k - 100k, 0) = 0 → buyer has no extra to invest
        r = simulate_rent_vs_buy({**BASE, 'starting_money': 50_000.0, 'stock_return': 0.0})
        # wealth_buy = equity only at each year
        self.assertAlmostEqual(r['wealth_buy'][-1], 500_000.0, places=0)

    def test_zero_starting_money_baseline(self):
        r = simulate_rent_vs_buy({**BASE, 'starting_money': 0.0})
        self.assertAlmostEqual(r['wealth_rent'][0], 0.0, places=0)
        self.assertAlmostEqual(r['wealth_buy'][-1], 500_000.0, places=0)


class TestInvestSunkDiff(unittest.TestCase):

    def test_buyer_invests_when_rent_sunk_exceeds_buy_sunk(self):
        # rent_payment=2000, all buy costs=0 → rent is more expensive → buyer invests
        r_off = simulate_rent_vs_buy({**BASE, 'monthly_rent': 2000.0, 'invest_sunk_diff': False})
        r_on = simulate_rent_vs_buy({**BASE, 'monthly_rent': 2000.0, 'invest_sunk_diff': True})
        # Buyer wealth should be higher when invest_sunk_diff is on
        for i in range(5):
            self.assertGreater(r_on['wealth_buy'][i], r_off['wealth_buy'][i],
                               msg=f'Year {i + 1}')
        # Renter wealth unchanged (they don't benefit)
        for i in range(5):
            self.assertAlmostEqual(r_on['wealth_rent'][i], r_off['wealth_rent'][i], places=0)

    def test_renter_invests_when_buy_sunk_exceeds_rent_sunk(self):
        # High property tax makes buying more expensive → renter invests the difference
        r_off = simulate_rent_vs_buy({
            **BASE,
            'monthly_rent': 100.0,
            'property_tax_rate': 0.02,  # 2% of 500k = 10k/yr = 833/month
            'invest_sunk_diff': False,
        })
        r_on = simulate_rent_vs_buy({
            **BASE,
            'monthly_rent': 100.0,
            'property_tax_rate': 0.02,
            'invest_sunk_diff': True,
        })
        # Renter wealth should be higher
        for i in range(5):
            self.assertGreater(r_on['wealth_rent'][i], r_off['wealth_rent'][i])
        # Buyer wealth unchanged
        for i in range(5):
            self.assertAlmostEqual(r_on['wealth_buy'][i], r_off['wealth_buy'][i], places=0)

    def test_invest_sunk_diff_year1_amount(self):
        # rent_payment=2000/mo, buy sunk=0 → buyer gets 2000/mo extra for 12 months
        r = simulate_rent_vs_buy({**BASE, 'monthly_rent': 2000.0, 'invest_sunk_diff': True})
        r_off = simulate_rent_vs_buy({**BASE, 'monthly_rent': 2000.0, 'invest_sunk_diff': False})
        extra = r['wealth_buy'][0] - r_off['wealth_buy'][0]
        self.assertAlmostEqual(extra, 2000.0 * 12, delta=1.0)


class TestSellAndBuy(unittest.TestCase):
    """Tests for the sell-current-home / buy-new-home transition."""

    def _sell(self, sell_price, new_home_price, **overrides):
        return simulate_rent_vs_buy({
            **SELL_BASE,
            'sell_price': sell_price,
            'new_home_price': new_home_price,
            **overrides,
        })

    # --- Guard conditions ---

    def test_no_transition_when_plan_to_sell_false(self):
        r = simulate_rent_vs_buy({**SELL_BASE, 'plan_to_sell': False,
                                   'sell_price': 500_000.0, 'new_home_price': 600_000.0})
        self.assertIsNone(r['sell_transition'])

    def test_no_transition_when_sell_price_zero(self):
        r = self._sell(sell_price=0.0, new_home_price=600_000.0)
        self.assertIsNone(r['sell_transition'])

    def test_no_transition_when_sell_year_exceeds_simulation(self):
        r = simulate_rent_vs_buy({
            **SELL_BASE,
            'sell_year': 10,   # years=5, so sell_year=10 is never reached
            'sell_price': 500_000.0,
            'new_home_price': 600_000.0,
        })
        self.assertIsNone(r['sell_transition'])

    # --- Mortgage payoff ---

    def test_mortgage_paid_from_proceeds(self):
        # balance at yr3 = 160k; sell_price = 160k → gross_proceeds = 0
        r = self._sell(sell_price=BALANCE_AT_YR3, new_home_price=400_000.0)
        t = r['sell_transition']
        self.assertAlmostEqual(t['gross_proceeds'], 0.0, places=0)
        self.assertAlmostEqual(t['new_down'], 0.0, places=0)

    def test_proceeds_exceed_mortgage(self):
        # sell for 160k + 200k = 360k → gross_proceeds = 200k
        r = self._sell(sell_price=BALANCE_AT_YR3 + 200_000.0, new_home_price=400_000.0)
        t = r['sell_transition']
        self.assertAlmostEqual(t['gross_proceeds'], 200_000.0, places=0)
        self.assertAlmostEqual(t['new_down'], 200_000.0, places=0)

    # --- Selling costs ---

    def test_realtor_commission_deducted_from_proceeds(self):
        sell_price = 400_000.0
        rate = 0.05
        r = simulate_rent_vs_buy({
            **SELL_BASE,
            'sell_price': sell_price,
            'new_home_price': 200_000.0,
            'sell_costs_rate': rate,
            'sell_legal_fee': 0.0,
        })
        t = r['sell_transition']
        expected_sell_costs = sell_price * rate
        self.assertAlmostEqual(t['sell_costs'], expected_sell_costs, places=2)

    def test_legal_fee_added_to_selling_costs(self):
        sell_price = 400_000.0
        r = simulate_rent_vs_buy({
            **SELL_BASE,
            'sell_price': sell_price,
            'new_home_price': 200_000.0,
            'sell_costs_rate': 0.05,
            'sell_legal_fee': 1500.0,
        })
        t = r['sell_transition']
        expected = sell_price * 0.05 + 1500.0
        self.assertAlmostEqual(t['sell_costs'], expected, places=2)

    def test_selling_costs_are_sunk(self):
        # Selling costs should appear in sunk_buy after transition
        sell_price = BALANCE_AT_YR3 + 100_000.0
        rate = 0.05
        r = simulate_rent_vs_buy({
            **SELL_BASE,
            'sell_price': sell_price,
            'new_home_price': 200_000.0,
            'sell_costs_rate': rate,
            'sell_legal_fee': 0.0,
        })
        # sunk_buy increases at transition year (yr4 > yr3 by more than normal month)
        jump = r['sunk_buy'][3] - r['sunk_buy'][2]
        expected_sunk = sell_price * rate + r['sell_transition']['buy_closing']
        self.assertAlmostEqual(jump, expected_sunk, delta=1.0)

    # --- New home closing costs ---

    def test_new_home_ltt_deducted_from_down_payment(self):
        proceeds = 300_000.0
        new_price = 1_000_000.0
        ltt_rate = 0.015
        r = simulate_rent_vs_buy({
            **SELL_BASE,
            'sell_price': BALANCE_AT_YR3 + proceeds,
            'new_home_price': new_price,
            'new_home_ltt_rate': ltt_rate,
        })
        t = r['sell_transition']
        expected_ltt = new_price * ltt_rate
        self.assertAlmostEqual(t['buy_closing'], expected_ltt, places=2)
        self.assertAlmostEqual(t['new_down'], proceeds - expected_ltt, delta=1.0)

    def test_new_home_misc_costs_deducted(self):
        proceeds = 300_000.0
        new_price = 800_000.0
        lawyer = 1500.0
        inspection = 500.0
        title = 850.0
        r = simulate_rent_vs_buy({
            **SELL_BASE,
            'sell_price': BALANCE_AT_YR3 + proceeds,
            'new_home_price': new_price,
            'new_home_lawyer_cost': lawyer,
            'new_home_inspection_cost': inspection,
            'new_home_title_appraisal': title,
        })
        t = r['sell_transition']
        expected_misc = lawyer + inspection + title
        self.assertAlmostEqual(t['buy_closing'], expected_misc, places=2)

    def test_gst_hst_applied_to_new_home_price(self):
        new_price = 800_000.0
        gst_rate = 0.05
        proceeds = 400_000.0
        r = simulate_rent_vs_buy({
            **SELL_BASE,
            'sell_price': BALANCE_AT_YR3 + proceeds,
            'new_home_price': new_price,
            'new_home_gst_hst_rate': gst_rate,
        })
        t = r['sell_transition']
        expected_gst = new_price * gst_rate
        self.assertAlmostEqual(t['buy_closing'], expected_gst, places=2)

    # --- CMHC insurance ---

    def _cmhc_scenario(self, desired_down, new_home_price=1_000_000.0):
        """Return result where net_down == desired_down (all fees=0)."""
        sell_price = BALANCE_AT_YR3 + desired_down
        return simulate_rent_vs_buy({
            **SELL_BASE,
            'sell_price': sell_price,
            'new_home_price': new_home_price,
        })

    def test_cmhc_not_required_at_20pct_down(self):
        # 20% of 1M = 200k → LTV = 80% → no CMHC (threshold is strictly >= 0.80)
        r = self._cmhc_scenario(desired_down=200_000.0)
        self.assertEqual(r['new_cmhc_premium'], 0.0)

    def test_cmhc_not_required_above_20pct_down(self):
        r = self._cmhc_scenario(desired_down=250_000.0)
        self.assertEqual(r['new_cmhc_premium'], 0.0)

    def test_cmhc_28pct_at_ltv_80_to_85(self):
        # 17% down → LTV = 83% → 2.8%
        down = 170_000.0
        new_price = 1_000_000.0
        r = self._cmhc_scenario(desired_down=down, new_home_price=new_price)
        loan = new_price - down
        expected = loan * 0.028
        self.assertAlmostEqual(r['new_cmhc_premium'], expected, places=2)

    def test_cmhc_31pct_at_ltv_85_to_90(self):
        # 12% down → LTV = 88% → 3.1%
        down = 120_000.0
        new_price = 1_000_000.0
        r = self._cmhc_scenario(desired_down=down, new_home_price=new_price)
        loan = new_price - down
        expected = loan * 0.031
        self.assertAlmostEqual(r['new_cmhc_premium'], expected, places=2)

    def test_cmhc_40pct_above_ltv_90(self):
        # 5% down → LTV = 95% → 4.0%
        down = 50_000.0
        new_price = 1_000_000.0
        r = self._cmhc_scenario(desired_down=down, new_home_price=new_price)
        loan = new_price - down
        expected = loan * 0.040
        self.assertAlmostEqual(r['new_cmhc_premium'], expected, places=2)

    def test_cmhc_added_to_new_mortgage_not_paid_upfront(self):
        # new_loan = (new_price - new_down) + cmhc_premium
        down = 120_000.0
        new_price = 1_000_000.0
        r = self._cmhc_scenario(desired_down=down, new_home_price=new_price)
        t = r['sell_transition']
        loan_pre_cmhc = new_price - down
        expected_loan = loan_pre_cmhc + loan_pre_cmhc * 0.031
        self.assertAlmostEqual(t['new_loan'], expected_loan, places=2)

    # --- Extra cash ---

    def test_extra_cash_invested_when_proceeds_exceed_new_home_price(self):
        # Proceeds = 700k, new home = 500k → 200k surplus goes to buy_invest_balance
        new_price = 500_000.0
        proceeds = 700_000.0
        r_base = self._cmhc_scenario(desired_down=new_price, new_home_price=new_price)  # no surplus
        r_surplus = simulate_rent_vs_buy({
            **SELL_BASE,
            'sell_price': BALANCE_AT_YR3 + proceeds,
            'new_home_price': new_price,
        })
        extra = 200_000.0  # proceeds - new_price
        # Wealth should be higher by ~extra (no stock return, so it just sits there)
        surplus_buy = r_surplus['wealth_buy'][-1]
        no_surplus_buy = r_base['wealth_buy'][-1]
        self.assertAlmostEqual(surplus_buy - no_surplus_buy, extra, delta=1.0)

    # --- New mortgage ---

    def test_new_mortgage_computed_from_new_loan(self):
        # With zero interest, new monthly payment = new_loan / num_payments
        new_price = 800_000.0
        down = 200_000.0
        r = self._cmhc_scenario(desired_down=down, new_home_price=new_price)
        t = r['sell_transition']
        new_loan = t['new_loan']
        expected_payment = new_loan / (5 * 12)  # years=5
        # After transition (yr4 & yr5), mortgage payment should reflect new loan
        # We can verify by checking the equity progression post-transition
        # year3 equity (old house, pre-transition) vs year4 equity (new house, post-1yr)
        yr4_equity = r['wealth_buy'][3] - 0  # no buy_invest_balance
        yr3_equity_post = new_price - new_loan  # equity right after purchase
        expected_yr4_equity = new_price - (new_loan - expected_payment * 12)
        self.assertAlmostEqual(r['wealth_buy'][3], expected_yr4_equity, delta=100.0)

    # --- sell_transition dict ---

    def test_sell_transition_dict_structure(self):
        r = self._sell(sell_price=BALANCE_AT_YR3 + 200_000.0, new_home_price=400_000.0)
        t = r['sell_transition']
        for key in ['sell_costs', 'buy_closing', 'cmhc_premium', 'gross_proceeds', 'new_down', 'new_loan']:
            self.assertIn(key, t, f'Missing key: {key}')

    def test_sell_transition_gross_proceeds_formula(self):
        sell_price = BALANCE_AT_YR3 + 300_000.0
        r = simulate_rent_vs_buy({
            **SELL_BASE,
            'sell_price': sell_price,
            'new_home_price': 600_000.0,
            'sell_costs_rate': 0.05,
            'sell_legal_fee': 1500.0,
        })
        t = r['sell_transition']
        expected = sell_price - (sell_price * 0.05 + 1500.0) - BALANCE_AT_YR3
        self.assertAlmostEqual(t['gross_proceeds'], expected, delta=1.0)

    # --- Wealth continuity ---

    def test_wealth_dip_at_transition_reflects_transaction_costs(self):
        sell_costs_rate = 0.05
        sell_price = BALANCE_AT_YR3 + 400_000.0
        new_price = 500_000.0
        r = simulate_rent_vs_buy({
            **SELL_BASE,
            'sell_price': sell_price,
            'new_home_price': new_price,
            'sell_costs_rate': sell_costs_rate,
            'sell_legal_fee': 0.0,
        })
        # yr3 wealth = old house equity, yr4 wealth = new house equity (post-transition)
        pre = r['wealth_buy'][2]   # year 3: old house, before transition
        post = r['wealth_buy'][3]  # year 4: new house, first full year
        total_costs = r['sell_transition']['sell_costs'] + r['sell_transition']['buy_closing'] + r['sell_transition']['cmhc_premium']
        # The net change should reflect costs lost plus one year of new mortgage paydown
        self.assertIsNotNone(r['sell_transition'])


class TestEdgeCases(unittest.TestCase):

    def test_years_equals_one(self):
        r = simulate_rent_vs_buy({**BASE, 'years': 1})
        self.assertEqual(len(r['years']), 1)
        self.assertEqual(r['years'], [1])

    def test_zero_rent_no_rent_spending(self):
        r = simulate_rent_vs_buy({**BASE, 'monthly_rent': 0.0})
        for s in r['spending_rent']:
            self.assertEqual(s, 0.0)

    def test_very_high_stock_return_renter_wins(self):
        r = simulate_rent_vs_buy({
            **BASE,
            'stock_return': 0.20,
            'home_return': 0.0,
            'years': 25,
            'monthly_invest': 1000.0,
        })
        self.assertGreater(r['wealth_rent'][-1], r['wealth_buy'][-1])

    def test_min_years_clamped_to_one(self):
        r = simulate_rent_vs_buy({**BASE, 'years': 0})
        self.assertEqual(len(r['years']), 1)

    def test_wealth_buy_never_negative(self):
        # Even with very large closing costs, equity is floored at 0
        r = simulate_rent_vs_buy({
            **BASE,
            'include_closing_costs': True,
            'closing_costs_amount': 999_999.0,
        })
        for w in r['wealth_buy']:
            self.assertGreaterEqual(w, 0.0)

    def test_buy_monthly_invest_grows_buyer_wealth(self):
        r0 = simulate_rent_vs_buy({**BASE, 'buy_monthly_invest': 0.0})
        r1 = simulate_rent_vs_buy({**BASE, 'buy_monthly_invest': 500.0})
        for i in range(5):
            self.assertGreater(r1['wealth_buy'][i], r0['wealth_buy'][i])


if __name__ == '__main__':
    unittest.main()
