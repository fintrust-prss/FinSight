import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import json

class AASimulator:
    """
    Simulates Account Aggregator (AA) Consent Flow Handshake.
    In production, this would make calls to Sahamati / AA API endpoints.
    """
    
    @staticmethod
    def initiate_consent_request(
        msme_id: str,
        data_types: List[str],
        purpose: str,
        valid_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Simulates initiating a consent request with the AA.
        Returns a mock consent request context, including a redirect URL.
        """
        consent_handle = f"consent_handle_{uuid.uuid4().hex[:12]}"
        expiry = datetime.now(timezone.utc) + timedelta(hours=valid_hours)
        
        return {
            "consent_handle": consent_handle,
            "status": "PENDING",
            "msme_id": msme_id,
            "data_types": data_types,
            "purpose": purpose,
            "expiry": expiry.isoformat(),
            "redirect_url": f"/ecosystem/aa/approve?handle={consent_handle}",
            "msg": "Consent request initiated successfully on Sahamati sandbox."
        }

    @staticmethod
    def fetch_consent_status(consent_id: str, current_status: str, expiry: datetime) -> str:
        """
        Checks and simulates AA status transitions (e.g., handling expiry).
        """
        now = datetime.now(timezone.utc)
        if expiry.replace(tzinfo=timezone.utc) < now:
            return "EXPIRED"
        return current_status
