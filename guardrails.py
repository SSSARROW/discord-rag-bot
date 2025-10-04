# guardrails.py - Anti-hallucination and response validation system
import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResponseQuality(Enum):
    HIGH_CONFIDENCE = "high_confidence"
    MEDIUM_CONFIDENCE = "medium_confidence"
    LOW_CONFIDENCE = "low_confidence"
    UNCERTAIN = "uncertain"
    HALLUCINATION_RISK = "hallucination_risk"

@dataclass
class GuardrailResult:
    """Result of guardrail validation"""
    passed: bool
    quality: ResponseQuality
    confidence_score: float
    warnings: List[str]
    suggestions: List[str]
    source_coverage: float

class HallucinationDetector:
    """Detects potential hallucinations in AI responses"""
    
    def __init__(self):
        # Patterns that often indicate hallucination
        self.hallucination_patterns = [
            r'\b(according to|based on|studies show|research indicates)\b.*(?:but|however|although)',
            r'\b(experts say|scientists believe|studies prove)\b(?!.*\b(?:according to|based on|from the document))\b',
            r'\b(always|never|all|every|none)\b(?!.*\b(?:according to|based on|from the document))\b',
            r'\b(guaranteed|certain|definitely|absolutely)\b(?!.*\b(?:according to|based on|from the document))\b',
            r'\b(proven|established|confirmed)\b(?!.*\b(?:according to|based on|from the document))\b',
            r'\b(statistics|data shows|figures indicate)\b(?!.*\b(?:according to|based on|from the document))\b',
            r'\b(typically|usually|generally|commonly)\b(?!.*\b(?:according to|based on|from the document))\b',
        ]
        
        # Confidence indicators
        self.confidence_indicators = {
            'high': [
                r'\b(according to|based on|from the document|as stated in)\b',
                r'\b(the document|the source|the text)\b',
                r'\b(clearly|explicitly|specifically)\b',
                r'\b(mentioned|described|outlined)\b'
            ],
            'medium': [
                r'\b(likely|probably|suggests|indicates)\b',
                r'\b(appears|seems|suggests)\b',
                r'\b(may|might|could)\b'
            ],
            'low': [
                r'\b(possibly|perhaps|maybe|potentially)\b',
                r'\b(uncertain|unclear|unknown)\b',
                r'\b(not specified|not mentioned|not clear)\b'
            ]
        }
    
    def detect_hallucination_risk(self, response: str, context: str) -> Tuple[bool, List[str]]:
        """Detect potential hallucination patterns in response"""
        warnings = []
        
        # Check for hallucination patterns
        for pattern in self.hallucination_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                warnings.append(f"Potential hallucination pattern detected: {pattern}")
        
        # Check if response makes claims not supported by context
        if not self._is_response_grounded_in_context(response, context):
            warnings.append("Response may contain information not found in provided context")
        
        # Check for overly confident language without source attribution
        if self._has_overconfident_language(response):
            warnings.append("Response uses overly confident language without proper source attribution")
        
        return len(warnings) > 0, warnings
    
    def _is_response_grounded_in_context(self, response: str, context: str) -> bool:
        """Check if response is grounded in the provided context"""
        if not context or not response:
            return False
        
        # Simple check: look for key terms from context in response
        context_words = set(re.findall(r'\b\w+\b', context.lower()))
        response_words = set(re.findall(r'\b\w+\b', response.lower()))
        
        # Check for overlap (excluding common words)
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must'}
        context_words -= common_words
        response_words -= common_words
        
        overlap = len(context_words.intersection(response_words))
        total_unique_words = len(response_words)
        
        if total_unique_words == 0:
            return False
        
        # If less than 30% of response words are from context, it might be hallucinated
        return overlap / total_unique_words >= 0.3
    
    def _has_overconfident_language(self, response: str) -> bool:
        """Check for overly confident language without proper attribution"""
        overconfident_patterns = [
            r'\b(always|never|all|every|none)\b(?!.*\b(?:according to|based on|from the document))\b',
            r'\b(guaranteed|certain|definitely|absolutely)\b(?!.*\b(?:according to|based on|from the document))\b',
            r'\b(proven|established|confirmed)\b(?!.*\b(?:according to|based on|from the document))\b'
        ]
        
        for pattern in overconfident_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return True
        return False

