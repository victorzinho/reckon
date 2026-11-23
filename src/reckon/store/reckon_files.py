import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, ValidationError


class Kind(Enum):
    SPECS = 'specs'
    AUDIT = 'audit'


@dataclass(frozen=True)
class ReckonFile:
    """A file whose document breaks no schema of its kind."""

    path: Path
    kind: Kind
    text: str
    document: Mapping[str, Any]


class UnknownFile(Exception):
    """A file whose name gives no kind."""


class InvalidFiles(Exception):
    """Files that can't be used. Each problem starts with the path of its file."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__('\n'.join(problems))
        self.problems = problems


_SPEC_NAME = re.compile(r'(?:(?P<name>.+)\.)?reckon\.yml')
_AUDIT_NAME = re.compile(r'(?:(?P<name>.+)\.)?reckon\.audit(?:\.[^/]+)?\.yml')
_SCHEMAS: dict[Kind, dict[str, Any]] = {
    kind: yaml.safe_load(files('reckon.store').joinpath('schemas', f'{kind.value}.schema.yml').read_text())
    for kind in Kind
}
_VALIDATORS = {kind: Draft202012Validator(schema) for kind, schema in _SCHEMAS.items()}


def schema(kind: Kind) -> dict[str, Any]:
    return _SCHEMAS[kind]


def audited_spec(path: Path) -> Path:
    """The spec the audit at path is named after: cli.reckon.audit.opus.yml audits cli.reckon.yml."""
    match = _AUDIT_NAME.fullmatch(path.name)
    name = match and match['name']
    return path.with_name(f'{name}.reckon.yml' if name else 'reckon.yml')


def find(directory: Path, kind: Kind) -> list[Path]:
    """The files of that kind under directory, sorted, leaving out hidden files and directories.

    Raises:
        NotADirectoryError: if directory isn't one.
    """
    if not directory.is_dir():
        raise NotADirectoryError(f'{directory} is not a directory')
    found: list[Path] = []
    for root, directories, names in os.walk(directory):
        directories[:] = [name for name in directories if not name.startswith('.')]
        found += [Path(root, name) for name in names if not name.startswith('.') and _kind_of(Path(name)) is kind]
    return sorted(found)


def read(path: Path) -> ReckonFile:
    """The file, of the kind its name gives: [<name>.]reckon.yml for a spec, [<name>.]reckon.audit[.<auditor>].yml
    for an audit.

    Raises:
        UnknownFile: if the name gives no kind.
        InvalidFiles: if it can't be read, isn't YAML, or breaks its kind's schema.
    """
    kind = _kind_of(path)
    if kind is None:
        raise UnknownFile(
            f'{path}: not a reckon file; name it [<name>.]reckon.yml or [<name>.]reckon.audit[.<auditor>].yml'
        )
    text = read_text(path)
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise InvalidFiles([_problem(path, error)]) from error
    errors = _VALIDATORS[kind].iter_errors(document)  # pyright: ignore[reportUnknownMemberType]
    if problems := sorted(f'{path}: {error.json_path}: {_message(error)}' for error in errors):
        raise InvalidFiles(problems)
    return ReckonFile(path, kind, text, document)


def read_text(path: Path) -> str:
    """The file's text, valid or not.

    Raises:
        InvalidFiles: if it can't be read as UTF-8.
    """
    try:
        return path.read_text(encoding='utf-8')
    except (OSError, UnicodeError) as error:
        raise InvalidFiles([_problem(path, error)]) from error


def _problem(path: Path, error: Exception) -> str:
    return f'{path}: {" ".join(str(error).split())}'


def _kind_of(path: Path) -> Kind | None:
    if _SPEC_NAME.fullmatch(path.name):
        return Kind.SPECS
    if _AUDIT_NAME.fullmatch(path.name):
        return Kind.AUDIT
    return None


def _message(error: ValidationError) -> str:
    # jsonschema words these with the whole value or subschema.
    match error.validator, error.validator_value:
        case 'not', {'required': [name]}:
            return f'{name!r} is not allowed here'
        case 'maxItems', limit:
            return f'more than {limit} items'
        case 'pattern', r'\S':
            return 'blank'
        case _:
            return error.message
