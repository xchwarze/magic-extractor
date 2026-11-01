---
name: cli-design
description: >
  Use whenever creating, modifying, reviewing, or documenting a command-line interface.
  Enforces predictable CLI behavior, stable arguments, correct stdout/stderr usage,
  meaningful exit codes, scripting compatibility, and Windows-safe invocation.
---

# CLI Design

## Purpose

Create CLIs that are predictable for both humans and automation.

Apply this skill to:

- new commands;
- argument changes;
- exit codes;
- stdout/stderr behavior;
- batch mode;
- help text;
- Windows Explorer invocation;
- scripting compatibility;
- CLI/GUI shared entry points.

---

# Core principles

A CLI is an API.

Treat these as compatibility surfaces:

- command names;
- flags;
- positional arguments;
- exit codes;
- stdout format;
- stderr behavior.

Do not change them casually.

---

# Argument design

Prefer:

```text
tool <input> [options]
```

Use positional arguments for required primary operands.

Use flags for optional behavior.

Good:

```text
tool file.bin --output out --force
```

Avoid:

```text
tool --input file.bin --output out --mode extract --yes true
```

when the command has one obvious primary operation.

Keep names concise and conventional.

Prefer:

- `-o`, `--output`;
- `-f`, `--force`;
- `-v`, `--verbose`;
- `-q`, `--quiet`;
- `--version`;
- `--help`.

Do not invent unconventional names without reason.

---

# Help

`--help` must:

- explain the command purpose;
- show usage;
- explain positional arguments;
- explain options;
- avoid implementation details;
- include defaults when useful.

Keep descriptions short.

The first line should explain what the tool does.

---

# Exit codes

Use exit codes consistently.

Minimum rule:

- `0`: success;
- non-zero: failure.

If multiple codes exist, document them and keep them stable.

Do not return `0` after a partial/failed operation unless partial success is explicitly part of the contract.

---

# stdout vs stderr

Use `stdout` for intended program output.

Use `stderr` for:

- errors;
- warnings;
- diagnostics;
- progress when it should not contaminate machine-readable stdout.

Do not print errors to stdout by default.

This matters for:

```text
tool input > result.txt
```

---

# Machine-readable output

If structured output is needed, make it explicit.

Example:

```text
--json
```

When `--json` is enabled:

- stdout should contain valid JSON only;
- diagnostics go to stderr;
- avoid decorative text;
- keep schema stable where practical.

Do not mix human prose with JSON output.

---

# Interactive behavior

Default behavior should be non-interactive when practical.

Do not block automation with unexpected prompts.

If confirmation is required, provide a bypass flag such as:

```text
--force
```

or:

```text
--yes
```

Interactive prompts must never appear in documented non-interactive modes.

---

# Batch behavior

Batch commands must define:

- what happens after one item fails;
- whether processing continues;
- what exit code represents partial failure;
- where per-item errors are reported.

Do not silently skip failed items.

---

# Windows invocation

Assume commands may be launched from:

- PowerShell;
- cmd.exe;
- Explorer context menu;
- another Python process;
- a frozen executable;
- a GUI frontend.

Paths may contain:

- spaces;
- Unicode;
- parentheses;
- punctuation.

Never depend on naive string splitting.

---

# Explorer integration

When the CLI can be invoked from Explorer, preserve a stable entry pattern.

Example project convention:

```text
tool.exe <file> [<outdir>|/scan]
```

Do not break Explorer integration when redesigning CLI parsing.

If legacy argument forms exist, keep backward compatibility unless the spec explicitly removes them.

---

# Parsing

Use one parser entry point.

Do not parse `sys.argv` manually in multiple modules.

Centralize argument parsing.

Prefer explicit normalization after parsing rather than mixing business logic into parser callbacks.

---

# CLI and GUI separation

The CLI must not own backend logic.

Preferred flow:

```text
argv
 ↓
parser
 ↓
validated request/options
 ↓
shared backend
 ↓
result
 ↓
exit code + output
```

The GUI should call the same backend.

Do not invoke the CLI subprocess from the GUI merely to reuse business logic unless process isolation is intentionally required.

---

# Errors

Errors should answer:

1. what failed;
2. what input caused it;
3. what the user can do next, when useful.

Good:

```text
error: input file does not exist: C:\data\sample.bin
```

Avoid:

```text
Something went wrong.
```

Do not dump tracebacks for expected user errors.

Tracebacks belong to debug/verbose modes or logs.

---

# Progress

Progress output should be optional when it harms scripting.

If stdout is used as machine-readable output, progress belongs on stderr.

Avoid noisy per-item output for large batches unless requested.

---

# Verbosity

Recommended convention:

- default: concise;
- `--verbose`: additional operational detail;
- `--quiet`: suppress non-essential output.

Do not make default mode excessively chatty.

---

# Destructive operations

Destructive commands must be explicit.

Require one or more of:

- specific destructive subcommand;
- confirmation;
- `--force`;
- exact target.

Do not infer destructive intent from ambiguous arguments.

---

# Stable behavior

Avoid changing:

- option names;
- default output location;
- exit codes;
- stdout format;

without a spec-level reason.

If behavior changes intentionally, update:

- help;
- tests;
- docs;
- GUI integration if applicable.

---

# Testing

Test parsing separately from backend logic.

Minimum cases:

- valid invocation;
- missing required argument;
- unknown option;
- path with spaces;
- Unicode path;
- invalid file;
- invalid output directory;
- backend failure;
- success exit code;
- failure exit code.

If Explorer integration exists, test its exact argv shape.

---

# Mandatory verification

Before completion:

- [ ] `--help` works.
- [ ] success returns `0`.
- [ ] expected failures return non-zero.
- [ ] errors go to stderr.
- [ ] normal output goes to stdout.
- [ ] path with spaces works.
- [ ] Unicode path works.
- [ ] non-interactive use does not prompt unexpectedly.
- [ ] legacy invocation remains compatible where required.
- [ ] GUI/backend behavior is not duplicated in CLI parsing code.

If a case was not tested, say so explicitly.

---

# Review priorities

## Critical

- wrong exit code causing automation to mis-detect failure;
- destructive behavior from ambiguous arguments;
- command injection;
- path parsing failure;
- stdout corruption in machine-readable mode.

## Important

- errors printed to stdout;
- unexpected prompts;
- duplicated backend logic;
- broken backward compatibility;
- unclear argument semantics.

## Minor

- overly verbose help;
- inconsistent option naming;
- redundant aliases.

Fix Critical and Important findings before completion.

---

# Final rule

Design the CLI as a stable programmatic interface first and a human-facing wrapper second.
