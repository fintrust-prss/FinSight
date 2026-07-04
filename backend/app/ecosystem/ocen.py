from typing import Dict, Any
from datetime import datetime, timezone
import uuid

class OCENSimulator:
    """
    Simulates Open Credit Enablement Network (OCEN) signal exchange stub
    between LSP (Loan Service Provider) and Lender.
    """
    
    @staticmethod
    def generate_loan_offer_signal(msme_id: str, score: float) -> Dict[str, Any]:
        """
        Simulates an OCEN LSP agent receiving/sending a signal about credit terms.
        Depending on the score, it creates an eligibility offer.
        """
        is_eligible = score >= 50.0
        offer_id = f"ocen_offer_{uuid.uuid4().hex[:8]}" if is_eligible else None
        
        return {
            "ocen_tx_id": f"ocen_tx_{uuid.uuid4().hex[:12]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lsp_identifier": "idbi_lsp_fintech_stub",
            "msme_id": msme_id,
            "credit_score_evaluated": score,
            "eligibility_status": "APPROVED" if is_eligible else "REJECTED",
            "signal_payload": {
                "offer_id": offer_id,
                "max_principal_amount": 1000000.0 if score >= 80 else (500000.0 if score >= 60 else 200000.0) if is_eligible else 0.0,
                "interest_rate_apr": 11.5 if score >= 80 else 13.0 if score >= 60 else 14.5,
                "tenure_months": 24 if is_eligible else 0,
                "repayment_frequency": "MONTHLY"
            } if is_eligible else None,
            "exchange_status": "COMPLETED" if is_eligible else "TERMINATED",
            "message": "Eligible loan offer signals synced over OCEN protocol." if is_eligible else "Credit score below threshold for automated OCEN offer signaling."
        }
