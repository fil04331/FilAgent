"""
Tool Parser Component - Structured Output Parsing

Replaces regex-based tool call parsing with structured output handling.
Supports both:
1. Native LLM structured outputs (tool_calls attribute)
2. Fallback JSON parsing from text (for models without native support)

Key Principles:
1. Single Responsibility: ONLY parses tool calls
2. No Regex: Uses JSON parsing and Pydantic validation
3. Graceful fallback: Handles both structured and text outputs
4. Type Safety: Pydantic V2 for all outputs
"""

import json
import re
from typing import List, Optional, Any

from pydantic import BaseModel, ValidationError

from runtime.tool_executor import ToolCall


class ParsingResult(BaseModel):
    """Result of tool call parsing"""

    tool_calls: List[ToolCall]
    parsing_method: str  # 'native_structured', 'json_extraction', 'none'
    raw_text: Optional[str] = None
    parsing_errors: List[str] = []


class ToolParser:
    """
    Parses tool calls from LLM outputs.

    This component handles the complexity of extracting structured tool calls
    from various LLM output formats, with graceful fallback to JSON extraction
    when native structured output is not available.
    """

    def __init__(self):
        """Initialize parser (stateless)"""

    def parse(
        self,
        generation_result: Any,
        response_text: str,
    ) -> ParsingResult:
        """
        Parse tool calls from generation result.

        Tries multiple methods in order:
        1. Native structured output (generation_result.tool_calls)
        2. JSON extraction from text (looking for <tool_call> tags)
        3. Direct JSON in text (no tags)

        Args:
            generation_result: Model generation result object
            response_text: Text response from model

        Returns:
            ParsingResult with extracted tool calls
        """
        # Method 1: Native structured output
        tool_calls_attr = getattr(generation_result, "tool_calls", None)
        if isinstance(tool_calls_attr, list) and tool_calls_attr:
            try:
                validated_calls = self._validate_tool_calls(tool_calls_attr)
                return ParsingResult(
                    tool_calls=validated_calls,
                    parsing_method="native_structured",
                    raw_text=response_text,
                )
            except ValidationError as e:
                # Fall through to next method
                parsing_errors = [f"Native structured validation failed: {str(e)}"]
        else:
            parsing_errors = []

        # Method 2: JSON extraction from <tool_call> tags
        if "<tool_call>" in response_text:
            try:
                extracted_calls = self._extract_from_tags(response_text)
                if extracted_calls:
                    return ParsingResult(
                        tool_calls=extracted_calls,
                        parsing_method="json_extraction",
                        raw_text=response_text,
                        parsing_errors=parsing_errors,
                    )
            except (json.JSONDecodeError, ValidationError) as e:
                parsing_errors.append(f"JSON extraction failed: {str(e)}")

        # Method 3: Direct JSON parsing (last resort)
        try:
            direct_call = self._extract_direct_json(response_text)
            if direct_call:
                return ParsingResult(
                    tool_calls=[direct_call],
                    parsing_method="direct_json",
                    raw_text=response_text,
                    parsing_errors=parsing_errors,
                )
        except (json.JSONDecodeError, ValidationError) as e:
            parsing_errors.append(f"Direct JSON parsing failed: {str(e)}")

        # No tool calls found
        return ParsingResult(
            tool_calls=[],
            parsing_method="none",
            raw_text=response_text,
            parsing_errors=parsing_errors,
        )

    def _validate_tool_calls(self, raw_calls: List[dict]) -> List[ToolCall]:
        """
        Validate and convert raw tool calls to ToolCall objects.

        Args:
            raw_calls: List of raw dictionaries from LLM

        Returns:
            List of validated ToolCall objects
        """
        validated = []
        for call_dict in raw_calls:
            # Ensure required fields exist
            if "tool" in call_dict:
                tool_call = ToolCall(
                    tool=call_dict["tool"],
                    arguments=call_dict.get("arguments", {}),
                )
                validated.append(tool_call)

        return validated

    def _extract_from_tags(self, text: str) -> List[ToolCall]:
        """
        Extract tool calls from <tool_call> XML-like tags.

        Format:
        <tool_call>
        {"tool": "name", "arguments": {...}}
        </tool_call>

        Args:
            text: Text containing tool call tags

        Returns:
            List of ToolCall objects
        """
        # Use regex only to locate JSON blocks, not to parse content
        pattern = r"<tool_call>(.*?)</tool_call>"
        matches = re.findall(pattern, text, re.DOTALL)

        tool_calls = []
        for match in matches:
            try:
                # Parse JSON from extracted content
                json_content = match.strip()
                tool_dict = json.loads(json_content)

                # Validate structure
                if "tool" in tool_dict and "arguments" in tool_dict:
                    tool_call = ToolCall(
                        tool=tool_dict["tool"],
                        arguments=tool_dict["arguments"],
                    )
                    tool_calls.append(tool_call)
            except (json.JSONDecodeError, ValidationError):
                # Skip malformed tool calls
                continue

        return tool_calls

    def _extract_direct_json(self, text: str) -> Optional[ToolCall]:
        """
        Try to parse entire text as JSON tool call.

        This is a last-resort fallback for models that output raw JSON.

        Args:
            text: Text that might be JSON

        Returns:
            ToolCall if valid JSON found, None otherwise
        """
        # Clean text (remove markdown code blocks if present)
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            tool_dict = json.loads(cleaned)
            if "tool" in tool_dict and "arguments" in tool_dict:
                return ToolCall(
                    tool=tool_dict["tool"],
                    arguments=tool_dict["arguments"],
                )
        except (json.JSONDecodeError, ValidationError):
            pass

        return None

    def has_tool_calls(self, text: str) -> bool:
        """
        Quick check if text contains tool call markers.

        Args:
            text: Text to check

        Returns:
            True if tool call markers found
        """
        return "<tool_call>" in text or (text.strip().startswith("{") and '"tool"' in text)
