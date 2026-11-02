"""Erixcel React hook validation; read-only."""
from analyzers.imports import validate_resource_scopes
from validators.structure import validate_structure
from validators.main import validate_main
from validators.styles import validate_styles
from validators.api import validate_api
from validators.components import validate_components
from validators.hooks import validate_hooks
from validators.services import validate_services, validate_api_services
from validators.stores import validate_stores
from validators.routes import validate_routes
from validators.pages import validate_pages, validate_page_routes, validate_page_files
from validators.layouts import validate_layout_files
from validators.functions import validate_functions
from validators.interfaces import validate_interfaces
from validators.config import validate_config

CHECKS = {
    "structure": validate_structure,
    "main": validate_main,
    "styles": validate_styles,
    "api": validate_api,
    "components": lambda root, changed: validate_components(root, changed) + validate_resource_scopes(root, changed),
    "hooks": lambda root, changed: validate_hooks(root, changed) + validate_resource_scopes(root, changed),
    "services": lambda root, changed: validate_services(root, changed) + validate_resource_scopes(root, changed),
    "stores": lambda root, changed: validate_stores(root, changed) + validate_resource_scopes(root, changed),
    "page-routes": validate_page_routes,
    "page-files": validate_page_files,
    "layouts": validate_layout_files,
    "functions": validate_functions,
    "interfaces": validate_interfaces,
    "package": lambda root, changed: validate_config(root, changed) if "package.json" in changed else [],
    "env": lambda root, changed: validate_config(root, changed) if {".env", ".env.example"} & changed else [],
    # Backwards-compatible entry points for old manual commands.
    "routes": validate_routes,
    "pages": validate_pages,
    "api-services": validate_api_services,
    "config": validate_config,
}
