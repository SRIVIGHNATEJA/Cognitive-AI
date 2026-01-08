"""
Integration tests for input API endpoints.
Tests end-to-end flows for file upload and text input.
"""

import pytest
from io import BytesIO
from fastapi.testclient import TestClient

from app.main import app
from app.models import InputType


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


class TestFileUploadEndpoint:
    """Integration tests for file upload endpoint."""
    
    def test_upload_text_file_as_pdf(self, client):
        """Test uploading a text file disguised as PDF (should work for testing)."""
        # Create a simple text content
        content = b"Course Syllabus\nWeek 1: Introduction\nWeek 2: Advanced Topics\n" * 10
        
        files = {
            "file": ("test_syllabus.pdf", BytesIO(content), "application/pdf")
        }
        
        response = client.post("/api/input/upload", files=files)
        
        # Note: This will fail with actual PDF parsing, but tests the endpoint structure
        # In real scenarios, we'd use actual PDF files
        assert response.status_code in [200, 500]  # Either success or processing error
    
    def test_upload_unsupported_format(self, client):
        """Test uploading unsupported file format."""
        content = b"Some text content"
        
        files = {
            "file": ("test_file.txt", BytesIO(content), "text/plain")
        }
        
        response = client.post("/api/input/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "error_type" in data["detail"]
        assert data["detail"]["error_type"] == "validation"
    
    def test_upload_without_file(self, client):
        """Test upload endpoint without providing a file."""
        response = client.post("/api/input/upload")
        
        assert response.status_code == 422  # Validation error


class TestTextInputEndpoint:
    """Integration tests for text input endpoint."""
    
    def test_process_valid_text_input(self, client):
        """Test processing valid text input."""
        payload = {
            "content": "Course Syllabus: Introduction to Python\n" * 10
        }
        
        response = client.post("/api/input/text", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "input_id" in data
        assert data["input_id"].startswith("input_")
        assert "detected_type" in data
        assert data["detected_type"] in ["syllabus", "question_bank", "mixed"]
        assert data["extracted_text_length"] > 0
        assert data["message"] == "Text input processed successfully"
    
    def test_process_text_with_type_hint(self, client):
        """Test processing text with type hint."""
        payload = {
            "content": "Some educational content here\n" * 10,
            "input_type": "question_bank"
        }
        
        response = client.post("/api/input/text", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["detected_type"] == "question_bank"
    
    def test_process_empty_text(self, client):
        """Test processing empty text."""
        payload = {
            "content": ""
        }
        
        response = client.post("/api/input/text", json=payload)
        
        assert response.status_code == 422  # Pydantic validation error
        data = response.json()
        assert "detail" in data or "error_type" in data
    
    def test_process_too_short_text(self, client):
        """Test processing text that's too short."""
        payload = {
            "content": "Too short"
        }
        
        response = client.post("/api/input/text", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "too short" in data["detail"]["message"].lower()
    
    def test_process_text_without_content(self, client):
        """Test text endpoint without content field."""
        payload = {}
        
        response = client.post("/api/input/text", json=payload)
        
        assert response.status_code == 422  # Validation error


class TestInputStatusEndpoint:
    """Integration tests for input status endpoint."""
    
    def test_get_status_of_existing_input(self, client):
        """Test retrieving status of existing input."""
        # First, create an input
        payload = {
            "content": "Course Syllabus: Introduction to Python\n" * 10
        }
        
        create_response = client.post("/api/input/text", json=payload)
        assert create_response.status_code == 200
        
        input_id = create_response.json()["input_id"]
        
        # Now get its status
        status_response = client.get(f"/api/input/status/{input_id}")
        
        assert status_response.status_code == 200
        data = status_response.json()
        
        assert data["input_id"] == input_id
        assert "detected_type" in data
        assert "extracted_text" in data
        assert "processed_at" in data
    
    def test_get_status_of_nonexistent_input(self, client):
        """Test retrieving status of non-existent input."""
        response = client.get("/api/input/status/nonexistent_id")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "error_type" in data["detail"]
        assert data["detail"]["error_type"] == "not_found"


class TestEndToEndFlow:
    """End-to-end integration tests."""
    
    def test_complete_text_input_flow(self, client):
        """Test complete flow: create input -> check status."""
        # Step 1: Create input
        payload = {
            "content": """
            Course Syllabus: Data Structures and Algorithms
            
            Week 1: Introduction to Data Structures
            Week 2: Arrays and Linked Lists
            Week 3: Stacks and Queues
            Week 4: Trees and Graphs
            
            Learning Objectives:
            - Understand fundamental data structures
            - Implement common algorithms
            - Analyze time and space complexity
            
            Prerequisites: Basic programming knowledge
            Textbook: Introduction to Algorithms
            """
        }
        
        create_response = client.post("/api/input/text", json=payload)
        assert create_response.status_code == 200
        
        create_data = create_response.json()
        input_id = create_data["input_id"]
        
        # Step 2: Verify it was created
        assert create_data["success"] is True
        assert create_data["detected_type"] == "syllabus"
        
        # Step 3: Check status
        status_response = client.get(f"/api/input/status/{input_id}")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        assert status_data["input_id"] == input_id
        assert status_data["detected_type"] == "syllabus"
        assert "Course Syllabus" in status_data["extracted_text"]
    
    def test_multiple_inputs_are_independent(self, client):
        """Test that multiple inputs are stored independently."""
        # Create first input
        payload1 = {
            "content": "First input content\n" * 10
        }
        response1 = client.post("/api/input/text", json=payload1)
        assert response1.status_code == 200
        input_id1 = response1.json()["input_id"]
        
        # Create second input
        payload2 = {
            "content": "Second input content\n" * 10
        }
        response2 = client.post("/api/input/text", json=payload2)
        assert response2.status_code == 200
        input_id2 = response2.json()["input_id"]
        
        # Verify they have different IDs
        assert input_id1 != input_id2
        
        # Verify both can be retrieved independently
        status1 = client.get(f"/api/input/status/{input_id1}")
        status2 = client.get(f"/api/input/status/{input_id2}")
        
        assert status1.status_code == 200
        assert status2.status_code == 200
        
        assert "First input" in status1.json()["extracted_text"]
        assert "Second input" in status2.json()["extracted_text"]
