"""
Analytics Service for the Cognitive AI Learning Platform.

Handles progress tracking, completion calculations, and weak area identification.
Integrates with cache service to retrieve quiz metrics and roadmap data.
"""

import logging
from typing import List, Dict, Optional, Any

from app.models import ModuleProgress, Module
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service for calculating learning analytics and progress tracking.
    
    Responsibilities:
    - Calculate module completion percentages
    - Calculate overall progress across all modules
    - Identify weak areas based on quiz performance
    - Aggregate quiz metrics for analytics
    """
    
    def __init__(self, cache_service: Optional[CacheService] = None):
        """
        Initialize the analytics service.
        
        Args:
            cache_service: Cache service instance for data retrieval
        """
        self.cache_service = cache_service or CacheService()
        logger.info("AnalyticsService initialized")
    
    def calculate_module_completion(self, module_id: str) -> float:
        """
        Calculate completion percentage for a module.
        
        Completion is based on:
        - Has notes been generated? (50%)
        - Has at least one quiz been taken? (50%)
        
        Args:
            module_id: Module identifier
            
        Returns:
            Completion percentage (0-100)
        """
        logger.debug(f"Calculating completion for module '{module_id}'")
        
        completion = 0.0
        
        # Check if notes exist (50%)
        notes = self.cache_service.get_cached_content(module_id, 'notes')
        if notes:
            completion += 50.0
            logger.debug(f"Module {module_id}: notes generated (+50%)")
        
        # Check if at least one quiz taken (50%)
        metrics = self.cache_service.get_quiz_metrics(module_id)
        if metrics and metrics.get("total_quizzes", 0) > 0:
            completion += 50.0
            logger.debug(f"Module {module_id}: quizzes taken (+50%)")
        
        logger.info(f"Module '{module_id}' completion: {completion}%")
        return completion
    
    def calculate_overall_progress(self) -> float:
        """
        Calculate overall progress percentage across all modules.
        
        Overall progress is the average completion percentage of all modules.
        
        Returns:
            Overall progress percentage (0-100)
        """
        logger.debug("Calculating overall progress")
        
        # Get roadmap
        roadmap_data = self.cache_service.get_cached_roadmap()
        if not roadmap_data:
            logger.warning("No roadmap found for progress calculation")
            return 0.0
        
        modules = roadmap_data.get("modules", [])
        if not modules:
            logger.warning("No modules in roadmap")
            return 0.0
        
        # Calculate average completion across all modules
        total_completion = 0.0
        for module_data in modules:
            module_id = module_data.get("module_id")
            if module_id:
                completion = self.calculate_module_completion(module_id)
                total_completion += completion
        
        overall_progress = total_completion / len(modules)
        logger.info(f"Overall progress: {overall_progress:.1f}%")
        
        return overall_progress
    
    def identify_weak_areas(self, threshold: float = 60.0) -> List[str]:
        """
        Identify modules with quiz accuracy below threshold.
        
        A module is considered weak if:
        - At least one quiz has been taken
        - Average quiz accuracy is below the threshold
        
        Args:
            threshold: Accuracy threshold percentage (default: 60%)
            
        Returns:
            List of module IDs with accuracy below threshold
        """
        logger.debug(f"Identifying weak areas (threshold: {threshold}%)")
        
        weak_module_ids = []
        
        # Get roadmap
        roadmap_data = self.cache_service.get_cached_roadmap()
        if not roadmap_data:
            logger.warning("No roadmap found for weak area identification")
            return weak_module_ids
        
        modules = roadmap_data.get("modules", [])
        
        # Check each module's quiz performance
        for module_data in modules:
            module_id = module_data.get("module_id")
            if not module_id:
                continue
            
            metrics = self.cache_service.get_quiz_metrics(module_id)
            if metrics and metrics.get("total_quizzes", 0) > 0:
                avg_accuracy = metrics.get("average_accuracy", 0.0)
                
                if avg_accuracy < threshold:
                    weak_module_ids.append(module_id)
                    logger.debug(
                        f"Weak area identified: {module_id} "
                        f"(accuracy: {avg_accuracy:.1f}% < {threshold}%)"
                    )
        
        logger.info(f"Identified {len(weak_module_ids)} weak areas")
        return weak_module_ids
    
    def aggregate_quiz_metrics(self, module_id: str) -> Dict[str, Any]:
        """
        Aggregate quiz metrics for a module.
        
        Returns quiz performance data including:
        - Total quizzes taken
        - Average score and accuracy
        - Best and worst scores
        
        Args:
            module_id: Module identifier
            
        Returns:
            Dictionary with aggregated metrics, or empty dict if no metrics
        """
        logger.debug(f"Aggregating quiz metrics for module '{module_id}'")
        
        metrics = self.cache_service.get_quiz_metrics(module_id)
        
        if not metrics:
            logger.debug(f"No quiz metrics found for module '{module_id}'")
            return {}
        
        logger.info(
            f"Aggregated metrics for '{module_id}': "
            f"{metrics.get('total_quizzes', 0)} quizzes, "
            f"{metrics.get('average_accuracy', 0):.1f}% avg accuracy"
        )
        
        return metrics
    
    def get_module_progress(self, module_id: str, topic_name: str) -> ModuleProgress:
        """
        Get progress data for a specific module.
        
        Args:
            module_id: Module identifier
            topic_name: Module topic name
            
        Returns:
            ModuleProgress object with completion and quiz data
        """
        logger.debug(f"Getting progress for module '{module_id}'")
        
        # Calculate completion
        completion = self.calculate_module_completion(module_id)
        
        # Get quiz metrics
        metrics = self.aggregate_quiz_metrics(module_id)
        quizzes_taken = metrics.get("total_quizzes", 0)
        average_accuracy = metrics.get("average_accuracy", 0.0)
        
        progress = ModuleProgress(
            module_id=module_id,
            topic_name=topic_name,
            completion_percentage=completion,
            quizzes_taken=quizzes_taken,
            average_accuracy=average_accuracy
        )
        
        return progress
    
    def get_all_module_progress(self) -> List[ModuleProgress]:
        """
        Get progress data for all modules in the roadmap.
        
        Returns:
            List of ModuleProgress objects for all modules
        """
        logger.debug("Getting progress for all modules")
        
        # Get roadmap
        roadmap_data = self.cache_service.get_cached_roadmap()
        if not roadmap_data:
            logger.warning("No roadmap found")
            return []
        
        modules = roadmap_data.get("modules", [])
        progress_list = []
        
        for module_data in modules:
            module_id = module_data.get("module_id")
            topic_name = module_data.get("topic_name", "Unknown")
            
            if module_id:
                progress = self.get_module_progress(module_id, topic_name)
                progress_list.append(progress)
        
        logger.info(f"Retrieved progress for {len(progress_list)} modules")
        return progress_list
    
    def count_completed_modules(self, threshold: float = 100.0) -> int:
        """
        Count modules that meet the completion threshold.
        
        Args:
            threshold: Completion threshold percentage (default: 100%)
            
        Returns:
            Number of modules meeting the threshold
        """
        logger.debug(f"Counting completed modules (threshold: {threshold}%)")
        
        # Get roadmap
        roadmap_data = self.cache_service.get_cached_roadmap()
        if not roadmap_data:
            return 0
        
        modules = roadmap_data.get("modules", [])
        completed_count = 0
        
        for module_data in modules:
            module_id = module_data.get("module_id")
            if module_id:
                completion = self.calculate_module_completion(module_id)
                if completion >= threshold:
                    completed_count += 1
        
        logger.info(f"Completed modules: {completed_count}/{len(modules)}")
        return completed_count
    
    def calculate_average_quiz_accuracy(self) -> float:
        """
        Calculate average quiz accuracy across all modules.
        
        Only includes modules where at least one quiz has been taken.
        
        Returns:
            Average quiz accuracy percentage (0-100)
        """
        logger.debug("Calculating average quiz accuracy across all modules")
        
        # Get roadmap
        roadmap_data = self.cache_service.get_cached_roadmap()
        if not roadmap_data:
            return 0.0
        
        modules = roadmap_data.get("modules", [])
        
        total_accuracy = 0.0
        modules_with_quizzes = 0
        
        for module_data in modules:
            module_id = module_data.get("module_id")
            if not module_id:
                continue
            
            metrics = self.cache_service.get_quiz_metrics(module_id)
            if metrics and metrics.get("total_quizzes", 0) > 0:
                total_accuracy += metrics.get("average_accuracy", 0.0)
                modules_with_quizzes += 1
        
        if modules_with_quizzes == 0:
            logger.info("No quizzes taken yet")
            return 0.0
        
        avg_accuracy = total_accuracy / modules_with_quizzes
        logger.info(f"Average quiz accuracy: {avg_accuracy:.1f}%")
        
        return avg_accuracy
    
    def get_quiz_attempt_history(self, quiz_id: str) -> List[Dict[str, Any]]:
        """
        Get all attempts for a specific quiz, ordered by attempt_number.
        
        Searches through all evaluation cache files to find evaluations
        matching the quiz_id, then sorts by attempt_number.
        
        Args:
            quiz_id: Quiz identifier
            
        Returns:
            List of attempt data dictionaries, sorted by attempt_number
            Each dict contains: attempt_number, score, accuracy, time_taken_seconds, evaluated_at
        """
        logger.debug(f"Getting attempt history for quiz '{quiz_id}'")
        
        attempts = []
        quizzes_dir = self.cache_service.cache_dir / 'quizzes'
        
        if not quizzes_dir.exists():
            logger.warning(f"Quizzes directory not found")
            return attempts
        
        # Search through all evaluation files
        for eval_file in quizzes_dir.glob('evaluation_*.json'):
            try:
                json_data = eval_file.read_text(encoding='utf-8')
                evaluation = self.cache_service._deserialize_data(json_data)
                
                # Check if this evaluation matches the quiz_id
                if evaluation.get("quiz_id") == quiz_id:
                    # Extract relevant fields
                    attempt_data = {
                        "attempt_number": evaluation.get("attempt_number", 1),
                        "score": evaluation.get("score", 0),
                        "accuracy": evaluation.get("accuracy", 0.0),
                        "time_taken_seconds": evaluation.get("time_taken_seconds", 0),
                        "evaluated_at": evaluation.get("evaluated_at", "")
                    }
                    attempts.append(attempt_data)
                    logger.debug(f"Found attempt {attempt_data['attempt_number']} for quiz {quiz_id}")
                    
            except Exception as e:
                logger.warning(f"Failed to read evaluation file {eval_file}: {str(e)}")
                continue
        
        # Sort by attempt_number
        attempts.sort(key=lambda x: x["attempt_number"])
        
        logger.info(f"Found {len(attempts)} attempts for quiz '{quiz_id}'")
        return attempts
    
    def calculate_improvement_rate(self, attempts: List[Dict[str, Any]]) -> Optional[float]:
        """
        Calculate improvement rate from first to latest attempt.
        
        Formula: (latest_accuracy - first_accuracy) / first_accuracy * 100
        
        Args:
            attempts: List of attempt data dictionaries (must be sorted by attempt_number)
            
        Returns:
            Percentage improvement (e.g., 50.0 for 50% improvement)
            None if less than 2 attempts or first attempt has 0% accuracy
        """
        if len(attempts) < 2:
            logger.debug("Less than 2 attempts, no improvement rate to calculate")
            return None
        
        first_accuracy = attempts[0].get("accuracy", 0.0)
        latest_accuracy = attempts[-1].get("accuracy", 0.0)
        
        # Avoid division by zero
        if first_accuracy == 0.0:
            logger.debug("First attempt has 0% accuracy, cannot calculate improvement rate")
            return None
        
        improvement_rate = ((latest_accuracy - first_accuracy) / first_accuracy) * 100.0
        logger.info(f"Improvement rate: {improvement_rate:.1f}% ({first_accuracy:.1f}% → {latest_accuracy:.1f}%)")
        
        return improvement_rate


# Global analytics service instance
analytics_service = AnalyticsService()
