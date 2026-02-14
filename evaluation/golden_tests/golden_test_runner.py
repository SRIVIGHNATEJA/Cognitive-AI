"""
Golden Set Test Runner for AI Model Efficacy

Tests model correctness across multiple dimensions:
- Syllabus adherence
- Concept accuracy
- Hallucination resistance
- JSON compliance
"""

import sys
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from app.services.roadmap_service import RoadmapService
    from app.services.content_service import ContentService
    from app.services.quiz_service import QuizService
    from app.models import LearningMode, Module
    from app.config import settings
except ImportError as e:
    print(f"Error: Cannot import services. Ensure you're in project root.")
    print(f"Details: {e}")
    sys.exit(1)


class GoldenTestRunner:
    """
    Executes golden set tests and measures model efficacy.
    """
    
    def __init__(self, golden_set_path: str = "evaluation/golden_tests/golden_set.json"):
        self.golden_set_path = golden_set_path
        self.golden_set = None
        self.results = []
        
        # Initialize services
        self.roadmap_service = RoadmapService()
        self.content_service = ContentService()
        self.quiz_service = QuizService()
    
    def load_golden_set(self):
        """Load golden set test cases from JSON file."""
        try:
            with open(self.golden_set_path, 'r') as f:
                self.golden_set = json.load(f)
            print(f"✓ Loaded golden set from {self.golden_set_path}")
            print(f"  - Syllabus tests: {len(self.golden_set['syllabus_tests'])}")
            print(f"  - Concept tests: {len(self.golden_set['concept_tests'])}")
            print(f"  - Hallucination tests: {len(self.golden_set['hallucination_tests'])}")
            print(f"  - Quiz tests: {len(self.golden_set['quiz_tests'])}")
        except Exception as e:
            print(f"Error loading golden set: {e}")
            sys.exit(1)
    
    def test_syllabus_adherence(self, test_case: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Test if roadmap covers expected topics.
        
        Returns:
            (coverage_rate, result_dict)
        """
        print(f"\n  Testing: {test_case['name']}")
        
        try:
            # Generate roadmap
            modules = self.roadmap_service.generate_roadmap(
                input_text=test_case['input_text'],
                mode=LearningMode.UNTIMED,
                input_id=f"golden_{test_case['id']}"
            )
            
            # Extract generated topics
            generated_topics = [m.topic_name.lower() for m in modules]
            
            # Check coverage of expected topics
            expected_topics = test_case['expected_topics']
            found_count = 0
            
            for expected in expected_topics:
                # Fuzzy match: check if expected topic appears in any generated topic
                if any(expected.lower() in gen_topic for gen_topic in generated_topics):
                    found_count += 1
            
            coverage_rate = found_count / len(expected_topics) if expected_topics else 0
            passed = coverage_rate >= test_case['min_coverage']
            
            result = {
                'test_id': test_case['id'],
                'test_name': test_case['name'],
                'test_type': 'syllabus',
                'passed': passed,
                'coverage_rate': round(coverage_rate, 2),
                'expected_topics': len(expected_topics),
                'found_topics': found_count,
                'generated_modules': len(modules),
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"    Coverage: {coverage_rate*100:.1f}% ({found_count}/{len(expected_topics)}) - {'PASS' if passed else 'FAIL'}")
            
            return coverage_rate, result
            
        except Exception as e:
            print(f"    ERROR: {str(e)}")
            return 0.0, {
                'test_id': test_case['id'],
                'test_name': test_case['name'],
                'test_type': 'syllabus',
                'passed': False,
                'coverage_rate': 0.0,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def test_concept_accuracy(self, test_case: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Test if generated content includes expected concepts and avoids forbidden ones.
        
        Returns:
            (passed, result_dict)
        """
        print(f"\n  Testing: {test_case['name']}")
        
        try:
            # Create test module
            test_module = Module(
                module_id=f"mod_{test_case['id']}",
                topic_name=test_case['name'],
                estimated_hours=1,
                prerequisites=[],
                order=1
            )
            
            # Generate notes
            notes = self.content_service.generate_notes(
                module=test_module,
                input_text=test_case['input_text']
            )
            
            notes_lower = notes.lower()
            
            # Check for expected concepts
            expected_found = sum(1 for concept in test_case['expected_concepts'] 
                                if concept.lower() in notes_lower)
            expected_rate = expected_found / len(test_case['expected_concepts'])
            
            # Check for forbidden concepts
            forbidden_found = sum(1 for concept in test_case['forbidden_concepts'] 
                                 if concept.lower() in notes_lower)
            
            # Pass if most expected concepts found and no forbidden concepts
            passed = expected_rate >= 0.6 and forbidden_found == 0
            
            result = {
                'test_id': test_case['id'],
                'test_name': test_case['name'],
                'test_type': 'concept',
                'passed': passed,
                'expected_found': expected_found,
                'expected_total': len(test_case['expected_concepts']),
                'forbidden_found': forbidden_found,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"    Expected: {expected_found}/{len(test_case['expected_concepts'])}, "
                  f"Forbidden: {forbidden_found} - {'PASS' if passed else 'FAIL'}")
            
            return passed, result
            
        except Exception as e:
            print(f"    ERROR: {str(e)}")
            return False, {
                'test_id': test_case['id'],
                'test_name': test_case['name'],
                'test_type': 'concept',
                'passed': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def test_hallucination_resistance(self, test_case: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Test if model avoids hallucinating information.
        
        Returns:
            (passed, result_dict)
        """
        print(f"\n  Testing: {test_case['name']}")
        
        try:
            # Create test module
            test_module = Module(
                module_id=f"mod_{test_case['id']}",
                topic_name="Hallucination Test",
                estimated_hours=1,
                prerequisites=[],
                order=1
            )
            
            # Generate notes (which should stay within scope)
            notes = self.content_service.generate_notes(
                module=test_module,
                input_text=test_case['input_text']
            )
            
            notes_lower = notes.lower()
            
            # Check for forbidden responses
            hallucination_detected = any(
                forbidden.lower() in notes_lower 
                for forbidden in test_case['forbidden_responses']
            )
            
            # Pass if no hallucinations detected
            passed = not hallucination_detected
            
            result = {
                'test_id': test_case['id'],
                'test_name': test_case['name'],
                'test_type': 'hallucination',
                'passed': passed,
                'hallucination_detected': hallucination_detected,
                'expected_behavior': test_case['expected_behavior'],
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"    Hallucination: {'DETECTED' if hallucination_detected else 'NONE'} - "
                  f"{'FAIL' if hallucination_detected else 'PASS'}")
            
            return passed, result
            
        except Exception as e:
            print(f"    ERROR: {str(e)}")
            return False, {
                'test_id': test_case['id'],
                'test_name': test_case['name'],
                'test_type': 'hallucination',
                'passed': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def test_quiz_json_compliance(self, test_case: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Test if quiz generation produces valid JSON with correct structure.
        
        Returns:
            (passed, result_dict)
        """
        print(f"\n  Testing: {test_case['name']}")
        
        try:
            # Create test module
            test_module = Module(
                module_id=f"mod_{test_case['id']}",
                topic_name=test_case['module_name'],
                estimated_hours=1,
                prerequisites=[],
                order=1
            )
            
            # Generate quiz
            quiz = self.quiz_service.generate_quiz(
                module=test_module,
                content=test_case['input_text'],
                mode=LearningMode.UNTIMED
            )
            
            # Validate structure
            has_correct_question_count = len(quiz.questions) == test_case['expected_question_count']
            
            # Check each question has correct number of options
            correct_options_count = all(
                len(q.options) == test_case['expected_options_per_question'] 
                for q in quiz.questions
            )
            
            # Check all questions have text
            all_have_text = all(q.question_text and len(q.question_text) > 0 for q in quiz.questions)
            
            # Pass if all validations pass
            passed = has_correct_question_count and correct_options_count and all_have_text
            
            result = {
                'test_id': test_case['id'],
                'test_name': test_case['name'],
                'test_type': 'quiz_json',
                'passed': passed,
                'question_count': len(quiz.questions),
                'expected_questions': test_case['expected_question_count'],
                'correct_structure': correct_options_count,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"    Questions: {len(quiz.questions)}/{test_case['expected_question_count']}, "
                  f"Structure: {'OK' if correct_options_count else 'INVALID'} - "
                  f"{'PASS' if passed else 'FAIL'}")
            
            return passed, result
            
        except Exception as e:
            print(f"    ERROR: {str(e)}")
            return False, {
                'test_id': test_case['id'],
                'test_name': test_case['name'],
                'test_type': 'quiz_json',
                'passed': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def run_all_tests(self):
        """Execute all golden set tests."""
        print("\n" + "="*80)
        print("GOLDEN SET TESTING - AI MODEL EFFICACY")
        print("="*80)
        
        # Test syllabus adherence
        print("\n[1/4] SYLLABUS ADHERENCE TESTS")
        print("-" * 80)
        syllabus_coverage_rates = []
        for test_case in self.golden_set['syllabus_tests']:
            coverage, result = self.test_syllabus_adherence(test_case)
            syllabus_coverage_rates.append(coverage)
            self.results.append(result)
        
        # Test concept accuracy
        print("\n[2/4] CONCEPT ACCURACY TESTS")
        print("-" * 80)
        concept_passes = []
        for test_case in self.golden_set['concept_tests']:
            passed, result = self.test_concept_accuracy(test_case)
            concept_passes.append(passed)
            self.results.append(result)
        
        # Test hallucination resistance
        print("\n[3/4] HALLUCINATION RESISTANCE TESTS")
        print("-" * 80)
        hallucination_passes = []
        for test_case in self.golden_set['hallucination_tests']:
            passed, result = self.test_hallucination_resistance(test_case)
            hallucination_passes.append(passed)
            self.results.append(result)
        
        # Test quiz JSON compliance
        print("\n[4/4] QUIZ JSON COMPLIANCE TESTS")
        print("-" * 80)
        quiz_passes = []
        for test_case in self.golden_set['quiz_tests']:
            passed, result = self.test_quiz_json_compliance(test_case)
            quiz_passes.append(passed)
            self.results.append(result)
        
        # Calculate summary metrics
        syllabus_adherence = sum(syllabus_coverage_rates) / len(syllabus_coverage_rates) * 100
        concept_accuracy = sum(concept_passes) / len(concept_passes) * 100
        hallucination_pass_rate = sum(hallucination_passes) / len(hallucination_passes) * 100
        json_compliance_rate = sum(quiz_passes) / len(quiz_passes) * 100
        
        # Print summary
        print("\n" + "="*80)
        print("SUMMARY REPORT")
        print("="*80)
        print(f"Syllabus Adherence:      {syllabus_adherence:.1f}%")
        print(f"Concept Accuracy:        {concept_accuracy:.1f}%")
        print(f"Hallucination Pass Rate: {hallucination_pass_rate:.1f}%")
        print(f"JSON Compliance Rate:    {json_compliance_rate:.1f}%")
        print("="*80)
        
        return {
            'syllabus_adherence': syllabus_adherence,
            'concept_accuracy': concept_accuracy,
            'hallucination_pass_rate': hallucination_pass_rate,
            'json_compliance_rate': json_compliance_rate
        }
    
    def save_results(self, output_path: str = "evaluation/results/golden_results.csv"):
        """Save test results to CSV file."""
        try:
            # Ensure results directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Determine if file exists (for header)
            file_exists = Path(output_path).exists()
            
            # Write results
            with open(output_path, 'a', newline='') as f:
                if self.results:
                    # Get all possible fieldnames from results
                    fieldnames = set()
                    for result in self.results:
                        fieldnames.update(result.keys())
                    fieldnames = sorted(list(fieldnames))
                    
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    
                    # Write header if new file
                    if not file_exists:
                        writer.writeheader()
                    
                    # Write all results
                    for result in self.results:
                        writer.writerow(result)
            
            print(f"\n✓ Results saved to {output_path}")
            
        except Exception as e:
            print(f"\nError saving results: {e}")


def main():
    """Main entry point for golden set testing."""
    runner = GoldenTestRunner()
    
    # Load golden set
    runner.load_golden_set()
    
    # Run all tests
    summary = runner.run_all_tests()
    
    # Save results
    runner.save_results()
    
    print("\n✓ Golden set testing complete!\n")


if __name__ == "__main__":
    main()
