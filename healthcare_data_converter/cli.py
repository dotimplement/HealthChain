"""
Healthcare Data Converter CLI - Command-line interface.

Provides command-line tools for healthcare data format conversion.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from healthcare_data_converter.converter import HealthcareDataConverter
from healthcare_data_converter.models import (
    ConversionFormat,
    ConversionRequest,
    ConversionStatus,
    DocumentType,
    ValidationLevel,
)


def setup_logging(verbose: bool = False):
    """Configure logging for CLI."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="healthcare-converter",
        description="Healthcare Data Format Converter - Convert between FHIR and CDA formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert CDA to FHIR
  healthcare-converter convert --input patient.xml --source cda --target fhir --output patient.json

  # Convert FHIR Bundle to CDA CCD
  healthcare-converter convert --input bundle.json --source fhir --target cda --document-type ccd

  # Validate a CDA document
  healthcare-converter validate --format cda --input document.xml

  # Start the API server
  healthcare-converter serve --host 0.0.0.0 --port 8000

  # Show conversion capabilities
  healthcare-converter info
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Convert command
    convert_parser = subparsers.add_parser(
        "convert", help="Convert between healthcare data formats"
    )
    convert_parser.add_argument(
        "-i", "--input",
        type=str,
        required=True,
        help="Input file path or '-' for stdin",
    )
    convert_parser.add_argument(
        "-o", "--output",
        type=str,
        default="-",
        help="Output file path or '-' for stdout (default: stdout)",
    )
    convert_parser.add_argument(
        "-s", "--source",
        type=str,
        required=True,
        choices=[f.value for f in ConversionFormat],
        help="Source format",
    )
    convert_parser.add_argument(
        "-t", "--target",
        type=str,
        required=True,
        choices=[f.value for f in ConversionFormat],
        help="Target format",
    )
    convert_parser.add_argument(
        "-d", "--document-type",
        type=str,
        default="ccd",
        choices=[dt.value for dt in DocumentType],
        help="CDA document type (for FHIR->CDA conversion)",
    )
    convert_parser.add_argument(
        "--validation",
        type=str,
        default="warn",
        choices=[v.value for v in ValidationLevel],
        help="Validation level",
    )
    convert_parser.add_argument(
        "--no-narrative",
        action="store_true",
        help="Exclude narrative sections from CDA output",
    )
    convert_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print output (JSON indentation)",
    )
    convert_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate healthcare data format"
    )
    validate_parser.add_argument(
        "-i", "--input",
        type=str,
        required=True,
        help="Input file path or '-' for stdin",
    )
    validate_parser.add_argument(
        "-f", "--format",
        type=str,
        required=True,
        choices=["cda", "fhir"],
        help="Data format to validate",
    )
    validate_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    # Serve command
    serve_parser = subparsers.add_parser(
        "serve", help="Start the conversion API server"
    )
    serve_parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )
    serve_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    serve_parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Logging level",
    )

    # Info command
    info_parser = subparsers.add_parser(
        "info", help="Show conversion capabilities"
    )
    info_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    # Batch command
    batch_parser = subparsers.add_parser(
        "batch", help="Batch convert multiple files"
    )
    batch_parser.add_argument(
        "-i", "--input-dir",
        type=str,
        required=True,
        help="Input directory containing files to convert",
    )
    batch_parser.add_argument(
        "-o", "--output-dir",
        type=str,
        required=True,
        help="Output directory for converted files",
    )
    batch_parser.add_argument(
        "-s", "--source",
        type=str,
        required=True,
        choices=[f.value for f in ConversionFormat],
        help="Source format",
    )
    batch_parser.add_argument(
        "-t", "--target",
        type=str,
        required=True,
        choices=[f.value for f in ConversionFormat],
        help="Target format",
    )
    batch_parser.add_argument(
        "-p", "--pattern",
        type=str,
        default="*",
        help="File pattern to match (default: *)",
    )
    batch_parser.add_argument(
        "-d", "--document-type",
        type=str,
        default="ccd",
        choices=[dt.value for dt in DocumentType],
        help="CDA document type",
    )
    batch_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    return parser.parse_args()


def read_input(input_path: str) -> str:
    """Read input from file or stdin."""
    if input_path == "-":
        return sys.stdin.read()
    else:
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        return path.read_text()


def write_output(output_path: str, data: str):
    """Write output to file or stdout."""
    if output_path == "-":
        print(data)
    else:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)


