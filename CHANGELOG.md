# Changelog

## Unreleased

- New command `specs`: every spec (`[<name>.]reckon.yml`) under a directory, validated.
- New command `audit-report`: every audit file (`[<name>.]reckon.audit[.<auditor>].yml`) under a directory, validated.
- New command `validate`: what makes a spec or audit file invalid, including an audit's assessments that don't
  match the spec it's named after.
- New command `template`: a spec or audit file to fill in, with each field described.
