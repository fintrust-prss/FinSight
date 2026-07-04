from typing import Dict, Any, List
from datetime import date, datetime, timezone

class ULISimulator:
    """
    Simulates Unified Lending Interface (ULI) standardized data fetches.
    Returns canned, structurally valid schema payloads based on MSME profiles.
    """
    
    @staticmethod
    def fetch_standardized_profile(msme_id: str) -> Dict[str, Any]:
        """
        Returns a standardized ULI schema payload for the given MSME.
        """
        return {
            "uli_reference_id": f"uli_ref_{msme_id}_01",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "uli.v1.0.0",
            "consent_reference": f"uli_consent_token_for_{msme_id}",
            "msme_profile": {
                "msme_id": msme_id,
                "regulatory_filings": {
                    "udyam_registration": {
                        "status": "VERIFIED",
                        "date_of_registration": "2021-04-12"
                    },
                    "gst_status": {
                        "registration_state": "Maharashtra",
                        "active_status": True,
                        "filing_frequency": "MONTHLY"
                    }
                },
                "financial_aggregates_last_12m": {
                    "estimated_gst_turnover_inr": 5400000.0,
                    "avg_monthly_bank_balance_inr": 230000.0,
                    "upi_transaction_count": 1420,
                    "utility_bill_payment_on_time_ratio": 0.95
                }
            }
        }
