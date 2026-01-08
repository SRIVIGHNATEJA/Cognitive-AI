"""
LLM output schemas and validation for structured generation.

Defines strict JSON schemas and constraints for LLM outputs to ensure
consistent, valid, and on-topic content generation.
"""

import re
from typing import List, Dict, Any, Tuple
from jsonschema import validate, ValidationError

from app.logging_config import get_logger

logger = get_logger(__name__)


# Roadmap JSON Schema
ROADMAP_SCHEMA = {
    "type": "object",
    "properties": {
        "modules": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "topic_name": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 200
                    },
                    "estimated_hours": {
                        "type": "number",
                        "minimum": 0.1,
                        "maximum": 100
                    },
                    "prerequisites": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "order": {
                        "type": "integer",
                        "minimum": 1
                    }
                },
                "required": ["topic_name", "estimated_hours", "order"],
                "additionalProperties": False
            }
        }
    },
    "required": ["modules"],
    "additionalProperties": False
}


# Forbidden domains - topics that should never appear in educational content
FORBIDDEN_DOMAINS = [
    # Political
    "politics", "political", "election", "government policy", "partisan",
    "democrat", "republican", "liberal", "conservative",
    
    # Religious/Controversial
    "religion", "religious", "theology", "faith-based", "spiritual beliefs",
    "controversial", "sensitive topic",
    
    # Inappropriate
    "adult content", "explicit", "violence", "weapons", "illegal",
    
    # Off-topic
    "celebrity gossip", "entertainment news", "sports betting",
    "cryptocurrency trading", "get rich quick"
]


def extract_allowed_topics(input_text: str, max_topics: int = 10) -> List[str]:
    """
    Extract main topics from input text to constrain LLM generation.
    
    Uses simple keyword extraction to identify the primary subjects
    that should be covered in the generated roadmap.
    
    Args:
        input_text: The processed input text (syllabus, questions, etc.)
        max_topics: Maximum number of topics to extract
        
    Returns:
        List of extracted topic keywords
    """
    if not input_text:
        return []
    
    # Convert to lowercase for processing
    text_lower = input_text.lower()
    
    # Common educational topic indicators
    topic_patterns = [
        r'(?:course|subject|topic|module|chapter|unit|lesson)[\s:]+([a-z0-9\s]+)',
        r'(?:introduction to|basics of|fundamentals of|advanced)\s+([a-z0-9\s]+)',
        r'week\s+\d+[\s:]+([a-z0-9\s]+)',
        r'(?:learning|studying|understanding)\s+([a-z0-9\s]+)',
    ]
    
    topics = set()
    
    # Extract topics using patterns
    for pattern in topic_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            # Clean up the match
            topic = match.strip()
            # Remove common stop words
            topic = re.sub(r'\b(the|a|an|and|or|but|in|on|at|to|for|of|with)\b', '', topic)
            topic = topic.strip()
            
            if len(topic) > 3 and len(topic) < 50:  # Reasonable topic length
                topics.add(topic)
    
    # Also extract capitalized phrases (likely to be topic names)
    capitalized_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', input_text)
    for phrase in capitalized_phrases:
        if len(phrase) > 3 and len(phrase) < 50:
            topics.add(phrase.lower())
    
    # Convert to list and limit
    topic_list = list(topics)[:max_topics]
    
    logger.info(f"Extracted {len(topic_list)} allowed topics from input")
    logger.debug(f"Allowed topics: {topic_list}")
    
    return topic_list


def check_forbidden_domains(text: str) -> Tuple[bool, List[str]]:
    """
    Check if text contains forbidden domain keywords.
    
    Args:
        text: Text to check for forbidden content
        
    Returns:
        Tuple of (has_forbidden_content, list_of_found_keywords)
    """
    text_lower = text.lower()
    found_keywords = []
    
    for keyword in FORBIDDEN_DOMAINS:
        if keyword in text_lower:
            found_keywords.append(keyword)
    
    has_forbidden = len(found_keywords) > 0
    
    if has_forbidden:
        logger.warning(f"Found forbidden domain keywords: {found_keywords}")
    
    return has_forbidden, found_keywords


