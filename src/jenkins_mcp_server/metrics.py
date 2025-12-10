"""
Metrics and Telemetry Module for Jenkins MCP Server

Tracks tool usage, performance, and errors for monitoring
and optimization purposes.
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolMetric:
    """Single tool execution metric"""
    tool_name: str
    execution_time_ms: float
    success: bool
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    args: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "tool_name": self.tool_name,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "success": self.success,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
            "args": self.args
        }


@dataclass
class ToolStats:
    """Aggregated statistics for a tool"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    
    @property
    def avg_time_ms(self) -> float:
        """Calculate average execution time"""
        if self.total_calls == 0:
            return 0.0
        return self.total_time_ms / self.total_calls
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100
    
    def add_metric(self, metric: ToolMetric) -> None:
        """Add a metric to the statistics"""
        self.total_calls += 1
        self.total_time_ms += metric.execution_time_ms
        
        if metric.success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
        
        self.min_time_ms = min(self.min_time_ms, metric.execution_time_ms)
        self.max_time_ms = max(self.max_time_ms, metric.execution_time_ms)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate_percent": round(self.success_rate, 2),
            "avg_time_ms": round(self.avg_time_ms, 2),
            "min_time_ms": round(self.min_time_ms, 2) if self.min_time_ms != float('inf') else 0,
            "max_time_ms": round(self.max_time_ms, 2),
            "total_time_ms": round(self.total_time_ms, 2)
        }


