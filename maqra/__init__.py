"""Maqra: an open, verified archive of verse-by-verse Qur'an recitations.

The package mirrors https://everyayah.com/data/ file by file, verifies every
file against the upstream MD5 lists where they exist and against exact byte
counts everywhere, records SHA-256 for every file, and packages the result for
Hugging Face and GitHub Releases.
"""

__version__ = "0.1.0"

UPSTREAM_BASE = "https://everyayah.com/data/"
USER_AGENT = f"maqra/{__version__} (+https://github.com/Abdalla-Eldoumani/maqra)"
