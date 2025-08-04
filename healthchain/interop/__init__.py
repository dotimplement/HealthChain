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
from typing import Optional, Union

try:
    from importlib import resources
except ImportError:
    # Python < 3.9 fallback
    try:
        import importlib_resources as resources
    except ImportError:
        resources = None


def _get_bundled_configs() -> Path:
    """Get path to bundled default configs.

    Returns:
        Path to bundled configuration directory
    """
    if resources:
        try:
            # Modern approach (Python 3.9+)
            configs_ref = resources.files("healthchain") / "configs"
            if hasattr(resources, "as_file"):
                # For Python 3.9+
                with resources.as_file(configs_ref) as config_path:
                    return Path(config_path)
            else:
                # For older importlib_resources
                return Path(str(configs_ref))
        except Exception:
            pass

    # Fallback for development/editable installs
    return Path(__file__).parent.parent / "configs"


def init_config_templates(target_dir: str = "./healthchain_configs") -> Path:
    """Copy default configuration templates to a directory for customization.

    Creates a complete set of customizable configuration files that users can
    modify for their specific interoperability needs.

    Args:
        target_dir: Directory to create configuration templates in

    Returns:
        Path to the created configuration directory

    Raises:
        FileExistsError: If target directory already exists
        OSError: If unable to copy configuration files
    """
    import shutil

    source = _get_bundled_configs()
    target = Path(target_dir)

    if target.exists():
        raise FileExistsError(f"Target directory already exists: {target}")

    try:
        shutil.copytree(source, target)
        print(f"✅ Configuration templates copied to {target}")
        print(f"📝 Customize them, then use: create_interop(config_dir='{target}')")
        print("📚 See documentation for configuration options")
        return target
    except Exception as e:
        raise OSError(f"Failed to copy configuration templates: {str(e)}")


def create_interop(
    config_dir: Optional[Union[str, Path]] = None,
    validation_level: str = "strict",
    environment: str = "development",
) -> InteropEngine:
    """Create and initialize an InteropEngine instance

    Creates a configured InteropEngine for converting between healthcare data formats.
    Automatically discovers configuration files from local directory or bundled defaults.

    Args:
        config_dir: Base directory containing configuration files. If None, auto-discovers configs
        validation_level: Level of configuration validation ("strict", "warn", "ignore")
        environment: Configuration environment to use ("development", "testing", "production")

    Returns:
        Initialized InteropEngine

    Raises:
        ValueError: If config_dir doesn't exist or if validation_level/environment has invalid values
    """
    logger = logging.getLogger(__name__)

    if config_dir is None:
        # Use bundled configs as default
        config_dir = _get_bundled_configs()
        logger.info("Using bundled default configs")
    else:
        # Convert string to Path if needed
        config_dir = Path(config_dir)

    if not config_dir.exists():
        raise ValueError(f"Config directory does not exist: {config_dir}")

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
    # Factory functions
    "create_interop",
    "init_config_templates",
]