class MetricsCollector:
    """
    Collects and aggregates metrics for tool executions.
    
    Features:
    - Per-tool statistics
    - Recent execution history
    - Error tracking
    - Performance monitoring
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize metrics collector.
        
        Args:
            max_history: Maximum number of recent metrics to keep
        """
        self.max_history = max_history
        self._metrics: List[ToolMetric] = []
        self._tool_stats: Dict[str, ToolStats] = defaultdict(ToolStats)
        self._lock = asyncio.Lock()
        self._start_time = datetime.now()
        
        logger.info(f"Metrics collector initialized (max_history={max_history})")
    
    async def record_execution(
        self,
        tool_name: str,
        execution_time_ms: float,
        success: bool,
        error_message: Optional[str] = None,
        args: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a tool execution.
        
        Args:
            tool_name: Name of the tool
            execution_time_ms: Execution time in milliseconds
            success: Whether execution was successful
            error_message: Error message if failed
            args: Tool arguments (optional, for debugging)
        """
        metric = ToolMetric(
            tool_name=tool_name,
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message,
            args=args
        )
        
        async with self._lock:
            # Add to history
            self._metrics.append(metric)
            
            # Trim history if needed
            if len(self._metrics) > self.max_history:
                self._metrics = self._metrics[-self.max_history:]
            
            # Update aggregated stats
            self._tool_stats[tool_name].add_metric(metric)
        
        # Log based on result
        if success:
            logger.debug(f"Metric recorded: {tool_name} completed in {execution_time_ms:.2f}ms")
        else:
            logger.warning(f"Metric recorded: {tool_name} failed after {execution_time_ms:.2f}ms - {error_message}")
    
    async def get_tool_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for a specific tool or all tools.
        
        Args:
            tool_name: Specific tool name, or None for all tools
            
        Returns:
            Dictionary with tool statistics
        """
        async with self._lock:
            if tool_name:
                if tool_name not in self._tool_stats:
                    return {
                        "tool_name": tool_name,
                        "stats": ToolStats().to_dict()
                    }
                
                return {
                    "tool_name": tool_name,
                    "stats": self._tool_stats[tool_name].to_dict()
                }
            
            # Return all tools
            return {
                tool_name: stats.to_dict()
                for tool_name, stats in self._tool_stats.items()
            }
    
    async def get_recent_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent metrics.
        
        Args:
            limit: Maximum number of metrics to return
            
        Returns:
            List of recent metrics
        """
        async with self._lock:
            recent = self._metrics[-limit:]
            return [m.to_dict() for m in recent]
    
    async def get_failed_executions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent failed executions.
        
        Args:
            limit: Maximum number of failures to return
            
        Returns:
            List of failed execution metrics
        """
        async with self._lock:
            failures = [m for m in self._metrics if not m.success]
            recent_failures = failures[-limit:]
            return [m.to_dict() for m in recent_failures]
    
    async def get_slow_executions(
        self,
        threshold_ms: float = 1000,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get executions that exceeded a time threshold.
        
        Args:
            threshold_ms: Threshold in milliseconds
            limit: Maximum number of results
            
        Returns:
            List of slow execution metrics
        """
        async with self._lock:
            slow = [
                m for m in self._metrics
                if m.execution_time_ms > threshold_ms
            ]
            recent_slow = slow[-limit:]
            return [m.to_dict() for m in recent_slow]
    
    async def get_summary(self) -> Dict[str, Any]:
        """
        Get overall metrics summary.
        
        Returns:
            Dictionary with summary statistics
        """
        async with self._lock:
            total_executions = len(self._metrics)
            successful = sum(1 for m in self._metrics if m.success)
            failed = total_executions - successful
            
            if total_executions > 0:
                avg_time = sum(m.execution_time_ms for m in self._metrics) / total_executions
                success_rate = (successful / total_executions) * 100
            else:
                avg_time = 0.0
                success_rate = 0.0
            
            uptime = datetime.now() - self._start_time
            
            return {
                "uptime_seconds": uptime.total_seconds(),
                "uptime_human": str(uptime).split('.')[0],  # Remove microseconds
                "total_executions": total_executions,
                "successful_executions": successful,
                "failed_executions": failed,
                "success_rate_percent": round(success_rate, 2),
                "avg_execution_time_ms": round(avg_time, 2),
                "unique_tools_used": len(self._tool_stats),
                "most_used_tool": self._get_most_used_tool(),
                "slowest_tool": self._get_slowest_tool()
            }
    
    def _get_most_used_tool(self) -> Optional[str]:
        """Get the most frequently used tool"""
        if not self._tool_stats:
            return None
        
        return max(
            self._tool_stats.items(),
            key=lambda x: x[1].total_calls
        )[0]
    
    def _get_slowest_tool(self) -> Optional[str]:
        """Get the tool with highest average execution time"""
        if not self._tool_stats:
            return None
        
        return max(
            self._tool_stats.items(),
            key=lambda x: x[1].avg_time_ms
        )[0]
    
    async def reset(self) -> None:
        """Reset all metrics"""
        async with self._lock:
            self._metrics.clear()
            self._tool_stats.clear()
            self._start_time = datetime.now()
            logger.info("Metrics reset")
    
    async def export_metrics(self) -> Dict[str, Any]:
        """
        Export all metrics data.
        
        Returns:
            Complete metrics export
        """
        async with self._lock:
            return {
                "summary": await self.get_summary(),
                "tool_stats": await self.get_tool_stats(),
                "recent_metrics": await self.get_recent_metrics(limit=100),
                "failed_executions": await self.get_failed_executions(limit=50),
                "slow_executions": await self.get_slow_executions(threshold_ms=1000, limit=50)
            }


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


# Convenience functions
async def record_tool_execution(
    tool_name: str,
    execution_time_ms: float,
    success: bool,
    error_message: Optional[str] = None,
    args: Optional[Dict[str, Any]] = None
) -> None:
    """Record a tool execution"""
    await get_metrics_collector().record_execution(
        tool_name,
        execution_time_ms,
        success,
        error_message,
        args
    )


async def get_metrics_summary() -> Dict[str, Any]:
    """Get metrics summary"""
    return await get_metrics_collector().get_summary()


async def get_tool_metrics(tool_name: Optional[str] = None) -> Dict[str, Any]:
    """Get tool-specific metrics"""
    return await get_metrics_collector().get_tool_stats(tool_name)
