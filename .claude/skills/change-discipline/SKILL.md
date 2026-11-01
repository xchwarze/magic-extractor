---
name: change-discipline
description: >
  Use for any code change in this repository, before editing. Classifies the
  change's risk, sets how much proof it needs, requires a regression test seen
  failing for behavior fixes, an independent adversarial review for risky
  changes, and reports only what a recorded run proved. Distilled from the
  "rabbit" engineering kit (gims), without its tooling.
---

# Change discipline

Depth follows risk. Judgment decides what to test; runs decide whether it passed.

## 1. Classify first

Pick the tier before editing. When unsure, take the higher one.

- **Trivial** — no observable behavior change (docs, comments, renames inside one
  module), or a localized fix that restores clearly intended behavior and touches
  no contract below.
- **Standard** — every other change: a new handler, a new option, a changed message.
- **High** — anything that can lose or overwrite user data, or a contract other
  code relies on. In this repo that means:
  - deleting or moving files: `--delete-source`, `merge_move`, staging cleanup
    (`extract_atomically`), output-folder resolution (`resolve_output_dir`);
  - the candidate chain and routing: `handlers.json` format, registry order,
    `PE_INSTALLER_FALLBACK`, `failure_markers`;
  - how extractors are invoked (`run_command`, `run_extraction`, stdin, timeouts);
  - the CLI flags and exit codes the GUI (`src/gui/runner.py`) builds on, and the
    `config.ini` keys the GUI Preferences read and write;
  - the release workflow, PyInstaller options, the updater (`update/`).
  A new test harness or detection technique is at least Standard.

| | Trivial | Standard | High |
|---|---|---|---|
| Regression test | behavior fix only | yes | yes |
| Red seen before the fix | behavior fix only | yes | yes |
| Verification | unit | unit + the battery the change touches | unit + both batteries + manual flow |
| Independent review | no | recommended | required (two lenses for big changes) |
| Ask the human | no | no | before changing destructive behavior or a contract |

## 2. Prove behavior with runs, not claims

- **Claim only what a run proved.** Never say a command, test or battery passed
  without its recorded output in front of you; label anything else a claim.
  This applies to messages and commit bodies too.
- **Name the level that ran.** These are different claims:
  - unit: `python test/run_battery.py --unit-only`
  - format battery (every sample through the CLI, Windows):
    `python test/run_battery.py --battery-only`
  - engine battery (extractor contract per handler, Windows):
    `python test/run_engine_battery.py [FormatXHandler ...]`
  - manual product flow: the real CLI on a sample, or the GUI opened, driven and
    screenshotted.
  Unit green is not "it works": a user-visible flow change needs the flow run.
- **Never weaken a test to get green.** Do not delete, skip, loosen or retarget
  an assertion that fails; fix the code or report the conflict.
- **Never retry until green.** A flaky failure is a finding: report both runs.
- **Fail closed.** If a required step cannot run (no Windows for the batteries,
  missing tool), stop and say so; never substitute a weaker check silently.
- **Prove a zero-result search can find something** before trusting "no matches".

## 3. Behavior fixes: red before green

1. Write the regression test for the reported failure.
2. Run it and see it fail for the right reason (not an import error).
3. Fix the product code.
4. Run it green, then the wider level the tier requires.

A test offered as proof must be able to fail: when it matters, revert or break the
fix temporarily and watch the test go red (then restore). A test that stays green
without the fix proves nothing.

Tests assert observable behavior (outputs, files on disk, return values, exit
codes, log lines), not code structure. Keep them isolated: temporary folders,
no network, no fixed sleeps, no order dependence.

## 4. Independent, adversarial review

For High changes (recommended for Standard), get a review from a fresh agent that
receives the code and the requirement, **not your reasoning or your conclusion**.
Its job is to break the change: reproduce, attack edge cases, look for missing
evidence. Nobody reviews their own work as the mandatory review.

Reviewer output:

```text
VERDICT: APPROVED | REJECTED
[BLOCKER|MAJOR|MINOR] [measured|reasoned] <file:line> — <claim> — <evidence> — <fix>
```

- `measured`: the reviewer ran it; `reasoned`: read from the code.
- BLOCKER or MAJOR means REJECTED. A REJECTED verdict binds: fix and re-review;
  never re-ask the same reviewer with unchanged code hoping for APPROVED.
- Verify every finding yourself before acting on it; reviewers can be wrong too.

## 5. Scope and contracts

- No unrelated refactors or new dependencies without the human asking.
- Change a shared contract together with all its consumers in the same change:
  e.g. a new CLI flag → `runner.build_command` + its tests + the readme; a
  `config.ini` key → GUI Preferences (`config_io`, `option_warnings`); a new
  handler → `handlers.json` (regenerate), `ENGINE_SAMPLES`, docs.
- New option with side effects → add its warning to `src/gui/option_warnings.py`.
- When an instruction conflicts with what the repository shows, stop and report
  the evidence instead of silently following either.

## 6. Commits

- Semi-atomic Conventional Commits, one theme each, with a body that says why.
- Each commit must pass the unit tests on its own (check the staged tree in a
  scratch worktree when splitting a mixed working tree).
- Commit directly to `master`; no AI co-author trailers.
- Report results with the level that ran and the commit hashes.
