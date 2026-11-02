"""Compatibility facade for pre-existing hooks and tests."""
import subprocess
from common.constants import STATE, SKIP, FOLDERS, DESCRIPTIONS
from common import snapshot as _snapshot
from common import runner as _runner
from common.discovery import project_for, looks_like_react, discover, text, changed_in, logic_files
from common.snapshot import snapshot_id, fingerprint, snapshot
from analyzers.ast import ast_check
from analyzers.imports import resource_scope, resource_kind, resolve_relative_import, validate_resource_scopes
from validators.registry import CHECKS
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

def store(payload, root):
    _snapshot.STATE = STATE
    return _snapshot.store(payload, root)

def load(payload, root):
    _snapshot.STATE = STATE
    return _snapshot.load(payload, root)

def stop(payload, kind):
    _snapshot.STATE = STATE
    return _runner.stop(payload, kind)

def run(kind):
    _snapshot.STATE = STATE
    return _runner.run(kind)
