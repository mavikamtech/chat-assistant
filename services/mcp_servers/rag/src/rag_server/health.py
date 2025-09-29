"""Health check and monitoring utilities for RAG MCP server."""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import aiohttp

from mavik_common.errors import OpenSearchError, ValidationError
from .vector_search import VectorSearchService

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitor health of RAG MCP server components."""
    
    def __init__(
        self,
        vector_search: VectorSearchService,
        check_interval_seconds: int = 60,
    ):
        """Initialize health monitor.
        
        Args:
            vector_search: Vector search service to monitor
            check_interval_seconds: How often to run health checks
        """
        self.vector_search = vector_search
        self.check_interval = check_interval_seconds
        self.last_check = None
        self.health_history: List[Dict[str, Any]] = []
        self.max_history = 100  # Keep last 100 health checks
    
    async def run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check."""
        
        check_time = datetime.utcnow()
        health_result = {
            "timestamp": check_time.isoformat(),
            "overall_status": "healthy",
            "components": {},
            "performance": {},
        }
        
        try:
            # Check vector search service
            search_health = await self._check_vector_search()
            health_result["components"]["vector_search"] = search_health
            
            # Check OpenSearch performance
            performance = await self._check_performance()
            health_result["performance"] = performance
            
            # Determine overall status
            component_statuses = [
                comp.get("status", "unhealthy") 
                for comp in health_result["components"].values()
            ]
            
            if all(status == "healthy" for status in component_statuses):
                health_result["overall_status"] = "healthy"
            elif any(status == "degraded" for status in component_statuses):
                health_result["overall_status"] = "degraded"
            else:
                health_result["overall_status"] = "unhealthy"
            
            self.last_check = check_time
            
            # Store in history
            self._add_to_history(health_result)
            
            logger.info(f"Health check completed: {health_result['overall_status']}")
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_result["overall_status"] = "unhealthy"
            health_result["error"] = str(e)
        
        return health_result
    
    async def _check_vector_search(self) -> Dict[str, Any]:
        """Check vector search service health."""
        
        try:
            # Use the service's built-in health check
            search_health = await self.vector_search.health_check()
            
            if search_health.get("opensearch_healthy", False):
                status = "healthy"
            else:
                status = "unhealthy"
            
            return {
                "status": status,
                "details": search_health,
            }
            
        except Exception as e:
            logger.error(f"Vector search health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }
    
    async def _check_performance(self) -> Dict[str, Any]:
        """Check system performance metrics."""
        
        performance = {
            "search_latency_ms": None,
            "index_size_mb": None,
            "document_count": None,
        }
        
        try:
            # Test search latency with simple query
            start_time = datetime.utcnow()
            
            from mavik_common.models import RAGSearchRequest
            test_request = RAGSearchRequest(
                query="test health check query",
                limit=1,
                use_vector_search=False,  # Use text search only for speed
                use_text_search=True,
            )
            
            try:
                await asyncio.wait_for(
                    self.vector_search.search_documents(test_request),
                    timeout=5.0  # 5 second timeout
                )
                
                latency = (datetime.utcnow() - start_time).total_seconds() * 1000
                performance["search_latency_ms"] = round(latency, 2)
                
            except asyncio.TimeoutError:
                performance["search_latency_ms"] = "timeout"
            except Exception as e:
                logger.warning(f"Search latency test failed: {e}")
                performance["search_latency_ms"] = "error"
            
            # Get index statistics
            try:
                opensearch_client = self.vector_search.opensearch_client
                index_name = self.vector_search.index_name
                
                if await opensearch_client.client.indices.exists(index=index_name):
                    stats = await opensearch_client.client.indices.stats(index=index_name)
                    index_stats = stats["indices"][index_name]["total"]
                    
                    performance["document_count"] = index_stats["docs"]["count"]
                    performance["index_size_mb"] = round(
                        index_stats["store"]["size_in_bytes"] / (1024 * 1024), 2
                    )
                
            except Exception as e:
                logger.warning(f"Index stats retrieval failed: {e}")
        
        except Exception as e:
            logger.error(f"Performance check failed: {e}")
        
        return performance
    
    def _add_to_history(self, health_result: Dict[str, Any]) -> None:
        """Add health result to history."""
        
        # Add to history
        self.health_history.append(health_result)
        
        # Trim history if too long
        if len(self.health_history) > self.max_history:
            self.health_history = self.health_history[-self.max_history:]
    
    def get_health_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get health summary for the last N hours."""
        
        if not self.health_history:
            return {
                "summary": "No health data available",
                "period_hours": hours,
            }
        
        # Filter history by time period
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_checks = [
            check for check in self.health_history
            if datetime.fromisoformat(check["timestamp"]) > cutoff_time
        ]
        
        if not recent_checks:
            return {
                "summary": f"No health data available for last {hours} hours",
                "period_hours": hours,
            }
        
        # Calculate summary statistics
        total_checks = len(recent_checks)
        healthy_checks = sum(
            1 for check in recent_checks 
            if check.get("overall_status") == "healthy"
        )
        degraded_checks = sum(
            1 for check in recent_checks 
            if check.get("overall_status") == "degraded"
        )
        unhealthy_checks = total_checks - healthy_checks - degraded_checks
        
        # Get latest performance metrics
        latest_check = recent_checks[-1]
        latest_performance = latest_check.get("performance", {})
        
        # Calculate uptime percentage
        uptime_percentage = (healthy_checks + degraded_checks) / total_checks * 100
        
        return {
            "period_hours": hours,
            "total_checks": total_checks,
            "uptime_percentage": round(uptime_percentage, 2),
            "status_distribution": {
                "healthy": healthy_checks,
                "degraded": degraded_checks,
                "unhealthy": unhealthy_checks,
            },
            "latest_performance": latest_performance,
            "first_check": recent_checks[0]["timestamp"],
            "last_check": recent_checks[-1]["timestamp"],
        }
    
    async def start_monitoring(self) -> None:
        """Start continuous health monitoring."""
        
        logger.info(f"Starting health monitoring (interval: {self.check_interval}s)")
        
        while True:
            try:
                await self.run_health_check()
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                logger.info("Health monitoring stopped")
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(min(self.check_interval, 30))  # Back off on errors


class AlertManager:
    """Manage alerts for RAG MCP server issues."""
    
    def __init__(
        self,
        webhook_url: Optional[str] = None,
        alert_thresholds: Optional[Dict[str, Any]] = None,
    ):
        """Initialize alert manager.
        
        Args:
            webhook_url: Optional webhook URL for sending alerts
            alert_thresholds: Thresholds for triggering alerts
        """
        self.webhook_url = webhook_url
        self.thresholds = alert_thresholds or {
            "max_search_latency_ms": 5000,
            "min_uptime_percentage": 95.0,
            "max_consecutive_failures": 3,
        }
        self.consecutive_failures = 0
        self.last_alert_time = {}
        self.min_alert_interval_minutes = 15  # Minimum time between same alert types
    
    async def check_alerts(self, health_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check if any alerts should be triggered."""
        
        alerts = []
        current_time = datetime.utcnow()
        
        try:
            # Check overall status
            overall_status = health_result.get("overall_status", "unknown")
            
            if overall_status == "unhealthy":
                self.consecutive_failures += 1
                
                if self.consecutive_failures >= self.thresholds["max_consecutive_failures"]:
                    alert = {
                        "type": "consecutive_failures",
                        "severity": "critical",
                        "message": f"Service unhealthy for {self.consecutive_failures} consecutive checks",
                        "details": health_result,
                        "timestamp": current_time.isoformat(),
                    }
                    
                    if self._should_send_alert("consecutive_failures", current_time):
                        alerts.append(alert)
            else:
                self.consecutive_failures = 0  # Reset on recovery
            
            # Check search latency
            performance = health_result.get("performance", {})
            search_latency = performance.get("search_latency_ms")
            
            if (
                isinstance(search_latency, (int, float)) and
                search_latency > self.thresholds["max_search_latency_ms"]
            ):
                alert = {
                    "type": "high_latency",
                    "severity": "warning",
                    "message": f"Search latency high: {search_latency}ms",
                    "details": {"latency_ms": search_latency},
                    "timestamp": current_time.isoformat(),
                }
                
                if self._should_send_alert("high_latency", current_time):
                    alerts.append(alert)
            
            # Send alerts if webhook configured
            if alerts and self.webhook_url:
                await self._send_webhook_alerts(alerts)
            
        except Exception as e:
            logger.error(f"Alert checking failed: {e}")
        
        return alerts
    
    def _should_send_alert(self, alert_type: str, current_time: datetime) -> bool:
        """Check if enough time has passed to send this alert type."""
        
        last_sent = self.last_alert_time.get(alert_type)
        if not last_sent:
            self.last_alert_time[alert_type] = current_time
            return True
        
        time_diff = (current_time - last_sent).total_seconds() / 60  # minutes
        
        if time_diff >= self.min_alert_interval_minutes:
            self.last_alert_time[alert_type] = current_time
            return True
        
        return False
    
    async def _send_webhook_alerts(self, alerts: List[Dict[str, Any]]) -> None:
        """Send alerts via webhook."""
        
        try:
            async with aiohttp.ClientSession() as session:
                for alert in alerts:
                    payload = {
                        "text": f"RAG MCP Alert: {alert['message']}",
                        "alert": alert,
                    }
                    
                    async with session.post(
                        self.webhook_url,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            logger.info(f"Alert sent successfully: {alert['type']}")
                        else:
                            logger.warning(f"Failed to send alert: {response.status}")
        
        except Exception as e:
            logger.error(f"Failed to send webhook alerts: {e}")


# Utility functions for health endpoints
async def get_detailed_health_status(
    vector_search: VectorSearchService,
    include_history: bool = False,
) -> Dict[str, Any]:
    """Get detailed health status for API responses."""
    
    try:
        # Create temporary health monitor for this check
        monitor = HealthMonitor(vector_search)
        health_result = await monitor.run_health_check()
        
        if include_history:
            health_result["history_summary"] = monitor.get_health_summary(hours=1)
        
        return health_result
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "unhealthy",
            "error": str(e),
        }