def cmd_convert(args: argparse.Namespace) -> int:
    """Execute convert command."""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # Read input
        input_data = read_input(args.input)
        logger.debug(f"Read {len(input_data)} bytes from input")

        # Create converter
        converter = HealthcareDataConverter(
            validation_level=ValidationLevel(args.validation)
        )

        # Build request
        request = ConversionRequest(
            data=input_data,
            source_format=ConversionFormat(args.source),
            target_format=ConversionFormat(args.target),
            document_type=DocumentType(args.document_type),
            validation_level=ValidationLevel(args.validation),
            include_narrative=not args.no_narrative,
        )

        # Convert
        response = converter.convert(request)

        # Handle result
        if response.status == ConversionStatus.FAILED:
            logger.error("Conversion failed:")
            for error in response.errors:
                logger.error(f"  - {error}")
            return 1

        if response.warnings:
            for warning in response.warnings:
                logger.warning(warning)

        # Format output
        if response.data:
            if isinstance(response.data, (dict, list)):
                indent = 2 if args.pretty else None
                output = json.dumps(response.data, indent=indent)
            else:
                output = response.data

            write_output(args.output, output)

        # Print summary to stderr
        print(
            f"Conversion completed: {response.metadata.resource_count} resources, "
            f"{response.metadata.processing_time_ms}ms",
            file=sys.stderr,
        )

        return 0 if response.status == ConversionStatus.SUCCESS else 1

    except Exception as e:
        logger.error(f"Conversion error: {e}")
        if args.verbose:
            logger.exception(e)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Execute validate command."""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        input_data = read_input(args.input)
        converter = HealthcareDataConverter()

        if args.format == "cda":
            is_valid, messages = converter.validate_cda(input_data)
        else:
            is_valid, messages = converter.validate_fhir(json.loads(input_data))

        if is_valid:
            print("Validation passed", file=sys.stderr)
            return 0
        else:
            print("Validation failed:", file=sys.stderr)
            for msg in messages:
                print(f"  - {msg}", file=sys.stderr)
            return 1

    except Exception as e:
        logger.error(f"Validation error: {e}")
        return 1


def cmd_serve(args: argparse.Namespace) -> int:
    """Execute serve command."""
    from healthcare_data_converter.service import ConversionService

    service = ConversionService()
    service.run(
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Execute info command."""
    converter = HealthcareDataConverter()
    capabilities = converter.get_capabilities()

    if args.json:
        print(json.dumps(capabilities.model_dump(), indent=2))
    else:
        print("Healthcare Data Format Converter")
        print("=" * 40)
        print()
        print("Supported Conversions:")
        for conv in capabilities.supported_conversions:
            print(f"  {conv['source'].upper()} -> {conv['target'].upper()}")
        print()
        print("Supported Document Types:")
        for dt in capabilities.supported_document_types:
            print(f"  - {dt}")
        print()
        print("Supported FHIR Resources:")
        for resource in capabilities.supported_fhir_resources:
            print(f"  - {resource}")
        print()
        print("Validation Levels:")
        for level in capabilities.validation_levels:
            print(f"  - {level}")

    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    """Execute batch command."""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    # Find matching files
    files = list(input_dir.glob(args.pattern))
    if not files:
        logger.warning(f"No files matching pattern '{args.pattern}' in {input_dir}")
        return 0

    logger.info(f"Found {len(files)} files to convert")

    converter = HealthcareDataConverter()
    success_count = 0
    fail_count = 0

    for input_file in files:
        try:
            input_data = input_file.read_text()

            request = ConversionRequest(
                data=input_data,
                source_format=ConversionFormat(args.source),
                target_format=ConversionFormat(args.target),
                document_type=DocumentType(args.document_type),
            )

            response = converter.convert(request)

            if response.status != ConversionStatus.FAILED:
                # Determine output extension
                ext = ".json" if args.target == "fhir" else ".xml"
                output_file = output_dir / f"{input_file.stem}{ext}"

                if isinstance(response.data, (dict, list)):
                    output_data = json.dumps(response.data, indent=2)
                else:
                    output_data = response.data

                output_file.write_text(output_data)
                success_count += 1
                logger.debug(f"Converted: {input_file.name} -> {output_file.name}")
            else:
                fail_count += 1
                logger.error(f"Failed: {input_file.name} - {response.errors}")

        except Exception as e:
            fail_count += 1
            logger.error(f"Error processing {input_file.name}: {e}")

    logger.info(f"Batch complete: {success_count} succeeded, {fail_count} failed")
    return 0 if fail_count == 0 else 1


def main():
    """Main entry point."""
    args = parse_args()

    if args.command is None:
        print("Usage: healthcare-converter <command> [options]")
        print("Commands: convert, validate, serve, info, batch")
        print("Use --help for more information")
        return 1

    commands = {
        "convert": cmd_convert,
        "validate": cmd_validate,
        "serve": cmd_serve,
        "info": cmd_info,
        "batch": cmd_batch,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
