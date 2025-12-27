"""
Analytics and Telemetry Service.

This service tracks:
- Query counts and patterns
- Token usage estimates
- Document access patterns
- No-answer frequency
- Latency distribution
- User activity
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Metrics for a single query."""
    query: str
    user_id: int
    project_id: Optional[int]
    timestamp: datetime
    latency_ms: float
    tokens_used: int
    sources_count: int
    confidence_score: float
    is_no_answer: bool


@dataclass
class DocumentMetrics:
    """Metrics for document access."""
    document_id: int
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    avg_relevance_score: float = 0.0


class AnalyticsService:
    """
    Analytics service for tracking platform usage and performance.
    
    Provides:
    - Real-time query metrics
    - Historical trends
    - Knowledge gap analysis
    - Performance monitoring
    """
    
    def __init__(self):
        """Initialize analytics service."""
        self._lock = Lock()
        self._enabled = settings.ENABLE_ANALYTICS
        
        # In-memory metrics storage (would use Redis/DB in production)
        self._query_metrics: List[QueryMetrics] = []
        self._document_metrics: Dict[int, DocumentMetrics] = defaultdict(lambda: DocumentMetrics(document_id=0))
        self._hourly_query_counts: Dict[str, int] = defaultdict(int)
        self._no_answer_queries: List[str] = []
        
        # Aggregated statistics
        self._total_queries = 0
        self._total_tokens = 0
        self._total_latency_ms = 0
        
        logger.info(f"Analytics service initialized. Enabled: {self._enabled}")
    
    def track_query(
        self,
        query: str,
        user_id: int,
        project_id: Optional[int],
        latency_ms: float,
        tokens_used: int,
        sources_count: int,
        confidence_score: float,
        is_no_answer: bool = False
    ):
        """
        Track a query for analytics.
        
        Args:
            query: The user's query text
            user_id: ID of the user
            project_id: Project scope (if any)
            latency_ms: Query processing time in milliseconds
            tokens_used: Estimated tokens consumed
            sources_count: Number of source documents used
            confidence_score: AI confidence in the answer
            is_no_answer: Whether the AI couldn't find an answer
        """
        if not self._enabled:
            return
        
        try:
            with self._lock:
                timestamp = datetime.utcnow()
                
                # Create metric record
                metric = QueryMetrics(
                    query=query[:200],  # Truncate long queries
                    user_id=user_id,
                    project_id=project_id,
                    timestamp=timestamp,
                    latency_ms=latency_ms,
                    tokens_used=tokens_used,
                    sources_count=sources_count,
                    confidence_score=confidence_score,
                    is_no_answer=is_no_answer
                )
                
                # Store metric
                self._query_metrics.append(metric)
                
                # Update aggregates
                self._total_queries += 1
                self._total_tokens += tokens_used
                self._total_latency_ms += latency_ms
                
                # Track hourly counts
                hour_key = timestamp.strftime("%Y-%m-%d-%H")
                self._hourly_query_counts[hour_key] += 1
                
                # Track no-answer queries for knowledge gap analysis
                if is_no_answer:
                    self._no_answer_queries.append(query[:200])
                
                # Cleanup old data
                self._cleanup_old_metrics()
                
        except Exception as e:
            logger.error(f"Error tracking query: {e}")
    
    def track_document_access(
        self,
        document_id: int,
        relevance_score: float
    ):
        """
        Track document access for analytics.
        
        Args:
            document_id: ID of the accessed document
            relevance_score: How relevant the document was (0-1)
        """
        if not self._enabled:
            return
        
        try:
            with self._lock:
                metrics = self._document_metrics[document_id]
                metrics.document_id = document_id
                metrics.access_count += 1
                metrics.last_accessed = datetime.utcnow()
                
                # Update rolling average relevance
                if metrics.avg_relevance_score == 0:
                    metrics.avg_relevance_score = relevance_score
                else:
                    # Exponential moving average
                    metrics.avg_relevance_score = (
                        0.7 * metrics.avg_relevance_score + 
                        0.3 * relevance_score
                    )
                    
        except Exception as e:
            logger.error(f"Error tracking document access: {e}")
    
    def _cleanup_old_metrics(self):
        """Remove metrics older than retention period."""
        cutoff = datetime.utcnow() - timedelta(days=settings.ANALYTICS_RETENTION_DAYS)
        
        # Remove old query metrics
        self._query_metrics = [
            m for m in self._query_metrics
            if m.timestamp > cutoff
        ]
        
        # Remove old hourly counts
        cutoff_hour = cutoff.strftime("%Y-%m-%d-%H")
        self._hourly_query_counts = {
            k: v for k, v in self._hourly_query_counts.items()
            if k >= cutoff_hour
        }
        
        # Limit no-answer queries list
        if len(self._no_answer_queries) > 1000:
            self._no_answer_queries = self._no_answer_queries[-500:]
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """
        Get metrics for admin dashboard.
        
        Returns:
            Dict with various analytics metrics
        """
        try:
            with self._lock:
                now = datetime.utcnow()
                day_ago = now - timedelta(days=1)
                week_ago = now - timedelta(days=7)
                
                # Filter recent metrics
                day_metrics = [m for m in self._query_metrics if m.timestamp > day_ago]
                week_metrics = [m for m in self._query_metrics if m.timestamp > week_ago]
                
                # Calculate statistics
                avg_latency = (
                    sum(m.latency_ms for m in day_metrics) / len(day_metrics)
                    if day_metrics else 0
                )
                
                p95_latency = self._calculate_percentile(
                    [m.latency_ms for m in day_metrics], 95
                )
                
                no_answer_rate = (
                    sum(1 for m in day_metrics if m.is_no_answer) / len(day_metrics)
                    if day_metrics else 0
                )
                
                avg_confidence = (
                    sum(m.confidence_score for m in day_metrics) / len(day_metrics)
                    if day_metrics else 0
                )
                
                # Get top documents
                top_documents = sorted(
                    self._document_metrics.values(),
                    key=lambda d: d.access_count,
                    reverse=True
                )[:10]
                
                # Get unique users
                unique_users_day = len(set(m.user_id for m in day_metrics))
                unique_users_week = len(set(m.user_id for m in week_metrics))
                
                return {
                    "summary": {
                        "total_queries": self._total_queries,
                        "total_tokens_estimated": self._total_tokens,
                        "queries_today": len(day_metrics),
                        "queries_this_week": len(week_metrics),
                        "unique_users_today": unique_users_day,
                        "unique_users_this_week": unique_users_week
                    },
                    "performance": {
                        "avg_latency_ms": round(avg_latency, 2),
                        "p95_latency_ms": round(p95_latency, 2),
                        "avg_confidence": round(avg_confidence, 3),
                        "no_answer_rate": round(no_answer_rate * 100, 2)
                    },
                    "top_documents": [
                        {
                            "document_id": d.document_id,
                            "access_count": d.access_count,
                            "avg_relevance": round(d.avg_relevance_score, 3)
                        }
                        for d in top_documents
                    ],
                    "hourly_trend": self._get_hourly_trend(24),
                    "knowledge_gaps": self._get_knowledge_gaps()
                }
                
        except Exception as e:
            logger.error(f"Error getting dashboard metrics: {e}")
            return {"error": str(e)}
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def _get_hourly_trend(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly query counts for trending."""
        trend = []
        now = datetime.utcnow()
        
        for i in range(hours):
            hour = now - timedelta(hours=i)
            hour_key = hour.strftime("%Y-%m-%d-%H")
            count = self._hourly_query_counts.get(hour_key, 0)
            trend.append({
                "hour": hour.strftime("%H:00"),
                "date": hour.strftime("%Y-%m-%d"),
                "count": count
            })
        
        return list(reversed(trend))
    
    def _get_knowledge_gaps(self) -> List[Dict[str, Any]]:
        """
        Identify knowledge gaps from no-answer queries.
        
        Returns frequently asked questions that couldn't be answered.
        """
        if not self._no_answer_queries:
            return []
        
        # Simple frequency analysis (would use NLP clustering in production)
        query_counts = defaultdict(int)
        for query in self._no_answer_queries:
            # Normalize query
            normalized = query.lower().strip()[:100]
            query_counts[normalized] += 1
        
        # Get top unanswered queries
        gaps = sorted(
            [{"query": q, "frequency": c} for q, c in query_counts.items()],
            key=lambda x: x["frequency"],
            reverse=True
        )[:20]
        
        return gaps
    
    def get_user_activity(self, user_id: int) -> Dict[str, Any]:
        """Get activity metrics for a specific user."""
        try:
            with self._lock:
                user_metrics = [m for m in self._query_metrics if m.user_id == user_id]
                
                if not user_metrics:
                    return {"queries": 0, "recent_queries": []}
                
                return {
                    "total_queries": len(user_metrics),
                    "avg_confidence": sum(m.confidence_score for m in user_metrics) / len(user_metrics),
                    "tokens_used": sum(m.tokens_used for m in user_metrics),
                    "recent_queries": [
                        {
                            "query": m.query,
                            "timestamp": m.timestamp.isoformat(),
                            "confidence": m.confidence_score
                        }
                        for m in sorted(user_metrics, key=lambda x: x.timestamp, reverse=True)[:10]
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error getting user activity: {e}")
            return {"error": str(e)}
    
    def get_project_analytics(self, project_id: int) -> Dict[str, Any]:
        """Get analytics for a specific project."""
        try:
            with self._lock:
                project_metrics = [
                    m for m in self._query_metrics 
                    if m.project_id == project_id
                ]
                
                if not project_metrics:
                    return {"queries": 0}
                
                return {
                    "total_queries": len(project_metrics),
                    "unique_users": len(set(m.user_id for m in project_metrics)),
                    "avg_confidence": sum(m.confidence_score for m in project_metrics) / len(project_metrics),
                    "no_answer_rate": sum(1 for m in project_metrics if m.is_no_answer) / len(project_metrics)
                }
                
        except Exception as e:
            logger.error(f"Error getting project analytics: {e}")
            return {"error": str(e)}
    
    def is_enabled(self) -> bool:
        """Check if analytics is enabled."""
        return self._enabled


# Global instance
analytics_service = AnalyticsService()

