"""Calculate financing plan use case."""

import math
from typing import Optional

from app.application.dtos.financing import FinancingPlan
from app.domain.value_objects.apr import APR
from app.domain.value_objects.loan_term_months import LoanTermMonths
from app.domain.value_objects.money_mxn import MoneyMXN


class CalculateFinancingPlan:
    """Use case for calculating financing plans."""

    # Fixed APR: 10% annual
    FIXED_APR = APR(rate=0.10)
    # Minimum down payment: 10% of car price
    MIN_DOWN_PAYMENT_PERCENTAGE = 0.10

    def calculate(
        self,
        car_price: MoneyMXN,
        down_payment: MoneyMXN,
        term_months: LoanTermMonths,
    ) -> FinancingPlan:
        """
        Calculate financing plan.

        Args:
            car_price: Total price of the car
            down_payment: Down payment amount
            term_months: Loan term in months

        Returns:
            Financing plan with payment details

        Raises:
            ValueError: If down payment is less than minimum required
        """
        # Validate minimum down payment (10% of car price)
        min_down_payment = car_price * self.MIN_DOWN_PAYMENT_PERCENTAGE
        if down_payment < min_down_payment:
            raise ValueError(
                f"Down payment must be at least {min_down_payment.amount:,.0f} MXN "
                f"({self.MIN_DOWN_PAYMENT_PERCENTAGE * 100}% of car price)"
            )

        if down_payment >= car_price:
            raise ValueError("Down payment cannot exceed car price")

        # Calculate financed amount
        financed_amount = car_price - down_payment

        # Calculate monthly payment using amortization formula
        # M = P * [r(1+r)^n] / [(1+r)^n - 1]
        # Where:
        # M = monthly payment
        # P = principal (financed amount)
        # r = monthly interest rate
        # n = number of months
        monthly_rate = self.FIXED_APR.monthly_rate
        num_months = term_months.months

        if monthly_rate == 0:
            # If interest rate is 0, simple division
            monthly_payment_amount = financed_amount.amount / num_months
        else:
            # Amortization formula
            numerator = monthly_rate * ((1 + monthly_rate) ** num_months)
            denominator = ((1 + monthly_rate) ** num_months) - 1
            monthly_payment_amount = financed_amount.amount * (numerator / denominator)

        monthly_payment = MoneyMXN(monthly_payment_amount)

        # Calculate total paid and total interest
        total_paid = monthly_payment * num_months
        total_interest = total_paid - financed_amount

        return FinancingPlan(
            term_months=term_months.months,
            financed_amount=round(financed_amount.amount, 2),
            monthly_payment=round(monthly_payment.amount, 2),
            total_paid=round(total_paid.amount, 2),
            total_interest=round(total_interest.amount, 2),
        )

    def calculate_multiple_plans(
        self,
        car_price: MoneyMXN,
        down_payment: MoneyMXN,
        terms: list[int] = None,
    ) -> list[FinancingPlan]:
        """
        Calculate multiple financing plans for different terms.

        Args:
            car_price: Total price of the car
            down_payment: Down payment amount
            terms: List of terms in months (default: [36, 48, 60])

        Returns:
            List of financing plans
        """
        if terms is None:
            terms = [36, 48, 60]

        plans = []
        for term in terms:
            try:
                term_months = LoanTermMonths(months=term)
                plan = self.calculate(car_price, down_payment, term_months)
                plans.append(plan)
            except ValueError:
                # Skip invalid terms
                continue

        return plans