def validate_roadmap_output(
    output: Dict[str, Any],
    allowed_topics: List[str] = None,
    strict_topic_check: bool = True
) -> Tuple[bool, str]:
    """
    Validate LLM roadmap output against schema and constraints.
    
    Performs multiple validation checks:
    1. JSON schema validation
    2. Forbidden domain detection
    3. Topic relevance check (if allowed_topics provided)
    
    Args:
        output: The LLM output dictionary to validate
        allowed_topics: Optional list of allowed topics for relevance check
        strict_topic_check: If True, enforce topic relevance strictly
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if output passes all checks
        - error_message: Empty string if valid, error description if invalid
    """
    # 1. Schema validation
    try:
        validate(instance=output, schema=ROADMAP_SCHEMA)
        logger.debug("Roadmap output passed schema validation")
    except ValidationError as e:
        error_msg = f"Schema validation failed: {e.message}"
        logger.error(error_msg)
        return False, error_msg
    
    # 2. Check for forbidden domains in module topics
    modules = output.get("modules", [])
    for module in modules:
        topic_name = module.get("topic_name", "")
        has_forbidden, keywords = check_forbidden_domains(topic_name)
        
        if has_forbidden:
            error_msg = f"Module '{topic_name}' contains forbidden keywords: {keywords}"
            logger.error(error_msg)
            return False, error_msg
    
    # 3. Topic relevance check (if allowed_topics provided)
    if allowed_topics and strict_topic_check:
        # Check if at least some modules relate to allowed topics
        relevant_modules = 0
        
        for module in modules:
            topic_name = module.get("topic_name", "").lower()
            
            # Check if any allowed topic appears in the module name
            for allowed_topic in allowed_topics:
                if allowed_topic.lower() in topic_name or topic_name in allowed_topic.lower():
                    relevant_modules += 1
                    break
        
        # Require at least 50% of modules to be relevant
        relevance_threshold = len(modules) * 0.5
        if relevant_modules < relevance_threshold:
            error_msg = (
                f"Only {relevant_modules}/{len(modules)} modules are relevant to allowed topics. "
                f"Expected at least {int(relevance_threshold)} relevant modules."
            )
            logger.warning(error_msg)
            return False, error_msg
    
    logger.info(f"Roadmap output validation passed ({len(modules)} modules)")
    return True, ""


def get_roadmap_schema_prompt() -> str:
    """
    Get a formatted prompt string describing the roadmap schema.
    
    Returns:
        String describing the expected JSON structure for LLM
    """
    return """
Generate a learning roadmap as a JSON object with the following structure:

{
  "modules": [
    {
      "topic_name": "string (1-200 characters)",
      "estimated_hours": number (0.1-100),
      "prerequisites": ["array of prerequisite topic names"],
      "order": integer (starting from 1)
    }
  ]
}

Requirements:
- Include at least 1 module
- Each module must have topic_name, estimated_hours, and order
- Prerequisites array can be empty if no prerequisites
- Order must be sequential starting from 1
- Topic names should be clear and descriptive
- Estimated hours should be realistic (0.1 to 100 hours)
"""


def get_topic_constraint_prompt(allowed_topics: List[str]) -> str:
    """
    Get a formatted prompt string with topic constraints.
    
    Args:
        allowed_topics: List of topics that should be covered
        
    Returns:
        String describing topic constraints for LLM
    """
    if not allowed_topics:
        return ""
    
    topics_str = ", ".join(allowed_topics[:5])  # Limit to first 5 for brevity
    
    return f"""
Topic Constraints:
- Focus ONLY on topics related to: {topics_str}
- Stay within the subject boundaries of the provided material
- Do NOT include unrelated subjects or off-topic content
"""


def get_forbidden_domains_prompt() -> str:
    """
    Get a formatted prompt string with forbidden domain rules.
    
    Returns:
        String describing forbidden content for LLM
    """
    return """
Forbidden Content:
- Do NOT include political, religious, or controversial topics
- Do NOT include inappropriate or sensitive content
- Do NOT include off-topic entertainment or celebrity content
- Focus strictly on educational and academic subjects
"""
