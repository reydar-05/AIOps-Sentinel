"""
AIOps Sentinel — Setup Verification Script
Run this after Phase 0 to confirm everything is correctly installed.
"""

import sys
import subprocess


def check(label: str, ok: bool, detail: str = ""):
    status = "✓" if ok else "✗"
    color = "\033[92m" if ok else "\033[91m"
    reset = "\033[0m"
    suffix = f"  ({detail})" if detail else ""
    print(f"  {color}{status}{reset}  {label}{suffix}")
    return ok


def run():
    print("\n======================================")
    print("  AIOps Sentinel — Setup Verification")
    print("======================================\n")

    all_ok = True

    # Python version
    major, minor = sys.version_info[:2]
    ok = major == 3 and minor >= 10
    all_ok &= check(f"Python >= 3.10", ok, f"found {major}.{minor}")

    # Core packages
    packages = [
        "boto3",
        "dotenv",
        "requests",
        "jsonschema",
        "tenacity",
        "structlog",
        "pytest",
        "moto",
        "rich",
    ]
    for pkg in packages:
        import_name = "dotenv" if pkg == "dotenv" else pkg
        try:
            __import__(import_name)
            ok = True
            version = __import__(import_name).__version__ if hasattr(__import__(import_name), "__version__") else "ok"
        except ImportError:
            ok = False
            version = "MISSING"
        all_ok &= check(f"Package: {pkg}", ok, version)

    # AWS CLI
    try:
        result = subprocess.run(
            ["aws", "--version"], capture_output=True, text=True, timeout=5
        )
        ok = result.returncode == 0
        detail = result.stdout.strip() or result.stderr.strip()
    except FileNotFoundError:
        ok = False
        detail = "aws CLI not found in PATH"
    all_ok &= check("AWS CLI installed", ok, detail)

    # AWS credentials
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"],
            capture_output=True, text=True, timeout=10
        )
        ok = result.returncode == 0
        if ok:
            import json
            identity = json.loads(result.stdout)
            detail = f"Account: {identity.get('Account')} | ARN: {identity.get('Arn')}"
        else:
            detail = "credentials not configured (run: aws configure)"
    except Exception as e:
        ok = False
        detail = str(e)
    all_ok &= check("AWS credentials valid", ok, detail)

    # .env file
    import os
    env_exists = os.path.exists(".env")
    all_ok &= check(".env file present", env_exists, "copy .env.example → .env if missing")

    # Project structure
    required_dirs = [
        "terraform", "lambda", "ai", "notifications",
        "ci-cd", "tests", "docs", "scripts", "config"
    ]
    for d in required_dirs:
        exists = os.path.isdir(d)
        all_ok &= check(f"Directory: {d}/", exists)

    print()
    if all_ok:
        print("  \033[92mAll checks passed. Phase 0 complete!\033[0m")
    else:
        print("  \033[91mSome checks failed — fix the issues above before proceeding.\033[0m")
    print()


if __name__ == "__main__":
    run()
