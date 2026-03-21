"""
AIOps Sentinel - Lambda Deployment Script
Run: python scripts/deploy_lambda.py
"""

import os
import sys
import shutil
import subprocess
import zipfile

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR       = os.path.join("C:\\Temp", "aiops_package_tmp")
ZIP_PATH      = os.path.join(BASE_DIR, "lambda_package.zip")
FUNCTION_NAME = "aiops-incident-processor-dev"
REGION        = "ap-south-1"

SOURCES = [
    os.path.join(BASE_DIR, "lambda", "incident_processor"),
    os.path.join(BASE_DIR, "lambda", "log_processor"),
    os.path.join(BASE_DIR, "lambda", "ai_analyzer"),
    os.path.join(BASE_DIR, "lambda", "notification_handler"),
    os.path.join(BASE_DIR, "ai", "prompts"),
]


def step(n, msg):
    print(f"\n[{n}/5] {msg}")


def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode


print("\nAIOps Sentinel - Lambda Deployment")
print("=" * 40)

# Step 1: Clean
step(1, "Cleaning old package...")
if os.path.exists(TMP_DIR):
    shutil.rmtree(TMP_DIR)
if os.path.exists(ZIP_PATH):
    os.remove(ZIP_PATH)
os.makedirs(TMP_DIR)
print("  Done")

# Step 2: Install dependencies
step(2, "Installing dependencies...")
run(f"pip install boto3 requests -t \"{TMP_DIR}\" --quiet")
print("  Done")

# Step 3: Copy source files
step(3, "Copying Lambda source files...")
for src in SOURCES:
    if os.path.exists(src):
        for f in os.listdir(src):
            if f.endswith(".py"):
                shutil.copy(os.path.join(src, f), TMP_DIR)
                print(f"  Copied: {f}")

# Step 4: Create ZIP
step(4, "Creating deployment ZIP...")
with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(TMP_DIR):
        # Skip __pycache__
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for file in files:
            full_path = os.path.join(root, file)
            arcname = os.path.relpath(full_path, TMP_DIR)
            zf.write(full_path, arcname)

size_mb = round(os.path.getsize(ZIP_PATH) / (1024 * 1024), 2)
print(f"  Package size: {size_mb} MB")

# Step 5: Deploy
step(5, "Deploying to AWS Lambda...")
code = run(
    f"aws lambda update-function-code "
    f"--function-name {FUNCTION_NAME} "
    f"--zip-file fileb://\"{ZIP_PATH}\" "
    f"--region {REGION} "
    f"--output table"
)

# Cleanup
shutil.rmtree(TMP_DIR)

if code == 0:
    print("\nDeployment complete!")
    print(f"Function: {FUNCTION_NAME}")
    print(f"Region:   {REGION}\n")
else:
    print("\nDeployment FAILED — check errors above")
    sys.exit(1)
