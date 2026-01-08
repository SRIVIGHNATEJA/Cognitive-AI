"""
Unit tests for LLM output schemas and validation.
Tests schema validation, topic extraction, and constraint checking.
"""

import pytest
from app.services.llm_schemas import (
    ROADMAP_SCHEMA,
    FORBIDDEN_DOMAINS,
    extract_allowed_topics,
    check_forbidden_domains,
    validate_roadmap_output,
    get_roadmap_schema_prompt,
    get_topic_constraint_prompt,
    get_forbidden_domains_prompt
)


class TestRoadmapSchemaValidation:
    """Tests for roadmap schema validation."""
    
    def test_valid_roadmap_passes_validation(self):
        """Test that a valid roadmap passes schema validation."""
        valid_roadmap = {
            "modules": [
                {
                    "topic_name": "Introduction to Python",
                    "estimated_hours": 5.0,
                    "prerequisites": [],
                    "order": 1
                },
                {
                    "topic_name": "Data Structures",
                    "estimated_hours": 8.5,
                    "prerequisites": ["Introduction to Python"],
                    "order": 2
                }
            ]
        }
        
        is_valid, error_msg = validate_roadmap_output(valid_roadmap, strict_topic_check=False)
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_missing_required_field_fails_validation(self):
        """Test that missing required fields fail validation."""
        invalid_roadmap = {
            "modules": [
                {
                    "topic_name": "Introduction to Python",
                    # Missing estimated_hours
                    "prerequisites": [],
                    "order": 1
                }
            ]
        }
        
        is_valid, error_msg = validate_roadmap_output(invalid_roadmap, strict_topic_check=False)
        
        assert is_valid is False
        assert "validation failed" in error_msg.lower()
    
    def test_invalid_data_type_fails_validation(self):
        """Test that invalid data types fail validation."""
        invalid_roadmap = {
            "modules": [
                {
                    "topic_name": "Introduction to Python",
                    "estimated_hours": "five hours",  # Should be number
                    "prerequisites": [],
                    "order": 1
                }
            ]
        }
        
        is_valid, error_msg = validate_roadmap_output(invalid_roadmap, strict_topic_check=False)
        
        assert is_valid is False
        assert "validation failed" in error_msg.lower()
    
    def test_empty_modules_array_fails_validation(self):
        """Test that empty modules array fails validation."""
        invalid_roadmap = {
            "modules": []
        }
        
        is_valid, error_msg = validate_roadmap_output(invalid_roadmap, strict_topic_check=False)
        
        assert is_valid is False
    
    def test_out_of_range_values_fail_validation(self):
        """Test that out-of-range values fail validation."""
        invalid_roadmap = {
            "modules": [
                {
                    "topic_name": "Introduction to Python",
                    "estimated_hours": 150.0,  # Exceeds maximum of 100
                    "prerequisites": [],
                    "order": 1
                }
            ]
        }
        
        is_valid, error_msg = validate_roadmap_output(invalid_roadmap, strict_topic_check=False)
        
        assert is_valid is False


class TestAllowedTopicExtraction:
    """Tests for allowed topic extraction from input text."""
    
    def test_extract_topics_from_syllabus(self):
        """Test extracting topics from syllabus text."""
        syllabus_text = """
        Course: Introduction to Data Science
        
        Week 1: Python Programming Basics
        Week 2: Data Analysis with Pandas
        Week 3: Machine Learning Fundamentals
        
        Topics covered:
        - Statistics
        - Data Visualization
        """
        
        topics = extract_allowed_topics(syllabus_text)
        
        assert len(topics) > 0
        # Should extract some relevant topics
        topics_lower = [t.lower() for t in topics]
        assert any("python" in t or "data" in t or "machine learning" in t for t in topics_lower)
    
    def test_extract_topics_from_question_bank(self):
        """Test extracting topics from question bank text."""
        question_text = """
        Question 1: What is Object-Oriented Programming?
        Question 2: Explain inheritance in Java
        Question 3: Define polymorphism
        """
        
        topics = extract_allowed_topics(question_text)
        
        assert len(topics) > 0
    
    def test_extract_topics_limits_count(self):
        """Test that topic extraction respects max_topics limit."""
        long_text = "\n".join([f"Week {i}: Topic {i}" for i in range(20)])
        
        topics = extract_allowed_topics(long_text, max_topics=5)
        
        assert len(topics) <= 5
    
    def test_extract_topics_from_empty_text(self):
        """Test extracting topics from empty text."""
        topics = extract_allowed_topics("")
        
        assert topics == []
    
    def test_extract_topics_filters_short_words(self):
        """Test that very short words are filtered out."""
        text = "a b c Introduction to Programming"
        
        topics = extract_allowed_topics(text)
        
        # Should not include single letters
        assert not any(len(t) <= 3 for t in topics)


