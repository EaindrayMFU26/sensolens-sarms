"""Pseudonyms for people in the history (docs/ethics.md): a salted hash, never the e-mail.

The salt is the team's secret: .salt in the sarms repository root (git-ignored) or RMS_SALT in the environment.
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path


def salt() -> str:
    s = os.environ.get("RMS_SALT")
    if not s and Path(".salt").exists():
        s = Path(".salt").read_text().strip()
    if not s:
        sys.exit("No salt: put the team's secret in .salt (git-ignored) or set RMS_SALT.")
    return s


def pseudonym(email: str) -> str:
    """Runbook Step 1b: salted SHA-256 of the lower-cased e-mail, first 16 hex characters."""
    return hashlib.sha256((salt() + email.lower()).encode()).hexdigest()[:16]
