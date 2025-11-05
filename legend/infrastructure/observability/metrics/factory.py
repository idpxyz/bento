"""
Metrics recorder factory module.
"""

from enum import Enum
from typing import Dict, Optional, Type, Union

from ..core.config import MetricsConfig, PostgresMetricsConfig
from .memory_recorder import MemoryMetricsRecorder
from .postgres import PostgresMetricsRecorder
from .prometheus_recorder import PrometheusMetricsRecorder
from .recorder import BaseMetricsRecorder


class MetricsRecorderType(str, Enum):
    """Metrics recorder type enumeration."""
    
    MEMORY = "MEMORY"
    PROMETHEUS = "PROMETHEUS"
    POSTGRES = "POSTGRES"


class MetricsRecorderFactory:
    """Factory for creating metrics recorders."""
    
    _recorder_classes: Dict[str, Type[BaseMetricsRecorder]] = {
        MetricsRecorderType.MEMORY: MemoryMetricsRecorder,
        MetricsRecorderType.PROMETHEUS: PrometheusMetricsRecorder,
        MetricsRecorderType.POSTGRES: PostgresMetricsRecorder,
    }

    @classmethod
    def register_recorder(cls, recorder_type: str, recorder_class: Type[BaseMetricsRecorder]) -> None:
        """Register a new recorder class.
        
        Args:
            recorder_type: Type identifier for the recorder
            recorder_class: Recorder class to register
        """
        cls._recorder_classes[recorder_type] = recorder_class

    @classmethod
    def create(
        cls,
        recorder_type: Union[str, MetricsRecorderType],
        config: MetricsConfig,
    ) -> BaseMetricsRecorder:
        """Create a metrics recorder instance.
        
        Args:
            recorder_type: Type of recorder to create
            config: Metrics configuration
            
        Returns:
            Configured metrics recorder instance
            
        Raises:
            ValueError: If recorder type is invalid or required config is missing
        """
        # Normalize recorder type
        if isinstance(recorder_type, str):
            try:
                recorder_type = MetricsRecorderType(recorder_type.upper())
            except ValueError:
                raise ValueError(f"Invalid recorder type: {recorder_type}")

        # Get recorder class
        recorder_class = cls._recorder_classes.get(recorder_type)
        if not recorder_class:
            raise ValueError(f"No recorder registered for type: {recorder_type}")

        # Create recorder instance based on type
        if recorder_type == MetricsRecorderType.POSTGRES:
            if not config.postgres:
                raise ValueError("PostgreSQL configuration required for POSTGRES recorder type")
            return recorder_class(
                config=config.postgres,
                service_name=config.service_name,
                namespace=config.namespace,
                prefix=config.prefix,
                default_labels=config.default_labels,
                aggregation_interval=config.aggregation_interval,
            )
        elif recorder_type == MetricsRecorderType.PROMETHEUS:
            return recorder_class(
                service_name=config.service_name,
                namespace=config.namespace,
                prefix=config.prefix,
                default_labels=config.default_labels,
            )
        else:  # MEMORY
            return recorder_class(
                service_name=config.service_name,
                namespace=config.namespace,
                prefix=config.prefix,
                default_labels=config.default_labels,
            )

    @classmethod
    def create_from_config(cls, config: MetricsConfig) -> Optional[BaseMetricsRecorder]:
        """Create a metrics recorder from configuration.
        
        Args:
            config: Metrics configuration
            
        Returns:
            Configured metrics recorder instance or None if metrics disabled
        """
        if not config.enabled:
            return None
            
        return cls.create(config.recorder_type, config) 