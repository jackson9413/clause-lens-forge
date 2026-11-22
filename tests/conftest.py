"""Test setup: point the database at a temporary file before it is imported."""

import os
import tempfile

TMP_DB = os.path.join(tempfile.mkdtemp(prefix="clause-lens-test-"), "reviews.db")
os.environ["CLAUSE_LENS_DB"] = TMP_DB

import db  # noqa: E402  (import after the env var is set)

db.init_db()