class TestForbiddenDomainDetection:
    """Tests for forbidden domain detection."""
    
    def test_detect_political_content(self):
        """Test detection of political keywords."""
        text = "This course covers politics and government policy"
        
        has_forbidden, keywords = check_forbidden_domains(text)
        
        assert has_forbidden is True
        assert len(keywords) > 0
        assert any("politic" in k for k in keywords)
    
    def test_detect_religious_content(self):
        """Test detection of religious keywords."""
        text = "This module explores religious beliefs and theology"
        
        has_forbidden, keywords = check_forbidden_domains(text)
        
        assert has_forbidden is True
        assert any("relig" in k for k in keywords)
    
    def test_detect_controversial_content(self):
        """Test detection of controversial keywords."""
        text = "This is a controversial topic with sensitive content"
        
        has_forbidden, keywords = check_forbidden_domains(text)
        
        assert has_forbidden is True
    
    def test_clean_educational_content_passes(self):
        """Test that clean educational content passes."""
        text = "Introduction to Computer Science and Programming"
        
        has_forbidden, keywords = check_forbidden_domains(text)
        
        assert has_forbidden is False
        assert len(keywords) == 0
    
    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive."""
        text = "This course covers POLITICS and RELIGION"
        
        has_forbidden, keywords = check_forbidden_domains(text)
        
        assert has_forbidden is True


class TestRoadmapValidationWithConstraints:
    """Tests for roadmap validation with topic and domain constraints."""
    
    def test_roadmap_with_forbidden_domain_fails(self):
        """Test that roadmap with forbidden domains fails validation."""
        roadmap = {
            "modules": [
                {
                    "topic_name": "Introduction to Politics",
                    "estimated_hours": 5.0,
                    "prerequisites": [],
                    "order": 1
                }
            ]
        }
        
        is_valid, error_msg = validate_roadmap_output(roadmap, strict_topic_check=False)
        
        assert is_valid is False
        assert "forbidden" in error_msg.lower()
    
    def test_roadmap_with_allowed_topics_passes(self):
        """Test that roadmap matching allowed topics passes."""
        roadmap = {
            "modules": [
                {
                    "topic_name": "Python Programming Basics",
                    "estimated_hours": 5.0,
                    "prerequisites": [],
                    "order": 1
                },
                {
                    "topic_name": "Advanced Python Concepts",
                    "estimated_hours": 8.0,
                    "prerequisites": ["Python Programming Basics"],
                    "order": 2
                }
            ]
        }
        
        allowed_topics = ["python", "programming"]
        is_valid, error_msg = validate_roadmap_output(
            roadmap,
            allowed_topics=allowed_topics,
            strict_topic_check=True
        )
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_roadmap_with_off_topic_modules_fails(self):
        """Test that roadmap with mostly off-topic modules fails."""
        roadmap = {
            "modules": [
                {
                    "topic_name": "Python Programming",
                    "estimated_hours": 5.0,
                    "prerequisites": [],
                    "order": 1
                },
                {
                    "topic_name": "Cooking Basics",
                    "estimated_hours": 3.0,
                    "prerequisites": [],
                    "order": 2
                },
                {
                    "topic_name": "Gardening Tips",
                    "estimated_hours": 2.0,
                    "prerequisites": [],
                    "order": 3
                }
            ]
        }
        
        allowed_topics = ["python", "programming"]
        is_valid, error_msg = validate_roadmap_output(
            roadmap,
            allowed_topics=allowed_topics,
            strict_topic_check=True
        )
        
        assert is_valid is False
        assert "relevant" in error_msg.lower()
    
    def test_validation_without_topic_check(self):
        """Test that validation works without strict topic checking."""
        roadmap = {
            "modules": [
                {
                    "topic_name": "Any Topic",
                    "estimated_hours": 5.0,
                    "prerequisites": [],
                    "order": 1
                }
            ]
        }
        
        is_valid, error_msg = validate_roadmap_output(
            roadmap,
            allowed_topics=["something else"],
            strict_topic_check=False
        )
        
        assert is_valid is True


class TestPromptHelpers:
    """Tests for prompt generation helpers."""
    
    def test_get_roadmap_schema_prompt(self):
        """Test that schema prompt is generated."""
        prompt = get_roadmap_schema_prompt()
        
        assert len(prompt) > 0
        assert "modules" in prompt.lower()
        assert "topic_name" in prompt
        assert "estimated_hours" in prompt
    
    def test_get_topic_constraint_prompt(self):
        """Test that topic constraint prompt is generated."""
        topics = ["python", "programming", "data science"]
        prompt = get_topic_constraint_prompt(topics)
        
        assert len(prompt) > 0
        assert "python" in prompt.lower()
    
    def test_get_topic_constraint_prompt_empty(self):
        """Test that empty topics returns empty prompt."""
        prompt = get_topic_constraint_prompt([])
        
        assert prompt == ""
    
    def test_get_forbidden_domains_prompt(self):
        """Test that forbidden domains prompt is generated."""
        prompt = get_forbidden_domains_prompt()
        
        assert len(prompt) > 0
        assert "forbidden" in prompt.lower() or "not include" in prompt.lower()
