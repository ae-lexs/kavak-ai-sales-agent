"""Unit tests for CalculateFinancingPlan use case."""

import pytest

from app.application.use_cases.calculate_financing_plan import CalculateFinancingPlan
from app.domain.value_objects.loan_term_months import LoanTermMonths
from app.domain.value_objects.money_mxn import MoneyMXN


class TestCalculateFinancingPlan:
    """Test cases for CalculateFinancingPlan."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.calculator = CalculateFinancingPlan()
        self.car_price = MoneyMXN(350000.0)  # $350,000 MXN

    def test_calculate_36_months_with_10_percent_down(self) -> None:
        """Test financing calculation for 36 months with 10% down payment."""
        down_payment = MoneyMXN(35000.0)  # 10%
        term = LoanTermMonths(months=36)

        plan = self.calculator.calculate(self.car_price, down_payment, term)

        assert plan.term_months == 36
        assert plan.financed_amount == 315000.0
        assert plan.monthly_payment > 0
        assert plan.total_paid > plan.financed_amount
        assert plan.total_interest > 0
        # Verify total paid = monthly payment * months
        assert abs(plan.total_paid - (plan.monthly_payment * 36)) < 1.0

    def test_calculate_48_months_with_20_percent_down(self) -> None:
        """Test financing calculation for 48 months with 20% down payment."""
        down_payment = MoneyMXN(70000.0)  # 20%
        term = LoanTermMonths(months=48)

        plan = self.calculator.calculate(self.car_price, down_payment, term)

        assert plan.term_months == 48
        assert plan.financed_amount == 280000.0
        assert plan.monthly_payment > 0
        assert plan.total_paid > plan.financed_amount
        assert plan.total_interest > 0

    def test_calculate_60_months_with_15_percent_down(self) -> None:
        """Test financing calculation for 60 months with 15% down payment."""
        down_payment = MoneyMXN(52500.0)  # 15%
        term = LoanTermMonths(months=60)

        plan = self.calculator.calculate(self.car_price, down_payment, term)

        assert plan.term_months == 60
        assert plan.financed_amount == 297500.0
        assert plan.monthly_payment > 0
        assert plan.total_paid > plan.financed_amount

    def test_calculate_72_months_with_10_percent_down(self) -> None:
        """Test financing calculation for 72 months with 10% down payment."""
        down_payment = MoneyMXN(35000.0)  # 10%
        term = LoanTermMonths(months=72)

        plan = self.calculator.calculate(self.car_price, down_payment, term)

        assert plan.term_months == 72
        assert plan.financed_amount == 315000.0
        assert plan.monthly_payment > 0
        # Longer term should have lower monthly payment but higher total interest
        plan_36 = self.calculator.calculate(self.car_price, down_payment, LoanTermMonths(months=36))
        assert plan.monthly_payment < plan_36.monthly_payment
        assert plan.total_interest > plan_36.total_interest

    def test_minimum_down_payment_10_percent(self) -> None:
        """Test that minimum down payment is 10%."""
        down_payment = MoneyMXN(35000.0)  # Exactly 10%
        term = LoanTermMonths(months=36)

        plan = self.calculator.calculate(self.car_price, down_payment, term)
        assert plan is not None

    def test_down_payment_below_minimum_raises_error(self) -> None:
        """Test that down payment below 10% raises ValueError."""
        down_payment = MoneyMXN(30000.0)  # Less than 10%
        term = LoanTermMonths(months=36)

        with pytest.raises(ValueError, match="Down payment must be at least"):
            self.calculator.calculate(self.car_price, down_payment, term)

    def test_zero_down_payment_raises_error(self) -> None:
        """Test that zero down payment raises error."""
        down_payment = MoneyMXN(0.0)
        term = LoanTermMonths(months=36)

        with pytest.raises(ValueError, match="Down payment must be at least"):
            self.calculator.calculate(self.car_price, down_payment, term)

    def test_down_payment_exceeds_car_price_raises_error(self) -> None:
        """Test that down payment exceeding car price raises error."""
        down_payment = MoneyMXN(400000.0)  # More than car price
        term = LoanTermMonths(months=36)

        with pytest.raises(ValueError, match="Down payment cannot exceed"):
            self.calculator.calculate(self.car_price, down_payment, term)

    def test_high_down_payment_50_percent(self) -> None:
        """Test financing with high down payment (50%)."""
        down_payment = MoneyMXN(175000.0)  # 50%
        term = LoanTermMonths(months=36)

        plan = self.calculator.calculate(self.car_price, down_payment, term)

        assert plan.financed_amount == 175000.0
        assert plan.monthly_payment > 0
        # Higher down payment should result in lower monthly payment
        plan_10pct = self.calculator.calculate(self.car_price, MoneyMXN(35000.0), term)
        assert plan.monthly_payment < plan_10pct.monthly_payment

    def test_calculate_multiple_plans(self) -> None:
        """Test calculating multiple plans for different terms."""
        down_payment = MoneyMXN(35000.0)  # 10%

        plans = self.calculator.calculate_multiple_plans(
            self.car_price, down_payment, terms=[36, 48, 60]
        )

        assert len(plans) == 3
        assert plans[0].term_months == 36
        assert plans[1].term_months == 48
        assert plans[2].term_months == 60

        # Verify monthly payments decrease as term increases
        assert plans[0].monthly_payment > plans[1].monthly_payment
        assert plans[1].monthly_payment > plans[2].monthly_payment

        # Verify total interest increases as term increases
        assert plans[0].total_interest < plans[1].total_interest
        assert plans[1].total_interest < plans[2].total_interest

    def test_calculate_multiple_plans_with_invalid_term(self) -> None:
        """Test that invalid terms are skipped."""
        down_payment = MoneyMXN(35000.0)

        plans = self.calculator.calculate_multiple_plans(
            self.car_price,
            down_payment,
            terms=[36, 24, 48],  # 24 is invalid
        )

        # Should only return valid terms (36, 48)
        assert len(plans) == 2
        assert plans[0].term_months == 36
        assert plans[1].term_months == 48

    def test_financing_calculation_accuracy(self) -> None:
        """Test that financing calculations are mathematically correct."""
        down_payment = MoneyMXN(70000.0)  # 20%
        term = LoanTermMonths(months=48)

        plan = self.calculator.calculate(self.car_price, down_payment, term)

        # Verify: total_paid = financed_amount + total_interest
        assert abs(plan.total_paid - (plan.financed_amount + plan.total_interest)) < 0.01

        # Verify: total_paid ≈ monthly_payment * months (with small rounding tolerance)
        calculated_total = plan.monthly_payment * term.months
        assert abs(plan.total_paid - calculated_total) < 1.0

    def test_different_car_prices(self) -> None:
        """Test financing with different car prices."""
        down_payment_pct = 0.15  # 15%

        for car_price_amount in [200000.0, 500000.0, 1000000.0]:
            car_price = MoneyMXN(car_price_amount)
            down_payment = MoneyMXN(car_price_amount * down_payment_pct)
            term = LoanTermMonths(months=48)

            plan = self.calculator.calculate(car_price, down_payment, term)

            assert plan.financed_amount == car_price_amount * (1 - down_payment_pct)
            assert plan.monthly_payment > 0
            assert plan.total_interest > 0
