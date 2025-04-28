"""
HealthChain Interoperability Module

This package provides modules for handling interoperability between
healthcare data formats.
"""

from .config_manager import InteropConfigManager
from .engine import InteropEngine
from .types import FormatType, validate_format
from .template_registry import TemplateRegistry
from .parsers.cda import CDAParser
from .generators.cda import CDAGenerator
from .generators.fhir import FHIRGenerator

import logging
from pathlib import Path
from typing import Optional


def create_engine(
    config_dir: Optional[Path] = None,
    validation_level: str = "strict",
    environment: str = "development",
) -> InteropEngine:
    """Create and initialize an InteropEngine instance

    Creates a configured InteropEngine for converting between healthcare data formats.

    Args:
        config_dir: Base directory containing configuration files. If None, defaults to "configs"
        validation_level: Level of configuration validation ("strict", "warn", "ignore")
        environment: Configuration environment to use ("development", "testing", "production")

    Returns:
        Initialized InteropEngine

    Raises:
        ValueError: If config_dir doesn't exist or if validation_level/environment has invalid values
    """
    logger = logging.getLogger(__name__)
    if config_dir is None:
        logger.warning("config_dir is not provided, looking for configs in /configs")
        config_dir = Path("configs")
        if not config_dir.exists():
            raise ValueError("config_dir does not exist")

    # TODO: Remove this once we have a proper environment system
    if environment not in ["development", "testing", "production"]:
        raise ValueError("environment must be one of: development, testing, production")

    engine = InteropEngine(config_dir, validation_level, environment)

    return engine


__all__ = [
    # Core classes
    "InteropEngine",
    "InteropConfigManager",
    "TemplateRegistry",
    # Types and utils
    "FormatType",
    "validate_format",
    # Parsers
    "CDAParser",
    # Generators
    "CDAGenerator",
    "FHIRGenerator",
    "create_engine",
]
