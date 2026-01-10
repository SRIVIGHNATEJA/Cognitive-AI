"""
Cache service for persistent storage of generated content.

Provides file-based caching with JSON serialization for all system data
including input, roadmaps, content, quizzes, and session state.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class CacheService:
    """
    File-based cache service for persistent data storage.
    
    Manages cache directory structure and provides methods for storing
    and retrieving cached data using JSON serialization.
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the cache service.
        
        Args:
            cache_dir: Optional custom cache directory path.
                      Defaults to settings.cache_dir
        """
        self.cache_dir = Path(cache_dir or settings.cache_dir)
        self._ensure_cache_structure()
    
    def _ensure_cache_structure(self) -> None:
        """
        Ensure the cache directory structure exists.
        
        Creates the main cache directory and all required subdirectories.
        """
        # Create main cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        subdirs = ['input', 'roadmap', 'content', 'quizzes', 'analytics']
        for subdir in subdirs:
            (self.cache_dir / subdir).mkdir(exist_ok=True)
        
        logger.info(f"Cache directory structure initialized at: {self.cache_dir}")
    
    def _serialize_data(self, data: Any) -> str:
        """
        Serialize data to JSON string.
        
        Handles datetime objects and other non-JSON-serializable types.
        
        Args:
            data: Data to serialize
            
        Returns:
            JSON string representation
        """
        def json_serializer(obj):
            """Custom JSON serializer for datetime objects."""
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        return json.dumps(data, indent=2, default=json_serializer)
    
    def _deserialize_data(self, json_str: str) -> Any:
        """
        Deserialize JSON string to Python object.
        
        Args:
            json_str: JSON string to deserialize
            
        Returns:
            Deserialized Python object
        """
        return json.loads(json_str)
    
    def cache_input(self, input_id: str, data: Dict[str, Any]) -> None:
        """
        Cache extracted input content.
        
        Args:
            input_id: Unique identifier for the input
            data: Input data to cache (should be JSON-serializable)
        """
        try:
            cache_file = self.cache_dir / 'input' / f'{input_id}.json'
            json_data = self._serialize_data(data)
            
            cache_file.write_text(json_data, encoding='utf-8')
            logger.info(f"Cached input data: {input_id}")
            
        except Exception as e:
            logger.error(f"Failed to cache input {input_id}: {str(e)}")
            raise
    
    def get_cached_data(self, cache_key: str, cache_type: str = 'input') -> Optional[Dict[str, Any]]:
        """
        Retrieve cached data by key and type.
        
        Args:
            cache_key: Identifier for the cached data
            cache_type: Type of cache ('input', 'roadmap', 'content', etc.)
            
        Returns:
            Cached data if found, None otherwise
        """
        try:
            cache_file = self.cache_dir / cache_type / f'{cache_key}.json'
            
            if not cache_file.exists():
                logger.debug(f"Cache miss: {cache_type}/{cache_key}")
                return None
            
            json_data = cache_file.read_text(encoding='utf-8')
            data = self._deserialize_data(json_data)
            
            logger.info(f"Cache hit: {cache_type}/{cache_key}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to retrieve cached data {cache_type}/{cache_key}: {str(e)}")
            return None
    
    def cache_exists(self, cache_key: str, cache_type: str = 'input') -> bool:
        """
        Check if cached data exists.
        
        Args:
            cache_key: Identifier for the cached data
            cache_type: Type of cache
            
        Returns:
            True if cache exists, False otherwise
        """
        cache_file = self.cache_dir / cache_type / f'{cache_key}.json'
        return cache_file.exists()
    
    def delete_cache(self, cache_key: str, cache_type: str = 'input') -> bool:
        """
        Delete cached data.
        
        Args:
            cache_key: Identifier for the cached data
            cache_type: Type of cache
            
        Returns:
            True if deleted successfully, False if not found
        """
        try:
            cache_file = self.cache_dir / cache_type / f'{cache_key}.json'
            
            if cache_file.exists():
                cache_file.unlink()
                logger.info(f"Deleted cache: {cache_type}/{cache_key}")
                return True
            else:
                logger.debug(f"Cache not found for deletion: {cache_type}/{cache_key}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete cache {cache_type}/{cache_key}: {str(e)}")
            return False
    
    def clear_cache_type(self, cache_type: str) -> int:
        """
        Clear all cached data of a specific type.
        
        Args:
            cache_type: Type of cache to clear
            
        Returns:
            Number of files deleted
        """
        try:
            cache_dir = self.cache_dir / cache_type
            if not cache_dir.exists():
                return 0
            
            count = 0
            for cache_file in cache_dir.glob('*.json'):
                cache_file.unlink()
                count += 1
            
            logger.info(f"Cleared {count} files from {cache_type} cache")
            return count
            
        except Exception as e:
            logger.error(f"Failed to clear {cache_type} cache: {str(e)}")
            return 0
    
    def load_session(self) -> Optional[Dict[str, Any]]:
        """
        Load session data from cache.
        
        Returns:
            Session data if found, None otherwise
        """
        try:
            session_file = self.cache_dir / 'session.json'
            
            if not session_file.exists():
                logger.info("No existing session found")
                return None
            
            json_data = session_file.read_text(encoding='utf-8')
            session_data = self._deserialize_data(json_data)
            
            logger.info("Session data loaded successfully")
            return session_data
            
        except Exception as e:
            logger.error(f"Failed to load session: {str(e)}")
            return None
    
    def save_session(self, session_data: Dict[str, Any]) -> None:
        """
        Save session data to cache.
        
        Args:
            session_data: Session data to save
        """
        try:
            session_file = self.cache_dir / 'session.json'
            json_data = self._serialize_data(session_data)
            
            session_file.write_text(json_data, encoding='utf-8')
            logger.info("Session data saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save session: {str(e)}")
            raise
    
    def cache_roadmap(self, roadmap_data: Dict[str, Any]) -> None:
        """
        Cache roadmap data permanently for the session.
        
        Roadmaps are cached once and never regenerated unless explicitly reset.
        
        Args:
            roadmap_data: Roadmap data to cache (should be JSON-serializable)
        """
        try:
            cache_file = self.cache_dir / 'roadmap' / 'roadmap.json'
            json_data = self._serialize_data(roadmap_data)
            
            cache_file.write_text(json_data, encoding='utf-8')
            logger.info("Cached roadmap data")
            
        except Exception as e:
            logger.error(f"Failed to cache roadmap: {str(e)}")
            raise
    
    def get_cached_roadmap(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached roadmap data.
        
        Returns:
            Cached roadmap data if found, None otherwise
        """
        try:
            cache_file = self.cache_dir / 'roadmap' / 'roadmap.json'
            
            if not cache_file.exists():
                logger.debug("Roadmap cache miss")
                return None
            
            json_data = cache_file.read_text(encoding='utf-8')
            data = self._deserialize_data(json_data)
            
            logger.info("Roadmap cache hit")
            return data
            
        except Exception as e:
            logger.error(f"Failed to retrieve cached roadmap: {str(e)}")
            return None
    
    def clear_cache(self, cache_type: Optional[str] = None) -> int:
        """
        Clear cached content. Can clear specific type or all caches.
        
        Args:
            cache_type: Optional type of cache to clear ('roadmap', 'content', etc.)
                       If None, clears all caches except input and session
            
        Returns:
            Number of files deleted
        """
        if cache_type:
            # Clear specific cache type
            return self.clear_cache_type(cache_type)
        else:
            # Clear all caches except input and session
            total_deleted = 0
            for ctype in ['roadmap', 'content', 'quizzes', 'analytics']:
                total_deleted += self.clear_cache_type(ctype)
            
            logger.info(f"Cleared all caches: {total_deleted} files deleted")
            return total_deleted
    
    def cache_content(
        self,
        module_id: str,
        content_type: str,
        content: str
    ) -> None:
        """
        Cache generated content (notes or cheat sheet) for a module.
        
        Content is cached permanently per session.
        
        Args:
            module_id: Module identifier
            content_type: Type of content ('notes' or 'cheatsheet')
            content: Generated content to cache
        """
        try:
            filename = f"{content_type}_{module_id}.json"
            cache_file = self.cache_dir / 'content' / filename
            
            content_data = {
                "module_id": module_id,
                "content_type": content_type,
                "content": content,
                "cached_at": datetime.now().isoformat()
            }
            
            json_data = self._serialize_data(content_data)
            cache_file.write_text(json_data, encoding='utf-8')
            
            logger.info(f"Cached {content_type} for module {module_id}")
            
        except Exception as e:
            logger.error(f"Failed to cache {content_type} for {module_id}: {str(e)}")
            raise
    
    def get_cached_content(
        self,
        module_id: str,
        content_type: str
    ) -> Optional[str]:
        """
        Retrieve cached content for a module.
        
        Args:
            module_id: Module identifier
            content_type: Type of content ('notes' or 'cheatsheet')
            
        Returns:
            Cached content if found, None otherwise
        """
        try:
            filename = f"{content_type}_{module_id}.json"
            cache_file = self.cache_dir / 'content' / filename
            
            if not cache_file.exists():
                logger.debug(f"{content_type} cache miss for module {module_id}")
                return None
            
            json_data = cache_file.read_text(encoding='utf-8')
            content_data = self._deserialize_data(json_data)
            
            logger.info(f"{content_type} cache hit for module {module_id}")
            return content_data.get("content")
            
        except Exception as e:
            logger.error(f"Failed to retrieve cached {content_type} for {module_id}: {str(e)}")
            return None
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get statistics about cached data.
        
        Returns:
            Dictionary with count of cached items by type
        """
        stats = {}
        
        for cache_type in ['input', 'roadmap', 'content', 'quizzes', 'analytics']:
            cache_dir = self.cache_dir / cache_type
            if cache_dir.exists():
                stats[cache_type] = len(list(cache_dir.glob('*.json')))
            else:
                stats[cache_type] = 0
        
        # Check for session file
        stats['session'] = 1 if (self.cache_dir / 'session.json').exists() else 0
        
        return stats
    
    def cache_quiz_qa(self, module_id: str, quiz_data: Dict[str, Any]) -> None:
        """
        Cache quiz Q&A data for a module.
        
        Q&A data is subject to pruning (only last 2 retained per module).
        If a quiz with the same quiz_id already exists, it will be updated.
        
        Args:
            module_id: Module identifier
            quiz_data: Quiz Q&A data to cache
        """
        try:
            # Get existing Q&A data
            qa_file = self.cache_dir / 'quizzes' / f'{module_id}_qa.json'
            
            if qa_file.exists():
                json_data = qa_file.read_text(encoding='utf-8')
                existing_data = self._deserialize_data(json_data)
                quizzes = existing_data.get("quizzes", [])
            else:
                quizzes = []
            
            # Check if quiz already exists (update instead of append)
            quiz_id = quiz_data.get("quiz_id")
            existing_index = None
            for i, q in enumerate(quizzes):
                if q.get("quiz_id") == quiz_id:
                    existing_index = i
                    break
            
            if existing_index is not None:
                # Update existing quiz
                quizzes[existing_index] = quiz_data
                logger.debug(f"Updated existing quiz {quiz_id} for module {module_id}")
            else:
                # Add new quiz data
                quizzes.append(quiz_data)
                logger.debug(f"Added new quiz {quiz_id} for module {module_id}")
            
            # Save updated data
            qa_data = {
                "module_id": module_id,
                "quizzes": quizzes,
                "updated_at": datetime.now().isoformat()
            }
            
            json_str = self._serialize_data(qa_data)
            qa_file.write_text(json_str, encoding='utf-8')
            
            logger.info(f"Cached quiz Q&A for module {module_id} (total: {len(quizzes)})")
            
        except Exception as e:
            logger.error(f"Failed to cache quiz Q&A for {module_id}: {str(e)}")
            raise
    
    def cache_quiz_metrics(self, module_id: str, metrics: Dict[str, Any]) -> None:
        """
        Cache quiz metrics for a module.
        
        Metrics are retained permanently regardless of Q&A pruning.
        
        Args:
            module_id: Module identifier
            metrics: Quiz metrics to cache
        """
        try:
            metrics_file = self.cache_dir / 'quizzes' / f'{module_id}_metrics.json'
            
            metrics_data = {
                **metrics,
                "updated_at": datetime.now().isoformat()
            }
            
            json_str = self._serialize_data(metrics_data)
            metrics_file.write_text(json_str, encoding='utf-8')
            
            logger.info(f"Cached quiz metrics for module {module_id}")
            
        except Exception as e:
            logger.error(f"Failed to cache quiz metrics for {module_id}: {str(e)}")
            raise
    
    def prune_quiz_qa(self, module_id: str) -> None:
        """
        Prune old quiz Q&A data, keeping only the last 2 quizzes per module.
        
        This method does NOT affect quiz metrics (retained permanently).
        
        Args:
            module_id: Module identifier
        """
        try:
            qa_file = self.cache_dir / 'quizzes' / f'{module_id}_qa.json'
            
            if not qa_file.exists():
                logger.debug(f"No Q&A data to prune for module {module_id}")
                return
            
            # Load existing data
            json_data = qa_file.read_text(encoding='utf-8')
            existing_data = self._deserialize_data(json_data)
            quizzes = existing_data.get("quizzes", [])
            
            # Keep only last 2 quizzes
            if len(quizzes) > 2:
                pruned_count = len(quizzes) - 2
                quizzes = quizzes[-2:]  # Keep last 2
                
                # Save pruned data
                qa_data = {
                    "module_id": module_id,
                    "quizzes": quizzes,
                    "updated_at": datetime.now().isoformat()
                }
                
                json_str = self._serialize_data(qa_data)
                qa_file.write_text(json_str, encoding='utf-8')
                
                logger.info(f"Pruned {pruned_count} old quiz Q&As for module {module_id} (kept last 2)")
            else:
                logger.debug(f"No pruning needed for module {module_id} ({len(quizzes)} quizzes)")
            
        except Exception as e:
            logger.error(f"Failed to prune quiz Q&A for {module_id}: {str(e)}")
            raise
    
    def get_quiz_history(self, module_id: str) -> Optional[list]:
        """
        Retrieve quiz history (last 2 Q&As) for a module.
        
        Args:
            module_id: Module identifier
            
        Returns:
            List of quiz Q&A data (max 2), or None if not found
        """
        try:
            qa_file = self.cache_dir / 'quizzes' / f'{module_id}_qa.json'
            
            if not qa_file.exists():
                logger.debug(f"No quiz history found for module {module_id}")
                return None
            
            json_data = qa_file.read_text(encoding='utf-8')
            qa_data = self._deserialize_data(json_data)
            
            quizzes = qa_data.get("quizzes", [])
            logger.info(f"Retrieved {len(quizzes)} quiz Q&As for module {module_id}")
            
            return quizzes
            
        except Exception as e:
            logger.error(f"Failed to retrieve quiz history for {module_id}: {str(e)}")
            return None
    
    def get_quiz_metrics(self, module_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve quiz metrics for a module.
        
        Args:
            module_id: Module identifier
            
        Returns:
            Quiz metrics if found, None otherwise
        """
        try:
            metrics_file = self.cache_dir / 'quizzes' / f'{module_id}_metrics.json'
            
            if not metrics_file.exists():
                logger.debug(f"No quiz metrics found for module {module_id}")
                return None
            
            json_data = metrics_file.read_text(encoding='utf-8')
            metrics = self._deserialize_data(json_data)
            
            logger.info(f"Retrieved quiz metrics for module {module_id}")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to retrieve quiz metrics for {module_id}: {str(e)}")
            return None
    
    def cache_analytics(self, analytics_data: Dict[str, Any]) -> None:
        """
        Cache analytics data for the current session.
        
        Analytics data includes overall progress, module progress, and weak areas.
        
        Args:
            analytics_data: Analytics data to cache (should be JSON-serializable)
        """
        try:
            cache_file = self.cache_dir / 'analytics' / 'analytics.json'
            
            # Add timestamp
            analytics_with_timestamp = {
                **analytics_data,
                "cached_at": datetime.now().isoformat()
            }
            
            json_data = self._serialize_data(analytics_with_timestamp)
            cache_file.write_text(json_data, encoding='utf-8')
            
            logger.info("Cached analytics data")
            
        except Exception as e:
            logger.error(f"Failed to cache analytics: {str(e)}")
            raise
    
    def get_cached_analytics(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached analytics data.
        
        Returns:
            Cached analytics data if found, None otherwise
        """
        try:
            cache_file = self.cache_dir / 'analytics' / 'analytics.json'
            
            if not cache_file.exists():
                logger.debug("Analytics cache miss")
                return None
            
            json_data = cache_file.read_text(encoding='utf-8')
            data = self._deserialize_data(json_data)
            
            logger.info("Analytics cache hit")
            return data
            
        except Exception as e:
            logger.error(f"Failed to retrieve cached analytics: {str(e)}")
            return None
    
    def cache_quiz_submission(self, submission_data: Dict[str, Any]) -> None:
        """
        Cache quiz submission data.
        
        Submissions are stored separately from quizzes to enable deferred evaluation.
        
        Args:
            submission_data: Submission data to cache (should be JSON-serializable)
        """
        try:
            submission_id = submission_data.get("submission_id")
            quiz_id = submission_data.get("quiz_id")
            
            if not submission_id or not quiz_id:
                raise ValueError("submission_id and quiz_id are required")
            
            cache_file = self.cache_dir / 'quizzes' / f'submission_{submission_id}.json'
            json_data = self._serialize_data(submission_data)
            
            cache_file.write_text(json_data, encoding='utf-8')
            logger.info(f"Cached quiz submission: {submission_id} for quiz {quiz_id}")
            
        except Exception as e:
            logger.error(f"Failed to cache quiz submission: {str(e)}")
            raise
    
    def get_quiz_submission(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached quiz submission.
        
        Args:
            submission_id: Submission identifier
            
        Returns:
            Submission data if found, None otherwise
        """
        try:
            cache_file = self.cache_dir / 'quizzes' / f'submission_{submission_id}.json'
            
            if not cache_file.exists():
                logger.debug(f"Submission cache miss: {submission_id}")
                return None
            
            json_data = cache_file.read_text(encoding='utf-8')
            data = self._deserialize_data(json_data)
            
            logger.info(f"Submission cache hit: {submission_id}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to retrieve submission {submission_id}: {str(e)}")
            return None
    
    def cache_quiz_evaluation(self, evaluation_data: Dict[str, Any]) -> None:
        """
        Cache quiz evaluation results.
        
        Evaluations are stored permanently for analytics and future reference.
        
        Args:
            evaluation_data: Evaluation data to cache (should be JSON-serializable)
        """
        try:
            evaluation_id = evaluation_data.get("evaluation_id")
            quiz_id = evaluation_data.get("quiz_id")
            
            if not evaluation_id or not quiz_id:
                raise ValueError("evaluation_id and quiz_id are required")
            
            cache_file = self.cache_dir / 'quizzes' / f'evaluation_{evaluation_id}.json'
            json_data = self._serialize_data(evaluation_data)
            
            cache_file.write_text(json_data, encoding='utf-8')
            logger.info(f"Cached quiz evaluation: {evaluation_id} for quiz {quiz_id}")
            
        except Exception as e:
            logger.error(f"Failed to cache quiz evaluation: {str(e)}")
            raise
    
    def get_quiz_evaluation(self, evaluation_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached quiz evaluation.
        
        Args:
            evaluation_id: Evaluation identifier
            
        Returns:
            Evaluation data if found, None otherwise
        """
        try:
            cache_file = self.cache_dir / 'quizzes' / f'evaluation_{evaluation_id}.json'
            
            if not cache_file.exists():
                logger.debug(f"Evaluation cache miss: {evaluation_id}")
                return None
            
            json_data = cache_file.read_text(encoding='utf-8')
            data = self._deserialize_data(json_data)
            
            logger.info(f"Evaluation cache hit: {evaluation_id}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to retrieve evaluation {evaluation_id}: {str(e)}")
            return None
    
    def get_quiz_evaluation_by_quiz_id(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve quiz evaluation by quiz_id.
        
        Searches through all evaluation files to find one matching the quiz_id.
        
        Args:
            quiz_id: Quiz identifier
            
        Returns:
            Evaluation data if found, None otherwise
        """
        try:
            quizzes_dir = self.cache_dir / 'quizzes'
            
            if not quizzes_dir.exists():
                return None
            
            # Search through all evaluation files
            for eval_file in quizzes_dir.glob('evaluation_*.json'):
                try:
                    json_data = eval_file.read_text(encoding='utf-8')
                    data = self._deserialize_data(json_data)
                    
                    if data.get("quiz_id") == quiz_id:
                        logger.info(f"Found evaluation for quiz {quiz_id}")
                        return data
                except Exception as e:
                    logger.warning(f"Failed to read evaluation file {eval_file}: {str(e)}")
                    continue
            
            logger.debug(f"No evaluation found for quiz {quiz_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to search for evaluation by quiz_id {quiz_id}: {str(e)}")
            return None


# Global cache service instance
cache_service = CacheService()
