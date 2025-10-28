"""
PII (Personally Identifiable Information) detection and masking

Detects and masks sensitive information in text to comply with privacy regulations.
"""

import re
from typing import List, Optional


class PIIDetector:
    """Detects PII in text"""
    
    def __init__(self):
        # Patterns for different PII types
        self.patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
            "ssn": r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
            "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            "ip_address": r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        }
    
    def contains_pii(self, text: str, pii_types: Optional[List[str]] = None) -> bool:
        """
        Check if text contains PII
        
        Args:
            text: Text to check
            pii_types: List of PII types to check (default: all)
        
        Returns:
            True if PII is detected
        """
        if pii_types is None:
            pii_types = list(self.patterns.keys())
        
        for pii_type in pii_types:
            if pii_type in self.patterns:
                if re.search(self.patterns[pii_type], text):
                    return True
        
        return False


class PIIMasker:
    """Masks PII in text"""
    
    def __init__(self, replacement: str = "[REDACTED]"):
        self.replacement = replacement
        self.detector = PIIDetector()
    
    def mask_text(self, text: str, pii_types: Optional[List[str]] = None) -> str:
        """
        Mask PII in text
        
        Args:
            text: Text to mask
            pii_types: List of PII types to mask (default: all)
        
        Returns:
            Text with PII masked
        """
        if pii_types is None:
            pii_types = list(self.detector.patterns.keys())
        
        masked_text = text
        
        for pii_type in pii_types:
            if pii_type in self.detector.patterns:
                pattern = self.detector.patterns[pii_type]
                masked_text = re.sub(pattern, self.replacement, masked_text)
        
        return masked_text
