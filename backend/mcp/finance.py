from typing import Dict, Any, Optional

class FinanceCalculator:
    """Financial calculations for CRE deals with trail strings"""

    def calculate_metrics(
        self,
        noi: Optional[float] = None,
        debt_service: Optional[float] = None,
        loan_amount: Optional[float] = None,
        property_value: Optional[float] = None,
        total_cost: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Calculate financial metrics with trail strings"""

        results = {}

        # DSCR (Debt Service Coverage Ratio)
        if noi is not None and debt_service is not None and debt_service > 0:
            dscr = noi / debt_service
            results['dscr'] = {
                'value': round(dscr, 2),
                'trail': f"DSCR = {self._format_number(noi)} / {self._format_number(debt_service)} = {dscr:.2f}x"
            }

        # LTV (Loan to Value)
        if loan_amount is not None and property_value is not None and property_value > 0:
            ltv = (loan_amount / property_value) * 100
            results['ltv'] = {
                'value': round(ltv, 1),
                'trail': f"LTV = {self._format_number(loan_amount)} / {self._format_number(property_value)} = {ltv:.1f}%"
            }

        # LTC (Loan to Cost)
        if loan_amount is not None and total_cost is not None and total_cost > 0:
            ltc = (loan_amount / total_cost) * 100
            results['ltc'] = {
                'value': round(ltc, 1),
                'trail': f"LTC = {self._format_number(loan_amount)} / {self._format_number(total_cost)} = {ltc:.1f}%"
            }

        # Cap Rate
        if noi is not None and property_value is not None and property_value > 0:
            cap_rate = (noi / property_value) * 100
            results['cap_rate'] = {
                'value': round(cap_rate, 2),
                'trail': f"Cap Rate = {self._format_number(noi)} / {self._format_number(property_value)} = {cap_rate:.2f}%"
            }

        # Debt Yield
        if noi is not None and loan_amount is not None and loan_amount > 0:
            debt_yield = (noi / loan_amount) * 100
            results['debt_yield'] = {
                'value': round(debt_yield, 2),
                'trail': f"Debt Yield = {self._format_number(noi)} / {self._format_number(loan_amount)} = {debt_yield:.2f}%"
            }

        return results

    def _format_number(self, value: float) -> str:
        """Format number with commas"""
        return f"{value:,.0f}"

# Global instance
finance_calculator = FinanceCalculator()

async def calculate_metrics(**kwargs) -> Dict[str, Any]:
    return finance_calculator.calculate_metrics(**kwargs)
