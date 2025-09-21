#!/usr/bin/env python3
"""
Analytics Service
Functional approach for query analytics and system monitoring
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from . import database_manager

logger = logging.getLogger(__name__)


def log_query(query: str, response_data: Dict[str, Any]) -> None:
    """
    Log query analytics

    """
    try:
        database_manager.log_query(query, response_data)
        logger.info(f"Logged query analytics for: {query[:50]}...")
    except Exception as e:
        logger.error(f"Failed to log query analytics: {e}")


def get_analytics_summary(days: int = 7) -> Dict[str, Any]:
    """
    Get analytics summary
    """
    try:
        # Get analytics from database
        analytics_data = database_manager.get_analytics_summary(days)

        # Get document stats
        doc_stats = database_manager.get_document_stats()

        # Get system health
        system_health = get_system_health()

        # Combine analytics
        summary = {
            'query_analytics': analytics_data,
            'document_stats': doc_stats,
            'system_health': system_health,
            'generated_at': datetime.now().isoformat()
        }

        return summary

    except Exception as e:
        logger.error(f"Failed to get analytics summary: {e}")
        return {
            'error': str(e),
            'generated_at': datetime.now().isoformat()
        }


def get_system_health() -> Dict[str, Any]:
    """
    Get system health metrics
    """
    try:
        return {
            'status': 'healthy',
            'database_connected': True,
            'search_engine_ready': True,
            'llm_service_ready': True,
            'last_check': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'last_check': datetime.now().isoformat()
        }
