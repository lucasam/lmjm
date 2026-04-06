import os

# Set environment variables required by Lambda handler modules at import time.
# These must be set before any handler module is imported during test collection.
os.environ.setdefault("TABLE_NAME", "lmjm")
os.environ.setdefault("EMAIL_BUCKET", "lmjm-fiscal-emails")
