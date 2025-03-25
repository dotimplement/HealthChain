"""
HealthChain Interoperability Module

This module provides functionality for interoperability between different healthcare data formats.
"""

from .engine import InteropEngine, FormatType
from .template_registry import TemplateRegistry
from .template_renderer import TemplateRenderer
from .parsers.cda import CDAParser
from .parsers.hl7v2 import HL7v2Parser
from .generators.cda import CDAGenerator
from .generators.fhir import FHIRGenerator
from .generators.hl7v2 import HL7v2Generator

import logging
from pathlib import Path
from typing import Optional


def create_engine(
    config_dir: Optional[Path] = None, validation_level: str = "strict"
) -> InteropEngine:
    """Create and initialize an InteropEngine instance

    Args:
        config_dir: Base directory containing configuration files
        validation_level: Level of configuration validation (strict, warn, ignore)

    Returns:
        Initialized InteropEngine
    """
    engine = InteropEngine(config_dir, validation_level)

    # Add a debug message to verify document validation is available
    logger = logging.getLogger(__name__)
    logger.debug("InteropEngine created with document validation support")

    return engine


__all__ = [
    "InteropEngine",
    "FormatType",
    "TemplateRegistry",
    "TemplateRenderer",
    "CDAParser",
    "HL7v2Parser",
    "CDAGenerator",
    "FHIRGenerator",
    "HL7v2Generator",
    "create_engine",
]
