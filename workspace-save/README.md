# Workspace Save

This folder stores sanitized snapshots prepared for remote backup.

Included archives:
- `Toonflow-app-source-snapshot.zip`
- `timesfm-local-snapshot.zip`
- `timesfm-upstream-snapshot.zip`
- `start-timesfm-dashboard.cmd`

Excluded from the snapshots:
- Embedded `.git` directories
- Dependency caches such as `node_modules`
- Build outputs, runtime logs, and `__pycache__`
- Local databases and environment files
- Temporary dashboard/token files