class ResponseValidator:
    """Validates response quality and appropriateness"""
    
    def __init__(self):
        self.inappropriate_patterns = [
            r'\b(illegal|unlawful|harmful|dangerous)\b',
            r'\b(hate|discrimination|prejudice)\b',
            r'\b(violence|threat|harm)\b',
            r'\b(medical advice|legal advice|financial advice)\b(?!.*\b(?:consult|professional|expert)\b)',
        ]
        
        self.off_topic_indicators = [
            r'\b(personal|private|confidential)\b',
            r'\b(opinion|belief|feeling)\b(?!.*\b(?:according to|based on)\b)',
            r'\b(you should|you must|you need to)\b',
        ]
    
    def validate_response(self, response: str, question: str, context: str) -> GuardrailResult:
        """Validate response for quality, appropriateness, and accuracy"""
        warnings = []
        suggestions = []
        
        # Check for inappropriate content
        if self._contains_inappropriate_content(response):
            warnings.append("Response may contain inappropriate content")
            suggestions.append("Reframe response to be more professional and appropriate")
        
        # Check for off-topic responses
        if self._is_off_topic(response, question):
            warnings.append("Response may be off-topic")
            suggestions.append("Focus on answering the specific question asked")
        
        # Check response length
        if len(response) > 2000:
            warnings.append("Response is very long")
            suggestions.append("Consider breaking into smaller, more digestible parts")
        elif len(response) < 50:
            warnings.append("Response is very short")
            suggestions.append("Provide more detailed information if available")
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(response, context)
        
        # Determine quality level
        quality = self._determine_quality(confidence_score, warnings)
        
        # Calculate source coverage
        source_coverage = self._calculate_source_coverage(response, context)
        
        return GuardrailResult(
            passed=len(warnings) == 0,
            quality=quality,
            confidence_score=confidence_score,
            warnings=warnings,
            suggestions=suggestions,
            source_coverage=source_coverage
        )
    
    def _contains_inappropriate_content(self, response: str) -> bool:
        """Check for inappropriate content patterns"""
        for pattern in self.inappropriate_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return True
        return False
    
    def _is_off_topic(self, response: str, question: str) -> bool:
        """Check if response is off-topic"""
        for pattern in self.off_topic_indicators:
            if re.search(pattern, response, re.IGNORECASE):
                return True
        
        # Check if response addresses the question
        question_words = set(re.findall(r'\b\w+\b', question.lower()))
        response_words = set(re.findall(r'\b\w+\b', response.lower()))
        
        # Simple overlap check
        overlap = len(question_words.intersection(response_words))
        return overlap < 2  # Very low overlap might indicate off-topic response
    
    def _calculate_confidence_score(self, response: str, context: str) -> float:
        """Calculate confidence score based on various factors"""
        score = 0.5  # Base score
        
        # Check for source attribution
        if re.search(r'\b(according to|based on|from the document|as stated in)\b', response, re.IGNORECASE):
            score += 0.3
        
        # Check for uncertainty markers
        uncertainty_markers = ['may', 'might', 'could', 'possibly', 'perhaps', 'maybe']
        uncertainty_count = sum(1 for marker in uncertainty_markers if marker in response.lower())
        score -= uncertainty_count * 0.1
        
        # Check for confidence markers
        confidence_markers = ['clearly', 'explicitly', 'specifically', 'definitely']
        confidence_count = sum(1 for marker in confidence_markers if marker in response.lower())
        score += confidence_count * 0.1
        
        # Check context grounding
        if self._is_well_grounded(response, context):
            score += 0.2
        
        return max(0.0, min(1.0, score))
    
    def _is_well_grounded(self, response: str, context: str) -> bool:
        """Check if response is well-grounded in context"""
        if not context or not response:
            return False
        
        # Look for specific references to context
        context_indicators = ['document', 'source', 'text', 'according to', 'based on']
        return any(indicator in response.lower() for indicator in context_indicators)
    
    def _calculate_source_coverage(self, response: str, context: str) -> float:
        """Calculate how well the response covers the available context"""
        if not context or not response:
            return 0.0
        
        # Simple word overlap calculation
        context_words = set(re.findall(r'\b\w+\b', context.lower()))
        response_words = set(re.findall(r'\b\w+\b', response.lower()))
        
        if not context_words:
            return 0.0
        
        overlap = len(context_words.intersection(response_words))
        return min(1.0, overlap / len(context_words))

