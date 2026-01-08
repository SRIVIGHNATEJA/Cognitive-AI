"""
Analytics API Router for the Cognitive AI Learning Platform.

Provides endpoints for retrieving learning analytics, progress tracking, and weak area identification.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any

from app.models import (
    AnalyticsOverviewResponse,
    ModuleProgress,
    WeakAreasResponse,
    Module
)
from app.services.analytics_service import AnalyticsService
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Service instances
analytics_service = AnalyticsService()
cache_service = CacheService()


def _get_module_from_roadmap(module_id: str) -> Module:
    """
    Helper function to get module details from cached roadmap.
    
    Args:
        module_id: Module identifier
        
    Returns:
        Module object
        
    Raises:
        HTTPException 404: If roadmap or module not found
    """
    # Get cached roadmap
    roadmap_data = cache_service.get_cached_roadmap()
    if not roadmap_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No roadmap found. Please generate a roadmap first."
        )
    
    # Find the module
    modules = roadmap_data.get("modules", [])
    for module_data in modules:
        if module_data.get("module_id") == module_id:
            return Module(**module_data)
    
    # Module not found
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Module '{module_id}' not found in roadmap."
    )


@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def get_analytics_overview() -> AnalyticsOverviewResponse:
    """
    Get overall analytics overview.
    
    Returns comprehensive analytics including:
    - Overall progress percentage
    - Number of completed modules
    - Average quiz accuracy
    - Progress for each module
    
    Returns:
        AnalyticsOverviewResponse with complete analytics data
        
    Raises:
        HTTPException 404: If no roadmap found
        HTTPException 500: If analytics calculation fails
    """
    try:
        logger.info("Fetching analytics overview")
        
        # Get roadmap
        roadmap_data = cache_service.get_cached_roadmap()
        if not roadmap_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No roadmap found. Please generate a roadmap first."
            )
        
        # Calculate analytics
        overall_progress = analytics_service.calculate_overall_progress()
        modules_completed = analytics_service.count_completed_modules(threshold=100.0)
        total_modules = len(roadmap_data.get("modules", []))
        average_quiz_accuracy = analytics_service.calculate_average_quiz_accuracy()
        module_progress = analytics_service.get_all_module_progress()
        
        logger.info(
            f"Analytics overview: {overall_progress:.1f}% progress, "
            f"{modules_completed}/{total_modules} modules completed"
        )
        
        return AnalyticsOverviewResponse(
            success=True,
            overall_progress=overall_progress,
            modules_completed=modules_completed,
            total_modules=total_modules,
            average_quiz_accuracy=average_quiz_accuracy,
            module_progress=module_progress
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analytics overview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate analytics: {str(e)}"
        )


@router.get("/module/{module_id}", response_model=ModuleProgress)
async def get_module_analytics(module_id: str) -> ModuleProgress:
    """
    Get analytics for a specific module.
    
    Returns detailed progress tracking for a single module including:
    - Completion percentage
    - Number of quizzes taken
    - Average quiz accuracy
    
    Args:
        module_id: Module identifier
        
    Returns:
        ModuleProgress with module-specific analytics
        
    Raises:
        HTTPException 404: If module not found
        HTTPException 500: If analytics calculation fails
    """
    try:
        logger.info(f"Fetching analytics for module '{module_id}'")
        
        # Validate module exists
        module = _get_module_from_roadmap(module_id)
        
        # Get module progress
        progress = analytics_service.get_module_progress(module_id, module.topic_name)
        
        logger.info(
            f"Module '{module_id}' analytics: {progress.completion_percentage:.1f}% complete, "
            f"{progress.quizzes_taken} quizzes, {progress.average_accuracy:.1f}% accuracy"
        )
        
        return progress
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get module analytics for '{module_id}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate module analytics: {str(e)}"
        )


@router.get("/weak-areas", response_model=WeakAreasResponse)
async def get_weak_areas() -> WeakAreasResponse:
    """
    Identify weak areas based on quiz performance.
    
    Returns modules where quiz accuracy is below 60% threshold,
    along with recommendations for improvement.
    
    Returns:
        WeakAreasResponse with weak modules and recommendations
        
    Raises:
        HTTPException 404: If no roadmap found
        HTTPException 500: If weak area identification fails
    """
    try:
        logger.info("Identifying weak areas")
        
        # Get roadmap
        roadmap_data = cache_service.get_cached_roadmap()
        if not roadmap_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No roadmap found. Please generate a roadmap first."
            )
        
        # Identify weak areas (60% threshold)
        threshold = 60.0
        weak_module_ids = analytics_service.identify_weak_areas(threshold=threshold)
        
        # Build detailed weak module information
        weak_modules = []
        recommendations = []
        
        for module_id in weak_module_ids:
            # Get module details
            module = _get_module_from_roadmap(module_id)
            
            # Get quiz metrics
            metrics = analytics_service.aggregate_quiz_metrics(module_id)
            
            weak_modules.append({
                "module_id": module_id,
                "topic_name": module.topic_name,
                "average_accuracy": metrics.get("average_accuracy", 0.0),
                "quizzes_taken": metrics.get("total_quizzes", 0)
            })
            
            # Generate recommendations
            recommendations.append(f"Review notes for '{module.topic_name}'")
            recommendations.append(f"Retake quizzes for '{module.topic_name}' to improve understanding")
        
        logger.info(f"Identified {len(weak_modules)} weak areas")
        
        return WeakAreasResponse(
            success=True,
            weak_modules=weak_modules,
            recommendations=recommendations,
            threshold=threshold
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to identify weak areas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to identify weak areas: {str(e)}"
        )
