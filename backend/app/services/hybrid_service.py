"""
backend/app/services/hybrid_service.py
======================================
Singleton provider for HybridScorer serving instance.
Imports recommender.serving.hybrid_scorer directly (no duplicate copy).
"""

from typing import Optional
from app.core.config import settings
from recommender.serving.hybrid_scorer import HybridScorer

_scorer_instance: Optional[HybridScorer] = None


def get_hybrid_scorer() -> HybridScorer:
    """Return the global HybridScorer singleton instance."""
    global _scorer_instance
    if _scorer_instance is None:
        artifacts_path = settings.model_artifacts_path
        _scorer_instance = HybridScorer(artifacts_dir=artifacts_path)
    return _scorer_instance