class GuardrailSystem:
    """Main guardrail system that coordinates all validation"""
    
    def __init__(self):
        self.hallucination_detector = HallucinationDetector()
        self.response_validator = ResponseValidator()
    
    def validate_response(self, response: str, question: str, context: str, source_documents: List[str] = None) -> GuardrailResult:
        """Main validation function that runs all guardrails"""
        logger.info(f"Validating response for question: {question[:100]}...")
        
        # Combine all context sources
        full_context = context
        if source_documents:
            full_context += "\n\n".join(source_documents)
        
        # Run hallucination detection
        has_hallucination_risk, hallucination_warnings = self.hallucination_detector.detect_hallucination_risk(response, full_context)
        
        # Run response validation
        validation_result = self.response_validator.validate_response(response, question, full_context)
        
        # Combine results
        all_warnings = validation_result.warnings + hallucination_warnings
        all_suggestions = validation_result.suggestions.copy()
        
        if has_hallucination_risk:
            all_suggestions.append("Add source attribution to claims")
            all_suggestions.append("Use more cautious language when uncertain")
        
        # Adjust quality based on hallucination risk
        quality = validation_result.quality
        if has_hallucination_risk:
            if quality == ResponseQuality.HIGH_CONFIDENCE:
                quality = ResponseQuality.MEDIUM_CONFIDENCE
            elif quality == ResponseQuality.MEDIUM_CONFIDENCE:
                quality = ResponseQuality.LOW_CONFIDENCE
            else:
                quality = ResponseQuality.HALLUCINATION_RISK
        
        return GuardrailResult(
            passed=len(all_warnings) == 0,
            quality=quality,
            confidence_score=validation_result.confidence_score,
            warnings=all_warnings,
            suggestions=all_suggestions,
            source_coverage=validation_result.source_coverage
        )
    
    def get_enhanced_prompt_instructions(self) -> str:
        """Get enhanced prompt instructions to prevent hallucinations"""
        return """
CRITICAL INSTRUCTIONS TO PREVENT HALLUCINATIONS:
- ONLY use information explicitly stated in the provided context
- If information is not in the context, say "I don't have that information in the provided documents"
- Use phrases like "According to the document" or "Based on the provided context"
- Avoid making claims about things not mentioned in the context
- If uncertain, use phrases like "The document suggests" or "It appears that"
- Never make up statistics, dates, or specific details not in the context
- If asked about something not in the documents, politely explain you don't have that information
- Always ground your responses in the provided source material
- Use caution when making generalizations or broad statements
"""

def create_safe_response(response: str, guardrail_result: GuardrailResult) -> str:
    """Create a safe response based on guardrail validation"""
    if guardrail_result.passed:
        return response
    
    # Add disclaimers based on quality level
    if guardrail_result.quality == ResponseQuality.HALLUCINATION_RISK:
        return f" **Please note:** {response}\n\n*This response may contain information not directly from the provided documents. Please verify important details.*"
    
    elif guardrail_result.quality == ResponseQuality.LOW_CONFIDENCE:
        return f" **Please note:** {response}\n\n*This response has low confidence. Please verify important details.*"
    
    elif guardrail_result.quality == ResponseQuality.UNCERTAIN:
        return f" **Please note:** {response}\n\n*I'm not entirely certain about this information. Please verify if important.*"
    
    return response
