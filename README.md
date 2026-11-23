# reckon

> I reckon this is how it's done.

reckon is the S in SDD (spec-driven development): the spec, kept in files an agent can write, check and build from.

A ticket says what's wanted in prose, and every dev (and agent) reads it differently and makes decisions on top.
reckon gives those requirements and decisions (the spec) a structure: criteria proven by a test, written as
**given-when-then**; and criteria a reviewer judges, written as a rule in loose prose, such as **EARS**.

Audits of a spec get a structure too: a verdict for each unit, and what the spec misses.
Each file has a schema, so you can build your agents around them: one writes the spec, another audits it, and the next
implements it.

reckon can:

- Read the specs and audits that exist, for a task or a whole app, validating them as it reads.
- Validate a file, telling what's wrong with it, including an audit that doesn't match its spec.
- Give a template to write a new file, with each field described.

## Quick start

```shell
uv tool install git+https://github.com/victorzinho/reckon
reckon template specs > reckon.yml  # fill it in
reckon validate reckon.yml
```

Run `reckon --help` to see everything it can do. The formats are in [src/reckon/store/schemas](src/reckon/store/schemas).

## Development

Clone [bosun](https://github.com/victorzinho/bosun) as `~/.config/bosun`; the justfile imports its recipes.
`just --list` shows the tasks. `just verify` runs what CI runs.

- Every meaningful commit adds to `## Unreleased` in `CHANGELOG.md`.
- Every breaking change also adds what to do to `MIGRATIONS.md`.
- Every breaking change from 1.0.0 bumps the major version manually (unless it's already bumped): `uv version 2.0.0.dev0`.
