import textwrap
from collections.abc import Mapping
from typing import Any, cast

import yaml
from jsonschema import Draft202012Validator

from reckon.store import reckon_files

_WIDTH = 120
_PLACEHOLDERS: dict[reckon_files.Kind, dict[str, Any]] = {
    reckon_files.Kind.SPECS: {
        'criteria': [
            {
                'id': 'AC-1',
                'verify': 'test',
                'description': '<the behaviour this criterion pins down>',
                'when': '<the surface every case exercises>',
                'given': '<the fixture state>',
                'then': '<the observable outcome>',
            },
            {
                'id': 'AC-2',
                'verify': 'test',
                'description': '<the behaviour this criterion pins down>',
                'when': '<the surface every case exercises>',
                'cases': [
                    {'given': '<the fixture state of this case>', 'then': '<the observable outcome of this case>'},
                    {'given': '<the fixture state of this case>', 'then': '<the observable outcome of this case>'},
                ],
            },
            {
                'id': 'AC-3',
                'verify': 'review',
                'obligation': 'must',
                'subject': '<what the reviewer inspects>',
                'rule': '<the yes/no property it holds>',
                'exception': '<a valid deviation>',
                'rationale': '<why the rule exists>',
            },
        ]
    },
    reckon_files.Kind.AUDIT: {
        'auditor': '<auditor label>',
        'assessments': [
            {'ac_id': 'AC-1', 'verdict': 'OK'},
            {'ac_id': 'AC-2a', 'verdict': 'AMBIGUOUS', 'note': '<the wording that decided the verdict>'},
            {
                'ac_id': 'AC-2b',
                'verdict': 'UNCONSTITUTIONAL',
                'rule': '<the standing-rule id>',
                'note': '<the wording that decided the verdict>',
            },
            {'ac_id': 'AC-3', 'verdict': 'OK'},
        ],
        'missed_requirements': [
            {'requirement': '<the obligation no criterion speaks to>', 'note': '<why the spec is silent>'}
        ]
    },
}


def template(kind: reckon_files.Kind) -> str:
    """A valid file of the kind, with placeholder values.

    It starts with the schema's description, and each field and list item comes after comments with its description
    in the schema, and its values, if they are a few. Only the first of fields with the same schema has them.
    """
    schema = reckon_files.schema(kind)
    template = _PLACEHOLDERS[kind]

    lines = [*_comments(schema['description'], 0), '']
    lines += _Writer(schema).template_lines(template, schema, 0)
    return '\n'.join(lines) + '\n'


class _Writer:
    def __init__(self, schema: Mapping[str, Any]) -> None:
        self._schema = schema
        self._commented: set[tuple[int, str]] = set()

    def template_lines(self, template: Mapping[str, Any], schema_node: Mapping[str, Any], indent: int) -> list[str]:
        lines: list[str] = []
        for field_name, field_value in template.items():
            field = schema_node['properties'][field_name]
            lines += self._comments_once(schema_node, field_name, field, indent)
            if not isinstance(field_value, list):
                lines += [' ' * indent + line for line in _yaml_lines(field_name, field_value)]
                continue

            # for lists
            lines.append(' ' * indent + f'{field_name}:')
            for item in cast(list[Mapping[str, Any]], field_value):
                item_node = self._for_value(self._resolved(field)['items'], item)
                lines += self._comments_once(item_node, '', item_node, indent + 2)
                lines += _list_item(self.template_lines(item, item_node, indent + 4), indent + 2)
        return lines

    def _comments_once(self, node: Mapping[str, Any], key: str, field: Mapping[str, Any], indent: int) -> list[str]:
        if (id(node), key) in self._commented:
            return []
        self._commented.add((id(node), key))
        resolved = self._resolved(field)
        description = field.get('description') or resolved.get('description', '')
        if values := resolved.get('enum'):
            description += f'\nValues: {", ".join(values)}'
        return _comments(description, indent)

    def _for_value(self, node: Mapping[str, Any], value: Any) -> Mapping[str, Any]:
        resolved = self._resolved(node)
        picks = [branch for branch in resolved.get('allOf', []) if '$ref' in branch.get('then', {})]
        if not picks:
            return resolved
        return next(self._resolved(branch['then']) for branch in picks if _is_valid(value, branch['if']))

    def _resolved(self, node: Mapping[str, Any]) -> Mapping[str, Any]:
        if ref := node.get('$ref'):
            return self._resolved(self._schema['$defs'][ref.removeprefix('#/$defs/')])
        return node


def _is_valid(value: Any, node: Mapping[str, Any]) -> bool:
    return Draft202012Validator(node).is_valid(value)  # pyright: ignore[reportUnknownMemberType]


def _list_item(item_lines: list[str], indent: int) -> list[str]:
    first_field = next(index for index, line in enumerate(item_lines) if not line.lstrip().startswith('#'))
    lines = [line[2:] for line in item_lines[:first_field]]
    lines.append(' ' * indent + '- ' + item_lines[first_field].lstrip())
    return lines + item_lines[first_field + 1 :]


def _comments(description: str, indent: int) -> list[str]:
    prefix = ' ' * indent + '# '
    return [
        line
        for paragraph in description.strip().splitlines()
        for line in textwrap.wrap(
            paragraph, _WIDTH, initial_indent=prefix, subsequent_indent=prefix, break_on_hyphens=False
        )
    ]


def _yaml_lines(key: str, value: Any) -> list[str]:
    # Placeholder prose is a folded block: text replacing it may hold backticks and `: ` unquoted.
    if isinstance(value, str) and value.startswith('<'):
        return [f'{key}: >-', f'  {value}']
    dumped = yaml.safe_dump({key: value}, allow_unicode=True, sort_keys=False, width=_WIDTH)  # pyright: ignore[reportUnknownMemberType]
    return dumped.splitlines()
