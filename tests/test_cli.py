from pathlib import Path

import pytest

from reckon import cli
from tests import helpers


def test_a_valid_spec_is_valid(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # GIVEN
    path = helpers.place('specs/every-shape.yml', tmp_path / 'reckon.yml')

    # WHEN
    exit_code = cli.main(['validate', str(path)])

    # THEN
    assert exit_code == 0
    assert capsys.readouterr().out == f'{path}: valid\n'


@pytest.mark.parametrize(('resource', 'problem'), [
    ('given-at-both-levels', "$.criteria[0].cases[0]: 'given' is not allowed here"),
    ('repeated-id', 'AC-1 is the id of more than one criterion'),
], ids=['breaks the schema', 'repeats an id'])
def test_an_invalid_spec_prints_its_problems(
    resource: str, problem: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # GIVEN
    path = helpers.place(f'specs/{resource}.yml', tmp_path / 'reckon.yml')

    # WHEN
    exit_code = cli.main(['validate', str(path)])

    # THEN
    assert exit_code == 1
    assert capsys.readouterr().err == f'{path}: {problem}\n'


@pytest.mark.parametrize(
    ('spec', 'audit'),
    [('reckon.yml', 'reckon.audit.gpt-5.5.yml'), ('cli.reckon.yml', 'cli.reckon.audit.gpt-5.5.yml')],
    ids=['unnamed', 'named'],
)
def test_an_audit_assessing_every_unit_of_the_spec_it_is_named_after_is_valid(
    spec: str, audit: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # GIVEN another spec beside them, with other units
    helpers.place('specs/one-criterion.yml', tmp_path / 'midi.reckon.yml')
    helpers.place('specs/every-shape.yml', tmp_path / spec)
    path = helpers.place('audits/every-shape.yml', tmp_path / audit)

    # WHEN
    exit_code = cli.main(['validate', str(path)])

    # THEN
    assert exit_code == 0
    assert capsys.readouterr().out == f'{path}: valid\n'


@pytest.mark.parametrize('resource', ['missed-only', 'empty-assessments'], ids=['no assessments', 'empty assessments'])
def test_an_audit_with_only_missed_requirements_is_valid_without_a_spec(
    resource: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # GIVEN
    path = helpers.place(f'audits/{resource}.yml', tmp_path / 'reckon.audit.yml')

    # WHEN
    exit_code = cli.main(['validate', str(path)])

    # THEN
    assert exit_code == 0
    assert capsys.readouterr().out == f'{path}: valid\n'


def test_an_audit_not_matching_the_spec_beside_it_prints_the_units_that_differ(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # GIVEN
    helpers.place('specs/one-criterion.yml', tmp_path / 'reckon.yml')
    path = helpers.place('audits/every-shape.yml', tmp_path / 'reckon.audit.yml')

    # WHEN
    exit_code = cli.main(['validate', str(path)])

    # THEN
    assert exit_code == 1
    problems = capsys.readouterr().err.splitlines()
    assert problems[:2] == [
        f'{path}: no assessment for AC-1',
        f'{path}: AC-1a is assessed, but the spec has no such unit',
    ]


@pytest.mark.parametrize('ac_id', ['AC-1', 'AC-1a'], ids=['bare id', 'case id'])
def test_an_audit_assessing_a_single_case_by_either_id_is_valid(
    ac_id: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # GIVEN
    helpers.place('specs/single-case.yml', tmp_path / 'reckon.yml')
    path = tmp_path / 'reckon.audit.yml'
    path.write_text(f'auditor: a\nassessments:\n  - {{ac_id: {ac_id}, verdict: OK}}\n')

    # WHEN
    exit_code = cli.main(['validate', str(path)])

    # THEN
    assert exit_code == 0
    assert capsys.readouterr().out == f'{path}: valid\n'


def test_an_audit_assessing_a_single_case_by_both_ids_is_invalid(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # GIVEN
    helpers.place('specs/single-case.yml', tmp_path / 'reckon.yml')
    path = tmp_path / 'reckon.audit.yml'
    path.write_text('auditor: a\nassessments:\n  - {ac_id: AC-1, verdict: OK}\n  - {ac_id: AC-1a, verdict: OK}\n')

    # WHEN
    exit_code = cli.main(['validate', str(path)])

    # THEN
    assert exit_code == 1
    assert capsys.readouterr().err == f'{path}: AC-1 and AC-1a are the same unit, assessed twice\n'


def test_no_command_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    # WHEN
    with pytest.raises(SystemExit) as exit_info:
        cli.main([])

    # THEN
    assert exit_info.value.code == 2
    assert 'the following arguments are required: command' in capsys.readouterr().err


def test_a_name_that_gives_no_kind_is_a_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # GIVEN
    path = helpers.place('specs/one-criterion.yml', tmp_path / 'reckon.audits.yml')

    # WHEN
    exit_code = cli.main(['validate', str(path)])

    # THEN
    assert exit_code == 2
    assert capsys.readouterr().err.startswith(f'reckon: {path}: not a reckon file')


def test_specs_prints_one_spec_as_it_is_leaving_hidden_paths_out(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # GIVEN
    path = helpers.place('specs/one-criterion.yml', tmp_path / 'repo' / 'reckon.yml')
    helpers.place('specs/every-shape.yml', tmp_path / '.git' / 'reckon.yml')

    # WHEN
    exit_code = cli.main(['specs', str(tmp_path)])

    # THEN
    assert exit_code == 0
    assert capsys.readouterr().out == path.read_text()


def test_specs_prints_several_specs_in_path_order_each_after_a_header(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # GIVEN
    web = helpers.place('specs/one-criterion.yml', tmp_path / 'web.reckon.yml')
    api = helpers.place('specs/every-shape.yml', tmp_path / 'api' / 'reckon.yml')

    # WHEN
    exit_code = cli.main(['specs', str(tmp_path)])

    # THEN
    assert exit_code == 0
    assert capsys.readouterr().out == f'==> {api} <==\n{api.read_text()}\n==> {web} <==\n{web.read_text()}'


def test_specs_without_specs_prints_that_there_is_no_reckoning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # WHEN
    exit_code = cli.main(['specs', str(tmp_path)])

    # THEN
    assert exit_code == 0
    assert capsys.readouterr().out == 'no reckoning\n'


def test_specs_with_an_invalid_spec_prints_only_its_problems(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # GIVEN
    helpers.place('specs/one-criterion.yml', tmp_path / 'api' / 'reckon.yml')
    invalid = helpers.place('specs/repeated-id.yml', tmp_path / 'web' / 'reckon.yml')

    # WHEN
    exit_code = cli.main(['specs', str(tmp_path)])

    # THEN
    assert exit_code == 1
    assert capsys.readouterr() == ('', f'{invalid}: AC-1 is the id of more than one criterion\n')


def test_audit_report_prints_the_audits_leaving_other_files_out(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # GIVEN
    helpers.place('specs/one-criterion.yml', tmp_path / 'reckon.yml')
    helpers.place('audits/missed-only.yml', tmp_path / 'reckon.audits.yml')
    path = helpers.place('audits/one-criterion.yml', tmp_path / 'reckon.audit.opus.yml')

    # WHEN
    exit_code = cli.main(['audit-report', str(tmp_path)])

    # THEN
    assert exit_code == 0
    assert capsys.readouterr().out == path.read_text()


def test_audit_report_with_an_invalid_audit_prints_it_and_its_problems(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # GIVEN
    helpers.place('specs/one-criterion.yml', tmp_path / 'reckon.yml')
    path = helpers.place('audits/every-shape.yml', tmp_path / 'reckon.audit.yml')

    # WHEN
    exit_code = cli.main(['audit-report', str(tmp_path)])

    # THEN
    assert exit_code == 1
    out, err = capsys.readouterr()
    assert out == path.read_text()
    assert err.startswith(f'{path}: no assessment for AC-1\n')


def test_the_templates_are_valid_and_the_audit_assesses_the_spec(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # GIVEN
    for kind, name in (('specs', 'reckon.yml'), ('audit', 'reckon.audit.yml')):
        cli.main(['template', kind])
        (tmp_path / name).write_text(capsys.readouterr().out)

    # WHEN
    exit_codes = [cli.main(['validate', str(tmp_path / name)]) for name in ('reckon.yml', 'reckon.audit.yml')]

    # THEN
    assert exit_codes == [0, 0]


def test_template_prose_takes_backticks_and_colons_unquoted(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # GIVEN
    cli.main(['template', 'specs'])
    template = capsys.readouterr().out
    path = tmp_path / 'reckon.yml'
    path.write_text(template.replace('<the observable outcome>', '`problems: wont_fit` lists `person: all`'))

    # WHEN
    exit_code = cli.main(['validate', str(path)])

    # THEN
    assert exit_code == 0
