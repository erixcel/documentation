"""Erixcel React hook validation; read-only."""
from pathlib import Path

STATE = Path.home() / ".codex" / "erixcel-react-validator"
SKIP = {".git", ".codex", ".vercel", "node_modules", "dist", "build", "coverage", ".next", ".turbo"}
FOLDERS = ("api", "assets", "components", "hooks", "pages", "routes", "services")  # Stores optional: no empty directories required.
DESCRIPTIONS = {
    "structure": "desarrollo/react/estructura",
    "main": "desarrollo/react/src/main",
    "styles": "desarrollo/react/src/styles",
    "api": "desarrollo/react/src/api",
    "components": "desarrollo/react/src/components",
    "hooks": "desarrollo/react/src/hooks",
    "services": "desarrollo/react/src/services",
    "stores": "desarrollo/react/src/stores",
    "page-routes": "desarrollo/react/src/pages",
    "page-files": "desarrollo/react/src/pages",
    "layouts": "desarrollo/react/src/pages",
    "functions": "desarrollo/react/src/pages",
    "interfaces": "desarrollo/react/src/pages",
    "package": "desarrollo/react/package-json",
    "env": "desarrollo/react/env",
    "routes": "desarrollo/react/src/routes",
    "pages": "desarrollo/react/src/pages",
    "api-services": "desarrollo/react/src/services",
    "config": "desarrollo/react/package-json",
}
