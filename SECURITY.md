# Security and private data

Never attach game saves, authentication information, downloaded databases, or local
research archives to an issue. Report ordinary installation failures through an
issue with identifying details removed.

For a vulnerability that could expose data or damage files, use this repository's
GitHub private vulnerability reporting feature. Do not disclose secrets in a public issue.

The release is manually installed and launched. It creates no background service,
scheduled task, browser automation, analytics, or automatic downloader.
Supported game builds and expected payload hashes are checked before launch.
Research tools and private data in the maintainer's workspace are excluded by a
default-deny Git allowlist, and scripts/check_publication.py checks the actual Git index.
