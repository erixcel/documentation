"""Legacy import facade; NestJS validation rules are split by resource."""
from validators._helpers import read, class_names, pascal, named_class, class_methods, controller_dto_files, IDENT
from validators.controller import validate_controller
from validators.service import validate_service
from validators.module import validate_module
from validators.dto import validate_dto
from validators.functions import validate_function
from validators.table import validate_table
from validators.script import validate_script
from validators.tsconfig import validate_tsconfig
from validators.seed import validate_seed
