"""
Outil d'analyse de documents pour PME québécoises
Supporte: PDF, Excel, Word avec calculs TPS/TVQ
"""

import pandas as pd
from typing import Dict, Any, Optional
import PyPDF2
import docx
import re
import logging
from pathlib import Path
from .base import BaseTool, ToolResult, ToolStatus

# Setup standard Python logger for testing compatibility
logger = logging.getLogger(__name__)

# Import custom logger for compliance (Loi 25 - audit trail)
try:
    from runtime.middleware.logging import get_logger
except ImportError:
    get_logger = None


class DocumentAnalyzerPME(BaseTool):
    """Analyseur intelligent de documents PME avec conformité Loi 25"""

    def __init__(self):
        super().__init__(
            name="document_analyzer_pme",
            description="Analyse de documents PME avec calculs TPS/TVQ (Québec)",
        )
        self.tps_rate = 0.05  # 5%
        self.tvq_rate = 0.09975  # 9.975%

        # Initialize logger for compliance (audit trail)
        try:
            self.logger = get_logger() if get_logger else None
        except Exception:
            self.logger = None

    def _redact_file_path(self, file_path: str) -> str:
        """
        Redact PII from file paths for compliance (Loi 25, PIPEDA)

        Removes:
        - Usernames (e.g., /Users/john.doe/ → /Users/[REDACTED]/)
        - Sensitive folder names (confidential, secret, private, etc.)
        - Email addresses in filenames
        - Phone numbers in filenames
        - SSN patterns in filenames

        Args:
            file_path: Original file path potentially containing PII

        Returns:
            Redacted file path safe for logging
        """
        path = Path(file_path)

        # Sensitive folder/file name patterns
        sensitive_patterns = [
            "confidential",
            "secret",
            "private",
            "personal",
            "prive",
            "confidentiel",
        ]

        # Redact parts in path
        parts = list(path.parts)
        for i, part in enumerate(parts):
            # Redact username in path (e.g., /Users/john.doe/)
            if i > 0 and parts[i - 1].lower() in ["users", "home"]:
                parts[i] = "[REDACTED]"
            # Redact sensitive folder names
            elif any(sensitive in part.lower() for sensitive in sensitive_patterns):
                parts[i] = "[REDACTED]"

        # Redact filename if it contains PII patterns
        filename = path.name

        # Email pattern
        filename = re.sub(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL_REDACTED]", filename
        )

        # Phone pattern (514-555-1234, 5145551234)
        filename = re.sub(r"\d{3}[-.\s]?\d{3}[-.\s]?\d{4}", "[PHONE_REDACTED]", filename)

        # SSN pattern (123-45-6789)
        filename = re.sub(r"\d{3}-\d{2}-\d{4}", "[SSN_REDACTED]", filename)

        # Sensitive words in filename (with underscores/hyphens)
        for sensitive in sensitive_patterns:
            # Match word with boundaries OR with underscore/hyphen
            filename = re.sub(
                rf"(?:^|[^a-zA-Z]){sensitive}(?:[^a-zA-Z]|$)",
                "[REDACTED]",
                filename,
                flags=re.IGNORECASE,
            )

        # Reconstruct path
        parts[-1] = filename
        return str(Path(*parts))

    def _redact_pii_from_error(self, error_message: str) -> str:
        """
        Redact PII from error messages for compliance

        Args:
            error_message: Original error message

        Returns:
            Redacted error message safe for logging
        """
        # Email redaction
        error_message = re.sub(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL_REDACTED]", error_message
        )

        # Phone redaction
        error_message = re.sub(r"\d{3}[-.\s]?\d{3}[-.\s]?\d{4}", "[PHONE_REDACTED]", error_message)

        # SSN redaction
        error_message = re.sub(r"\d{3}-\d{2}-\d{4}", "[SSN_REDACTED]", error_message)

        # Path redaction (any absolute path)
        error_message = re.sub(r"/(?:Users|home)/[^/\s]+", "/[REDACTED]", error_message)

        return error_message

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """
        Execute l'analyse de document

        Args:
            arguments: Dict avec 'file_path' et optionnellement 'analysis_type'

        Returns:
            ToolResult avec les données extraites
        """
        # Validate arguments
        is_valid, error = self.validate_arguments(arguments)
        if not is_valid:
            return ToolResult(status=ToolStatus.ERROR, output="", error=error)

        file_path = arguments["file_path"]
        analysis_type = arguments.get("analysis_type", "invoice")

        try:
            if analysis_type == "invoice":
                result = self.analyze_invoice(file_path)
            else:
                result = self._extract_data(file_path)

            return ToolResult(status=ToolStatus.SUCCESS, output=str(result), metadata=result)
        except FileNotFoundError:
            # Redact PII from file path for compliance (Loi 25, PIPEDA)
            safe_path = self._redact_file_path(file_path)

            # Log at ERROR level for audit trail (Loi 25 Article 63.2)
            # Standard Python logging for testing compatibility
            logger.error(
                f"File not found error: {safe_path}",
                extra={
                    "actor": "document_analyzer_pme",
                    "event": "file.not_found",
                    "safe_path": safe_path,
                    "analysis_type": analysis_type,
                },
            )

            # Custom middleware logger for compliance
            if self.logger:
                self.logger.log_event(
                    actor="document_analyzer_pme",
                    event="file.not_found",
                    level="ERROR",
                    metadata={
                        "safe_path": safe_path,
                        "analysis_type": analysis_type,
                        "error": "FileNotFoundError",
                    },
                )

            return ToolResult(
                status=ToolStatus.ERROR, output="", error=f"File not found: {safe_path}"
            )
        except Exception as e:
            # Redact PII from error message
            safe_error_msg = self._redact_pii_from_error(str(e))
            safe_file_path = self._redact_file_path(file_path)

            # Log at ERROR level for audit trail (Loi 25 Article 63.2)
            # Standard Python logging for testing compatibility
            logger.error(
                f"Analysis error: {safe_error_msg}",
                extra={
                    "actor": "document_analyzer_pme",
                    "event": "analysis.error",
                    "safe_path": safe_file_path,
                    "error_type": type(e).__name__,
                    "analysis_type": analysis_type,
                },
            )

            # Custom middleware logger for compliance
            if self.logger:
                self.logger.log_event(
                    actor="document_analyzer_pme",
                    event="analysis.error",
                    level="ERROR",
                    metadata={
                        "safe_path": safe_file_path,
                        "error_type": type(e).__name__,
                        "error_message": safe_error_msg,
                        "analysis_type": analysis_type,
                    },
                )

            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Error analyzing document: {safe_error_msg}",
            )

    def validate_arguments(self, arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate arguments"""
        if "file_path" not in arguments:
            return False, "Missing required argument: file_path"

        file_path = arguments["file_path"]
        if not isinstance(file_path, str):
            return False, "file_path must be a string"

        # Check file extension
        valid_extensions = [".pdf", ".xlsx", ".xls", ".docx", ".doc"]
        if not any(file_path.lower().endswith(ext) for ext in valid_extensions):
            return False, f"Unsupported file type. Supported: {', '.join(valid_extensions)}"

        return True, None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        """Return parameter schema"""
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the document to analyze"},
                "analysis_type": {
                    "type": "string",
                    "enum": ["invoice", "extract"],
                    "description": "Type of analysis to perform (default: invoice)",
                },
            },
            "required": ["file_path"],
        }

    def analyze_invoice(self, file_path: str) -> Dict[str, Any]:
        """Analyse facture avec calculs taxes québécoises"""
        # Extraction données
        data = self._extract_data(file_path)

        # Calculs taxes
        subtotal = data.get("subtotal", 0)
        tps = subtotal * self.tps_rate
        tvq = subtotal * self.tvq_rate
        total = subtotal + tps + tvq

        return {
            "subtotal": subtotal,
            "tps": round(tps, 2),
            "tvq": round(tvq, 2),
            "total": round(total, 2),
            "tps_number": self._extract_tax_number(data, "TPS"),
            "tvq_number": self._extract_tax_number(data, "TVQ"),
            "pii_redacted": True,  # Conformité Loi 25
        }

    def _extract_data(self, file_path: str) -> Dict:
        """Extraction sécurisée avec redaction PII"""
        # Check file exists
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Logique extraction selon type fichier
        if file_path.lower().endswith(".pdf"):
            return self._extract_pdf(file_path)
        elif file_path.lower().endswith((".xlsx", ".xls")):
            return self._extract_excel(file_path)
        elif file_path.lower().endswith((".docx", ".doc")):
            return self._extract_word(file_path)
        return {}

    def _extract_pdf(self, file_path: str) -> Dict:
        """Extract data from PDF file"""
        try:
            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)

                # Extract text from all pages
                text = ""
                for page in reader.pages:
                    text += page.extract_text()

                # Extract monetary values
                amounts = re.findall(r"\$?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)", text)
                subtotal = 0
                if amounts:
                    # Try to find subtotal (usually largest or last before total)
                    try:
                        subtotal = float(amounts[-1].replace(",", ""))
                    except (ValueError, IndexError):
                        pass

                return {"text": text, "subtotal": subtotal, "raw_amounts": amounts}
        except Exception as e:
            raise ValueError(f"Error reading PDF: {str(e)}")

    def _extract_excel(self, file_path: str) -> Dict:  # noqa: C901
        """Extract data from Excel file"""
        try:
            df = pd.read_excel(file_path)

            # Look for common invoice columns
            subtotal = 0

            # Try to find subtotal in various ways
            for col in df.columns:
                col_lower = str(col).lower()
                if "subtotal" in col_lower or "sous-total" in col_lower:
                    values = df[col].dropna()
                    if not values.empty:
                        try:
                            subtotal = float(values.iloc[-1])
                        except (ValueError, TypeError):
                            pass
                    break

            # If no subtotal column, try to find numeric values
            if subtotal == 0:
                numeric_cols = df.select_dtypes(include=["float64", "int64"]).columns
                if len(numeric_cols) > 0:
                    values = df[numeric_cols[0]].dropna()
                    if not values.empty:
                        try:
                            subtotal = float(values.iloc[-1])
                        except (ValueError, TypeError):
                            pass

            return {
                "data": df.to_dict(),
                "subtotal": subtotal,
                "columns": list(df.columns),
                "rows": len(df),
            }
        except Exception as e:
            raise ValueError(f"Error reading Excel: {str(e)}")

    def _extract_word(self, file_path: str) -> Dict:
        """Extract data from Word document"""
        try:
            doc = docx.Document(file_path)

            # Extract all text
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])

            # Extract monetary values
            amounts = re.findall(r"\$?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)", text)
            subtotal = 0
            if amounts:
                try:
                    subtotal = float(amounts[-1].replace(",", ""))
                except (ValueError, IndexError):
                    pass

            return {
                "text": text,
                "subtotal": subtotal,
                "paragraphs": len(doc.paragraphs),
                "raw_amounts": amounts,
            }
        except Exception as e:
            raise ValueError(f"Error reading Word document: {str(e)}")

    def _extract_tax_number(self, data: Dict, tax_type: str) -> str:
        """Extraction numéros taxes (TPS/TVQ)"""
        patterns = {"TPS": r"TPS[:\s]*(\d{9}RT\d{4})", "TVQ": r"TVQ[:\s]*(\d{10}TQ\d{4})"}

        # Search in text if available
        text = data.get("text", "")
        if text and tax_type in patterns:
            match = re.search(patterns[tax_type], text)
            if match:
                return "REDACTED"  # For security/compliance

        return "REDACTED"  # Par défaut pour sécurité
