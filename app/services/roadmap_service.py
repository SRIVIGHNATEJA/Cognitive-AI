"""
Roadmap Service for the Cognitive AI Learning Platform.

Handles roadmap generation, module ID stability, and prerequisite validation.
Integrates with LLM service for roadmap generation and cache service for persistence.
"""

import hashlib
import logging
from typing import List, Dict, Optional
from datetime import datetime

from app.models import Module, LearningMode
from app.services.llm_service import LLMService
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class RoadmapService:
    """
    Service for generating and managing learning roadmaps.
    
    Responsibilities:
    - Generate roadmaps from input content using LLM
    - Assign stable module IDs
    - Validate module prerequisites
    - Integrate with cache for persistence
    """
    
    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        cache_service: Optional[CacheService] = None
    ):
        """
        Initialize the roadmap service.
        
        Args:
            llm_service: LLM service instance for roadmap generation
            cache_service: Cache service instance for persistence
        """
        self.llm_service = llm_service or LLMService()
        self.cache_service = cache_service or CacheService()
        logger.info("RoadmapService initialized")
    
    def generate_stable_module_id(self, topic_name: str, order: int) -> str:
        """
        Generate a stable, unique module ID based on topic name and order.
        
        The same topic name and order will always produce the same module_id,
        ensuring stability across sessions.
        
        Args:
            topic_name: Name of the module topic
            order: Sequential order of the module
            
        Returns:
            Stable module ID string
            
        Example:
            >>> service = RoadmapService()
            >>> service.generate_stable_module_id("Python Basics", 1)
            'mod_a1b2c3d4e5f6'
        """
        # Create a deterministic hash from topic name and order
        content = f"{topic_name.lower().strip()}_{order}"
        hash_obj = hashlib.sha256(content.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()[:12]  # Use first 12 characters
        
        module_id = f"mod_{hash_hex}"
        logger.debug(f"Generated module_id '{module_id}' for topic '{topic_name}' (order {order})")
        
        return module_id
    
    def map_prerequisites_to_module_ids(self, modules: List[Module]) -> List[Module]:
        """
        Map topic-name prerequisites to module IDs.
        
        This function handles the mismatch between LLM output (topic names) and
        validation requirements (module IDs). The LLM is instructed to use topic
        names in prerequisites, but module IDs are generated after LLM output.
        
        This is a design alignment fix to bridge the gap between prompt instructions
        and validation logic.
        
        Args:
            modules: List of modules with topic-name prerequisites
            
        Returns:
            List of modules with mapped module_id prerequisites
        """
        # Build topic_name -> module_id mapping (case-insensitive)
        topic_to_id = {}
        for module in modules:
            key = module.topic_name.lower().strip()
            topic_to_id[key] = module.module_id
        
        logger.debug(f"Built topic-to-ID mapping for {len(topic_to_id)} modules")
        
        # Transform prerequisites from topic names to module IDs
        for module in modules:
            mapped_prereqs = []
            
            for prereq in module.prerequisites:
                prereq_key = prereq.lower().strip()
                
                if prereq_key in topic_to_id:
                    # Exact match found
                    mapped_id = topic_to_id[prereq_key]
                    
                    # Don't add self-references
                    if mapped_id != module.module_id:
                        mapped_prereqs.append(mapped_id)
                        logger.debug(
                            f"Mapped prerequisite '{prereq}' -> '{mapped_id}' "
                            f"for module '{module.topic_name}'"
                        )
                    else:
                        logger.warning(
                            f"Skipping self-reference prerequisite '{prereq}' "
                            f"for module '{module.topic_name}'"
                        )
                else:
                    # No match - log warning and skip
                    logger.warning(
                        f"Could not map prerequisite '{prereq}' for module "
                        f"'{module.topic_name}'. Skipping."
                    )
            
            # Update module with mapped prerequisites
            module.prerequisites = mapped_prereqs
        
        logger.info(f"Prerequisite mapping complete for {len(modules)} modules")
        return modules
    
    def validate_module_prerequisites(self, modules: List[Module]) -> bool:
        """
        Validate that all module prerequisites reference valid module IDs.
        
        Args:
            modules: List of modules to validate
            
        Returns:
            True if all prerequisites are valid, False otherwise
            
        Raises:
            ValueError: If invalid prerequisites are found
        """
        # Build set of valid module IDs
        valid_module_ids = {module.module_id for module in modules}
        
        # Check each module's prerequisites
        for module in modules:
            for prereq_id in module.prerequisites:
                if prereq_id not in valid_module_ids:
                    error_msg = (
                        f"Module '{module.module_id}' has invalid prerequisite '{prereq_id}'. "
                        f"Valid module IDs: {valid_module_ids}"
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)
        
        logger.debug(f"All prerequisites validated for {len(modules)} modules")
        return True
    
    def generate_roadmap(
        self,
        input_text: str,
        mode: LearningMode,
        input_id: str
    ) -> List[Module]:
        """
        Generate a learning roadmap from input content.
        
        This method:
        1. Calls LLM service to generate roadmap structure
        2. Assigns stable module IDs to each module
        3. Validates prerequisites
        4. Returns list of Module objects
        
        Args:
            input_text: Extracted educational content
            mode: Learning mode (timed or untimed)
            input_id: ID of the input being processed
            
        Returns:
            List of Module objects with stable IDs
            
        Raises:
            ValueError: If roadmap generation fails or validation fails
            RuntimeError: If LLM service fails
        """
        logger.info(f"Generating roadmap for input_id '{input_id}' in {mode} mode")
        
        try:
            # Call LLM service to generate roadmap
            llm_response = self.llm_service.generate_roadmap_llm(
                input_text=input_text,
                mode=mode.value
            )
            
            # Extract modules from LLM response
            if not llm_response or "modules" not in llm_response:
                raise ValueError("LLM response missing 'modules' field")
            
            raw_modules = llm_response["modules"]
            
            if not raw_modules:
                raise ValueError("LLM generated empty roadmap")
            
            logger.info(f"LLM generated {len(raw_modules)} modules")
            
            # Convert to Module objects with stable IDs
            modules = []
            for raw_module in raw_modules:
                # Generate stable module ID
                module_id = self.generate_stable_module_id(
                    topic_name=raw_module["topic_name"],
                    order=raw_module["order"]
                )
                
                # Create Module object
                module = Module(
                    module_id=module_id,
                    topic_name=raw_module["topic_name"],
                    estimated_hours=raw_module["estimated_hours"],
                    prerequisites=raw_module.get("prerequisites", []),
                    order=raw_module["order"]
                )
                modules.append(module)
            
            # Map topic-name prerequisites to module IDs
            # This aligns LLM output (topic names) with validation requirements (module IDs)
            modules = self.map_prerequisites_to_module_ids(modules)
            
            # Validate prerequisites (now with module IDs)
            self.validate_module_prerequisites(modules)
            
            logger.info(f"Successfully generated roadmap with {len(modules)} modules")
            return modules
            
        except Exception as e:
            logger.error(f"Failed to generate roadmap: {str(e)}")
            raise
