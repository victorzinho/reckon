import argparse
import sys
from importlib.metadata import version
from pathlib import Path

from reckon.services import files_service, template_service
from reckon.store import reckon_files


def main(argv: list[str] | None = None) -> int:
    """Run the reckon command line; argv defaults to sys.argv. Problems go to stderr.

    Returns:
        The exit code: 1 if a file is invalid; 2 for a usage error, such as a directory that isn't one, or a file name
        that gives no kind.
    """
    parser = argparse.ArgumentParser(prog='reckon', description='Specs and their audits.')
    parser.add_argument('--version', action='version', version=f'%(prog)s {version("reckon")}')
    commands = parser.add_subparsers(title='commands', dest='command', required=True)
    specs = commands.add_parser(
        'specs',
        help='print the specs under a directory',
        description='Show every [<name>.]reckon.yml file under the directory, hidden paths aside.',
    )
    specs.add_argument('directory', type=Path)
    audit_report = commands.add_parser(
        'audit-report',
        help='print the audits under a directory',
        description='Show every [<name>.]reckon.audit[.<auditor>].yml under the directory, hidden paths aside; '
        'invalid ones too, with their problems after.',
    )
    audit_report.add_argument('directory', type=Path)
    validate = commands.add_parser(
        'validate',
        help='validate a spec or audit file',
        description='Validate a file, discovering the type by filename. All files are validated syntactically. '
        'An audit with assessments must assess exactly the units of the spec it is named after: '
        'cli.reckon.audit.opus.yml audits cli.reckon.yml.',
    )
    validate.add_argument('file', type=Path)
    template_command = commands.add_parser(
        'template',
        help='print a file to fill in',
        description='Print a valid file, with placeholder values and comments on each field.',
    )
    template_command.add_argument('kind', choices=[kind.value for kind in reckon_files.Kind])
    args = parser.parse_args(argv)
    try:
        match args.command:
            case 'specs':
                _print_texts(files_service.specs(args.directory), none_found='no reckoning')
            case 'audit-report':
                texts, problems = files_service.audits(args.directory)
                if texts or not problems:
                    _print_texts(texts, none_found='no reckon audits')
                if problems:
                    raise reckon_files.InvalidFiles(problems)
            case 'validate':
                files_service.validate(args.file)
                print(f'{args.file}: valid')
            case 'template':
                print(template_service.template(reckon_files.Kind(args.kind)), end='')
            case _:
                raise AssertionError(f'unknown command {args.command}')  # argparse rejects it first
    except (reckon_files.UnknownFile, NotADirectoryError) as error:
        print(f'reckon: {error}', file=sys.stderr)
        return 2
    except reckon_files.InvalidFiles as error:
        print(*error.problems, sep='\n', file=sys.stderr)
        return 1
    return 0


def _print_texts(texts: dict[Path, str], none_found: str) -> None:
    # one file as it is; several with headers
    if not texts:
        print(none_found)
    elif len(texts) == 1:
        print(*texts.values(), sep='', end='')
    else:
        print('\n\n'.join(f'==> {path} <==\n{text.rstrip()}' for path, text in texts.items()))
