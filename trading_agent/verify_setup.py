"""
Setup verification script
Run this to check if everything is installed correctly
"""

import sys
from pathlib import Path

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 11:
        print("✅ Python version:", f"{version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor} found, but 3.11+ required")
        return False

def check_imports():
    """Check required packages"""
    packages = [
        ("claude_agent_sdk", "Claude Agent SDK"),
        ("alpaca", "Alpaca API"),
        ("pandas", "Pandas"),
        ("numpy", "NumPy"),
        ("sqlalchemy", "SQLAlchemy"),
        ("yaml", "PyYAML"),
        ("slack_bolt", "Slack Bolt")
    ]

    all_good = True
    for module, name in packages:
        try:
            __import__(module)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name} - Run: pip install -r requirements.txt")
            all_good = False

    return all_good

def check_config():
    """Check configuration file"""
    config_path = Path(__file__).parent / "config" / "config.yaml"
    example_path = Path(__file__).parent / "config" / "config.example.yaml"

    if not example_path.exists():
        print("❌ config.example.yaml missing")
        return False

    print("✅ config.example.yaml found")

    if not config_path.exists():
        print("⚠️  config.yaml not found")
        print("   → Run: cp config/config.example.yaml config/config.yaml")
        print("   → Then edit config/config.yaml with your API keys")
        return False

    print("✅ config.yaml found")

    # Try to load it
    try:
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Check for required keys
        if not config.get("alpaca", {}).get("api_key"):
            print("⚠️  Alpaca API key not configured")
            return False

        if config["alpaca"]["api_key"] == "YOUR_ALPACA_API_KEY":
            print("⚠️  Please update config.yaml with real API keys")
            return False

        print("✅ Configuration looks good")
        return True

    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False

def check_directory_structure():
    """Check required directories"""
    base = Path(__file__).parent
    dirs = [
        "agent",
        "tools",
        "storage",
        "messaging",
        "hooks",
        "config"
    ]

    all_good = True
    for dirname in dirs:
        dirpath = base / dirname
        if dirpath.exists():
            print(f"✅ {dirname}/")
        else:
            print(f"❌ {dirname}/ missing")
            all_good = False

    return all_good

def check_claude_cli():
    """Check if Claude CLI is installed"""
    import subprocess
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✅ Claude Code CLI installed")
            return True
        else:
            print("❌ Claude Code CLI not found")
            print("   → Run: npm install -g @anthropic-ai/claude-code")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ Claude Code CLI not found")
        print("   → Run: npm install -g @anthropic-ai/claude-code")
        return False

def main():
    print("\n" + "="*60)
    print("🔍 TRADING AGENT SETUP VERIFICATION")
    print("="*60 + "\n")

    results = []

    print("📋 Checking Python version...")
    results.append(check_python_version())
    print()

    print("📦 Checking Python packages...")
    results.append(check_imports())
    print()

    print("⚙️  Checking Claude CLI...")
    results.append(check_claude_cli())
    print()

    print("📁 Checking directory structure...")
    results.append(check_directory_structure())
    print()

    print("🔧 Checking configuration...")
    results.append(check_config())
    print()

    print("="*60)
    if all(results):
        print("✅ ALL CHECKS PASSED!")
        print("\nYou're ready to start the trading agent:")
        print("   python main.py")
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nPlease fix the issues above and run this script again:")
        print("   python verify_setup.py")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()