import contextlib
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from reckon.store import reckon_files


def specs(directory: Path) -> dict[Path, str]:
    """The text of every spec under directory, hidden paths aside, by path in path order.

    Raises:
        NotADirectoryError: if directory isn't one.
        reckon_files.InvalidFiles: with the problems of every file that isn't valid, as validate finds them.
    """
    return _texts(directory, reckon_files.Kind.SPECS)


def audits(directory: Path) -> tuple[dict[Path, str], list[str]]:
    """The text of every audit file under directory that can be read, valid or not, by path in path order, hidden
    paths aside; and the problems of every file that isn't valid, as validate finds them.

    Raises:
        NotADirectoryError: if directory isn't one.
    """
    paths = reckon_files.find(directory, reckon_files.Kind.AUDIT)
    texts: dict[Path, str] = {}
    for path in paths:
        with contextlib.suppress(reckon_files.InvalidFiles):  # _problems reports it
            texts[path] = reckon_files.read_text(path)
    return texts, [problem for path in paths for problem in _problems(path)]


def validate(path: Path) -> None:
    """Check the file, of the kind its name gives, against its schema; and that no id repeats.

    An audit with assessments must assess exactly the units of the spec it's named after.

    Raises:
        reckon_files.UnknownFile: if the name gives no kind.
        reckon_files.InvalidFiles: with every problem found.
    """
    if problems := _problems(path):
        raise reckon_files.InvalidFiles(problems)


def _texts(directory: Path, kind: reckon_files.Kind) -> dict[Path, str]:
    paths = reckon_files.find(directory, kind)
    if problems := [problem for path in paths for problem in _problems(path)]:
        raise reckon_files.InvalidFiles(problems)
    return {path: reckon_files.read(path).text for path in paths}


def _problems(path: Path) -> list[str]:
    try:
        reckon_file = reckon_files.read(path)
    except reckon_files.InvalidFiles as error:
        return error.problems

    if problems := _repeated_ids(reckon_file):
        return [f'{path}: {problem}' for problem in problems]
    if reckon_file.kind is reckon_files.Kind.SPECS or not reckon_file.document.get('assessments'):
        return []

    # for audits
    spec_path = reckon_files.audited_spec(path)
    if not spec_path.is_file():
        return [f'{path}: it has assessments, but there is no {spec_path.name} beside it']
    if spec_problems := _problems(spec_path):
        return [f'{path}: the {spec_path.name} beside it is invalid', *spec_problems]
    spec_document = reckon_files.read(spec_path).document
    return [f'{path}: {problem}' for problem in _coverage_problems(reckon_file.document, spec_document)]


def _repeated_ids(reckon_file: reckon_files.ReckonFile) -> list[str]:
    if reckon_file.kind is reckon_files.Kind.SPECS:
        criterion_ids = (criterion['id'] for criterion in reckon_file.document['criteria'])
        return [f'{id_} is the id of more than one criterion' for id_ in _repeated(criterion_ids)]
    assessed_ids = (assessment['ac_id'] for assessment in reckon_file.document.get('assessments', []))
    return [f'{id_} is assessed more than once' for id_ in _repeated(assessed_ids)]


def _units(spec: Mapping[str, Any]) -> list[tuple[str, ...]]:
    # each unit's ids: a single case is both its criterion's id and its own
    units: list[tuple[str, ...]] = []
    for criterion in spec['criteria']:
        id_ = criterion['id']
        case_ids = [f'{id_}{chr(ord("a") + index)}' for index in range(len(criterion.get('cases', [])))]
        if len(case_ids) > 1:
            units += [(case_id,) for case_id in case_ids]
        else:
            units.append((id_, *case_ids))
    return units


def _coverage_problems(audit: Mapping[str, Any], spec: Mapping[str, Any]) -> list[str]:
    units = _units(spec)
    assessed = [assessment['ac_id'] for assessment in audit['assessments']]
    problems: list[str] = []
    for ids in units:
        found = [id_ for id_ in ids if id_ in assessed]
        if not found:
            problems.append(f'no assessment for {" or ".join(ids)}')
        elif len(found) > 1:
            problems.append(f'{" and ".join(found)} are the same unit, assessed twice')
    known = {id_ for ids in units for id_ in ids}
    return problems + [f'{id_} is assessed, but the spec has no such unit' for id_ in assessed if id_ not in known]


def _repeated(ids: Iterable[str]) -> list[str]:
    return [id_ for id_, count in Counter(ids).items() if count > 1]
