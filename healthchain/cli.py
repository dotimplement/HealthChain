import argparse
import subprocess
import sys
from pathlib import Path


def run_file(filename):
    """Run a Python file using poetry with enhanced error handling."""
    # Validate file exists and has .py extension
    file_path = Path(filename)
    
    if not file_path.exists():
        print(f"❌ Error: File '{filename}' not found")
        print("💡 Tip: Check the file path and make sure the file exists")
        print("   Example: healthchain run my_script.py")
        return
    
    if not filename.endswith('.py'):
        print(f"❌ Error: '{filename}' is not a Python file")
        print("💡 Tip: HealthChain can only run Python (.py) files")
        print("   Example: healthchain run my_healthchain_app.py")
        return
    
    try:
        print(f"🚀 Running {filename}...")
        result = subprocess.run(
            ["poetry", "run", "python", filename], 
            check=True,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
            
    except FileNotFoundError:
        print("❌ Error: Poetry not found")
        print("💡 Tip: Install Poetry or run the file directly with Python:")
        print(f"   python {filename}")
        print("📚 Poetry installation: https://python-poetry.org/docs/#installation")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: Script execution failed with exit code {e.returncode}")
        if e.stdout:
            print("📋 Output:")
            print(e.stdout)
        if e.stderr:
            print("🔍 Error details:")
            print(e.stderr)
        print("\n💡 Common fixes:")
        print("   • Check for syntax errors in your Python file")
        print("   • Ensure all required dependencies are installed")
        print("   • Verify your HealthChain code follows the documentation examples")
        print("📚 Documentation: https://dotimplement.github.io/HealthChain/")


def init_configs(target_dir: str):
    """Initialize configuration templates for customization with enhanced validation."""
    # Validate target directory name
    target_path = Path(target_dir)
    
    # Check if target is a file
    if target_path.exists() and target_path.is_file():
        print(f"❌ Error: '{target_dir}' is a file, not a directory")
        print("💡 Tip: Choose a directory name instead:")
        print(f"   healthchain init-configs {target_dir}_configs")
        return
    
    # Warn if target directory name might cause issues
    if ' ' in target_dir:
        print("⚠️  Warning: Directory name contains spaces, which may cause issues")
        print("💡 Tip: Consider using underscores instead:")
        print(f"   healthchain init-configs {target_dir.replace(' ', '_')}")
    
    try:
        from healthchain.interop import init_config_templates

        print(f"📁 Creating configuration templates in: {target_dir}")
        target_path = init_config_templates(target_dir)
        print(f"\n🎉 Success! Configuration templates created at: {target_path}")
        print("\n📖 Next steps:")
        print("  1. Customize the configuration files in the created directory")
        print("     • Edit template files in templates/ subdirectory")
        print("     • Modify code mappings in mappings/ subdirectory")
        print("     • Adjust validation rules in environments/ subdirectory")
        print("  2. Use them in your code:")
        print("     from healthchain.interop import create_interop")
        print(f"     engine = create_interop(config_dir='{target_dir}')")
        print("\n📚 Documentation: https://dotimplement.github.io/HealthChain/reference/interop/configuration/")
        print("💬 Need help? Join our Discord: https://discord.gg/UQC6uAepUz")

    except FileExistsError as e:
        print(f"❌ Error: {str(e)}")
        print("💡 Possible solutions:")
        print(f"   • Choose a different directory name:")
        print(f"     healthchain init-configs {target_dir}_new")
        print(f"   • Remove the existing directory:")
        print(f"     rm -rf {target_dir}  # Linux/Mac")
        print(f"     rmdir /s {target_dir}  # Windows")
        print(f"   • Use the existing directory if it already contains configs")
        
    except ImportError as e:
        print(f"❌ Error: Missing required HealthChain components: {str(e)}")
        print("💡 Fix: Reinstall HealthChain with all dependencies:")
        print("   pip install --upgrade healthchain")
        print("   # or")
        print("   poetry add healthchain")
        
    except PermissionError as e:
        print(f"❌ Error: Permission denied: {str(e)}")
        print("💡 Possible solutions:")
        print("   • Run with appropriate permissions")
        print("   • Choose a directory you have write access to:")
        print("     healthchain init-configs ~/my_healthchain_configs")
        print("   • Check if the target location is write-protected")
        
    except Exception as e:
        print(f"❌ Error initializing configs: {str(e)}")
        print("💡 Troubleshooting steps:")
        print("   1. Ensure HealthChain is properly installed:")
        print("      pip install --upgrade healthchain")
        print("   2. Check if you have write permissions to the target directory")
        print("   3. Try a different target directory name")
        print("   4. If the issue persists, please report it:")
        print("      https://github.com/dotimplement/HealthChain/issues")
        print("💬 Get help on Discord: https://discord.gg/UQC6uAepUz")


def main():
    parser = argparse.ArgumentParser(
        description="HealthChain CLI - Build and deploy healthcare AI applications",
        epilog="""
Examples:
  healthchain run my_cds_service.py              # Run a HealthChain application
  healthchain init-configs ./my_configs          # Create customizable config templates
  healthchain init-configs                       # Create configs in default location

For more help:
  Documentation: https://dotimplement.github.io/HealthChain/
  Discord Community: https://discord.gg/UQC6uAepUz
  GitHub Issues: https://github.com/dotimplement/HealthChain/issues
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subparser for the 'run' command
    run_parser = subparsers.add_parser(
        "run", 
        help="Run a HealthChain Python application",
        description="""
Run a HealthChain Python application using Poetry.

This command executes your HealthChain script with proper dependency management,
ensuring all required packages are available in the Poetry environment.
        """,
        epilog="""
Examples:
  healthchain run cds_service.py                 # Run a CDS Hooks service
  healthchain run clinical_pipeline.py           # Run a clinical NLP pipeline
  healthchain run fhir_gateway.py               # Run a FHIR gateway application

Note: This command requires Poetry to be installed. If Poetry is not available,
you can run your script directly with: python your_script.py
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    run_parser.add_argument(
        "filename", 
        type=str, 
        help="Python file to run (must be a .py file)"
    )

    # Subparser for the 'init-configs' command
    init_parser = subparsers.add_parser(
        "init-configs",
        help="Initialize customizable configuration templates",
        description="""
Create a complete set of customizable configuration templates for HealthChain
interoperability features. These templates allow you to customize FHIR ↔ CDA
conversions, code system mappings, and validation rules.
        """,
        epilog="""
Examples:
  healthchain init-configs                       # Create in ./healthchain_configs/
  healthchain init-configs ./my_configs          # Create in custom directory
  healthchain init-configs ~/hospital_configs    # Create in home directory

The created directory will contain:
  • templates/     - CDA ↔ FHIR conversion templates
  • mappings/      - Code system mappings (SNOMED, LOINC, etc.)
  • environments/ - Development, testing, production configs
  • defaults.yaml - Base configuration settings

After creation, you can use your custom configs with:
  from healthchain.interop import create_interop
  engine = create_interop(config_dir="./my_configs")
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    init_parser.add_argument(
        "target_dir",
        type=str,
        nargs="?",
        default="./healthchain_configs",
        help="Directory to create configuration templates (default: ./healthchain_configs)"
    )

    # Add aliases for common commands
    parser.add_argument(
        "--version", "-v",
        action="version", 
        version="HealthChain CLI - Run 'pip show healthchain' for version info"
    )

    args = parser.parse_args()

    if args.command == "run":
        run_file(args.filename)
    elif args.command == "init-configs":
        init_configs(args.target_dir)


if __name__ == "__main__":
    main()