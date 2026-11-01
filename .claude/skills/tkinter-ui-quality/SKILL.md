---
name: tkinter-ui-quality
description: >
  Use whenever creating, modifying, reviewing, or refactoring a Tkinter/ttk GUI.
  Enforces a consistent modern desktop UI using ttk + sv-ttk, system light/dark
  mode, disciplined spacing, accessible contrast, keyboard usability, DPI-safe
  layouts, and verification before completion.
---

# Tkinter UI Quality

## Purpose

Produce **clean, consistent, readable, desktop-native GUIs**.

The UI must look like one coherent application, not a collection of Tkinter widgets.

This skill applies to:

- new windows or dialogs;
- layout changes;
- menus;
- forms;
- theme changes;
- new controls;
- visual refactors;
- GUI code review.

## Project baseline

Assume this stack unless the repository explicitly says otherwise:

- Python 3.13.
- `tkinter` + `ttk`.
- Root: `tkinterdnd2.TkinterDnD.Tk()` with fallback to `tk.Tk()`.
- Theme: `sv-ttk`.
- OS theme detection: `darkdetect`.
- Windows titlebar integration: `pywinstyles`, with DWM fallback.
- Third-party GUI dependencies are optional and must degrade gracefully.
- Custom native-looking menubar may use `tk.Frame` + `tk.Label`.
- Configuration is persisted separately from presentation code.

Do not replace this stack with another GUI framework unless explicitly requested.

---

# Mandatory principles

## 1. Theme owns the visual system

Use `ttk` + `sv-ttk` as the primary visual system.

Do **not**:

- recreate the theme manually;
- introduce a project-wide custom `ttk.Style`;
- add arbitrary widget palettes;
- mix multiple visual systems.

Custom styling is allowed only when `sv-ttk` cannot style the widget or platform surface.

Typical exceptions:

- `tk.Text`;
- custom `tk.Frame` / `tk.Label` menubar;
- `Toplevel` background;
- Windows native titlebar/menu integration.

Keep such overrides minimal and centralized.

---

## 2. Color must have meaning

Use neutral colors for:

- backgrounds;
- surfaces;
- borders;
- normal text.

Use accent colors only for semantic states:

- primary action;
- success;
- warning;
- error;
- selected/active state.

Never add colors only for decoration.

Requirements:

- normal text should target at least `4.5:1` contrast;
- secondary text must remain clearly readable;
- color must never be the only state indicator;
- light and dark mode must both remain usable.

Do not invent new colors when the existing theme already provides the required state.

---

## 3. Use a fixed spacing scale

Use only this spacing scale unless there is a concrete layout reason:

`4 / 8 / 12 / 16 / 24 / 32`

Defaults:

- label → related control: `4–8 px`;
- controls in one group: `8–12 px`;
- groups: `16–24 px`;
- window/panel outer margin: `16–24 px`.

Do not scatter arbitrary `padx` / `pady` values through the code.

Prefer shared constants when several views use the same spacing.

---

## 4. Layout must be resilient

Prefer `grid()` for application layouts.

Every resizable view must explicitly define:

- expandable rows;
- expandable columns;
- widget `sticky`;
- minimum useful size where necessary.

Use `rowconfigure()` / `columnconfigure()` with appropriate `weight`.

Avoid:

- pixel-perfect absolute positioning;
- magic geometry values;
- fixed sizes when content should grow;
- layouts that only work at one window size.

The main content area should normally absorb extra space.

No horizontal scrollbars: wrap text, ellipsize with a tooltip, or let a column stretch;
vertical scrollbars only when content exceeds the viewport and auto-hide when it fits
(`AutoScrollbar` in `src/gui/windows/autoscroll.py`).

---

## 5. Establish obvious hierarchy

A user should identify the primary task within a few seconds.

Each view should have:

1. clear context/title when needed;
2. primary content;
3. supporting/secondary content;
4. actions.

Use spacing before borders.

Do not add frames, separators, `LabelFrame`s, lines, or boxes unless they clarify grouping.

Whitespace is valid UI.

---

## 6. Typography stays simple

Use system/theme fonts.

Maintain a small hierarchy:

- title/section heading;
- normal text;
- secondary text.

Avoid:

- decorative fonts;
- excessive bold;
- ALL CAPS;
- shrinking text to make layout fit;
- many font sizes.

Text hierarchy should come primarily from placement, spacing, and limited weight differences.

---

## 7. Actions must be predictable

There should normally be at most **one visually dominant primary action per context**.

Use explicit verbs:

- `Extract`
- `Browse`
- `Save`
- `Cancel`

Avoid vague labels such as:

- `OK` when a specific action exists;
- `Go`;
- `Do it`.

Do not give every button equal visual emphasis.

Destructive actions must be clearly distinguishable and confirmed when accidental execution has meaningful consequences.

---

## 8. Interactive states must exist

Interactive controls must expose the states relevant to them:

- normal;
- hover;
- focus;
- pressed;
- selected;
- disabled;
- error.

Do not fake disabled state by changing text color alone.

Do not remove visible keyboard focus indicators.

---

## 9. Forms must scan easily

Use one consistent label strategy within a form:

- label above input; or
- aligned label column.

Do not mix strategies randomly.

Related inputs should use similar widths.

Show:

- units beside numeric values when relevant;
- validation close to the affected control;
- concise error messages.

Prefer inline validation for minor input errors.

Use modal dialogs only when the message genuinely requires interruption.

---

## 10. Dialogs and Toplevels

Dialogs must:

- use an appropriate parent;
- appear centered relative to that parent where practical;
- avoid visible repositioning/flicker;
- be themed before final presentation when possible;
- have a useful minimum size;
- support `Escape` when safe.

Do not create:

- huge windows for tiny forms;
- tiny dialogs with compressed content;
- dialogs that appear partially off-screen.

For this project, keep dialogs hidden until geometry/theme setup is complete when required by the existing implementation.

---

## 11. Menus

Custom menus must behave like menus, not floating panels.

Expected behavior:

- close on `Escape`;
- close on focus loss/click outside as appropriate;
- do not immediately reopen from the same click that closed them;
- disabled actions should be visibly disabled;
- group commands only when grouping has semantic value.

Do not use `grab_set()` or `transient()` if the established menu implementation intentionally avoids them.

Preserve the project's `_suppress`-style protection against close/reopen races.

---

## 12. Keyboard accessibility

Every important action must be usable without a mouse.

Requirements:

- visible focus;
- logical `Tab` order;
- `Shift+Tab` behaves correctly;
- `Escape` closes temporary UI where safe;
- default/primary actions may support `Enter` where appropriate.

Do not make hover the only way to discover functionality.

---

## 13. DPI and scaling

The GUI must remain usable under Windows display scaling.

Target checks:

- 100%;
- 125%;
- 150%;
- 200%.

Avoid assumptions based on physical pixel dimensions.

Do not use fixed geometry merely because it looks correct at 100%.

Long labels, translated text, and OS font scaling must not silently clip important controls.

---

## 14. Iconography — Fluent System Icons

Use **Microsoft Fluent System Icons — Regular** as the default icon set.

### Rules

- Use `fluent-regular` as the primary icon style.
- Do not mix Fluent with Lucide, Font Awesome, Material Icons, emojis, or arbitrary SVG sets.
- Prefer **16 px** for compact controls and **20 px** for normal buttons/toolbars.
- Use **24 px** only when the icon has higher visual importance.
- Avoid scaling icons to arbitrary sizes.
- Use `Regular` icons for normal/default states.
- Use `Filled` only when it communicates a meaningful state such as selected, active, enabled, or highlighted.
- Do not use `Filled` merely for decoration. Only Regular glyphs are baked; a Filled icon would need a different generation source (for example the `fluent-filled` extra of `tkinter-icons` wired into `packaging/tools/generate_icons.py`) and its own variant rules.
- Project rule (owner decision): every push button (`ttk.Button` and `tk.Button`) carries icon + text, in every window and dialog. Menu bar labels and menu bar dropdown rows, checkbuttons, radiobuttons, comboboxes, tooltips and native OS dialogs (`messagebox`, `filedialog`) are excepted. Icon-only is reserved for compact list controls (move up/down, add, remove in list editors) and always has a tooltip.
- Project rule (owner decision): every row of a popup context menu (right-click, Shift+F10, Menu key; `menus.show_context_menu`) carries a 16 px icon + text, given as `(label, icon, command)`; the icon column is aligned by the shared row helper (the gap is padded into the image), disabled rows use the `disabled` variant. The menu bar dropdowns (File/Edit/Engines) stay text-only; Options and Help are direct-action labels that open their dialog on click (no dropdown).
- A button that only repeats a menu item is not added; the menu is the single entry point for that action.
- Every icon-only control must provide a tooltip or equivalent accessible description.
- Never use an icon whose meaning is ambiguous in context.
- Use the same icon consistently for the same action throughout the application.
- Do not use multiple icons to communicate one simple action.
- Icons must inherit or adapt to the current light/dark theme.
- Do not hardcode icon colors unless required for a semantic state.
- Normal icons should use the same foreground hierarchy as surrounding controls.
- Reserve semantic colors for states such as error, warning, success, or destructive actions.
- Disabled icons must follow the disabled visual state of the corresponding control.
- Keep sufficient spacing between icon and text, normally `6–8 px`.
- Icons must remain visually centered inside their control.
- Do not compensate for badly aligned icons with arbitrary per-widget padding; fix alignment at the shared component/helper level.
- Keep strong contrast at small sizes and avoid icons with excessive internal detail.
- Never replace the text label with an icon on a push button; the icon sits left of the text with an 8 px gap produced by the shared factory.

### Preferred mapping

Use established Fluent metaphors whenever possible:

- folder → browse/open directory;
- document → file;
- folder-open → open;
- save → save;
- settings → configuration;
- search → search/scan;
- arrow-clockwise → refresh/retry;
- play → start/run;
- stop → stop/cancel running operation;
- dismiss → close/remove;
- delete → destructive deletion;
- info → informational state;
- warning → warning;
- error-circle → failure/error;
- checkmark-circle → success;
- shield → security/protection;
- shield-checkmark → verified/safe result.

Do not invent alternate metaphors when Fluent already provides a conventional icon.

### Implementation

Centralize icon creation instead of loading icons independently in every view.

Prefer a shared helper/component that controls:

- icon family;
- size;
- theme-aware foreground;
- regular/filled variant;
- disabled state;
- image lifetime/reference management.

Views should request semantic icons by name and should not implement their own icon styling.

#### Library and usage

Glyph source: Microsoft Fluent System Icons 1.1.261 (Regular, MIT). The running GUI has **no icon library, font or Pillow**: every icon is a pre-baked, pre-tinted transparent RGBA PNG committed under `src/gui/icons/assets/{light,dark}/`, one folder per theme, named `<semantic_name>-<size>[-<variant>].png` (sizes 16/20/24).

- Generation (dev only): `uv run --group icons python packaging/tools/generate_icons.py`. It uses `tkinter-icons[fluent-regular]` + Pillow from the dev-only `icons` dependency group (never in the `gui` extra/group), takes only the glyph alpha from `render_pil` and applies the exact color itself (the library's own RGB tint shows fringes on thin strokes), and writes deterministic PNGs (a test regenerates into a temp dir and requires byte-identical files; it skips where the `icons` group is absent). Some Fluent glyphs have no 16 px variant (`eraser`, `select-all-on`, `checkbox-unchecked` at 20): pick alternatives, the generator fails on a missing glyph.
- Variants (`catalog.variants_for`): normal (no suffix, the theme's TButton foreground), `disabled`, `accent` and `accent-disabled` (only for names in `catalog.ACCENT_ICONS`, i.e. shown on an `Accent.TButton`; a test keeps the set equal to what the views use), and one status color (`clean`, `detection`, `error`, `unavailable`) for `status_*` icons, taken from `theme.py` palettes. The ttk button foregrounds are constants at the top of `packaging/tools/generate_icons.py`, resolved from a real `ttk.Style` under sv-ttk; a test fails when sv-ttk drifts from them. There is no pressed variant: the plain image stays.
- Runtime helper: `src/gui/icons/` (`render.py` loads the PNG by theme/name/size/variant into a `tk.PhotoImage` and pads the 8 px icon-to-text gap with a Tk image copy so it follows DPI; `controls.py` picks the size step, variant and theme, and swaps every live icon to the other folder on `<<ThemeChanged>>`). The assets folder is `Path(__file__).parent/'assets'`, or `sys._MEIPASS/gui/icons/assets` in the exe (`--add-data` in `packaging/tools/build_exe.py`). A missing folder or file leaves the widget text-only.
- Adding an icon: add `semantic: glyph` to `GLYPHS` in `catalog.py` (one glyph per meaning; add to `COLOR_ROLES` for a status color, to `ACCENT_ICONS` if it sits on an accent button), run the generator, commit the PNGs together with the catalog change, and use the semantic name in the view. Changing a theme/status color also means regenerating.
- Views use semantic names only: `icons.button(parent, "Scan", "scan", cmd, style=...)` (the only way to create a labelled push button; a test fails on any other `Button(` in `gui`), `icons.IconButton(parent, "move_up", "Move up", cmd, tip=..., fallback_text=...)`, `icons.attach(button, name)`, `button_row(parent, ("Save", "save", cmd), ("Cancel", "dismiss", cmd))` (the icon is named per entry, never derived from the label), `icons.set_status_icons(tree, {tag: name})` / `icons.status_image(...)`. The semantic-to-glyph table is `src/gui/icons/catalog.py`; current mapping (all Fluent Regular, one glyph per name, each verified at 16/20/24):

| Semantic | Glyph | Used for |
|---|---|---|
| `browse` | `folder-open` | Browse |
| `scan` | `search` | Scan |
| `stop` | `stop` | Stop |
| `add` | `add` | Add engine / Add rule / Add profile, list Add |
| `remove` | `subtract` | Remove profile, list Remove |
| `move_up` / `move_down` | `arrow-up` / `arrow-down` | list Move |
| `duplicate` | `document-copy` | Duplicate engine |
| `copy` | `copy` | Copy (debug), Copy results, Copy selection / all |
| `delete` | `delete` | Delete engine |
| `validate` | `checkmark` | Validate |
| `save` | `save` | Save, Save results |
| `dismiss` | `dismiss` | Cancel, Close |
| `set_default` | `star` | Set as default (profiles) |
| `info` | `info` | Variables help button |
| `go_to` | `arrow-right` | Go to first problem (validation alert) |
| `reload` | `arrow-clockwise` | Reload |
| `run` | `play` | Run test |
| `send` | `send` | Send input |
| `regex_test` | `beaker` | Regex tester launcher |
| `build_rule` | `wand` | Build detection rule |
| `select_all` | `checkbox-checked` | Select all engines |
| `select_available` | `filter` | Select available engines |
| `clear_selection` | `dismiss-circle` | Clear engine selection |
| `clear` | `broom` | Clear log, Clear pane, Clear results (not `delete`: it empties, it deletes nothing) |
| `copy_bbcode` | `code` | Copy results as BBCode (context menu) |
| `open_detail` | `open` | Open detail (context menu) |
| `status_clean` / `status_detection` / `status_error` / `status_unavailable` | `checkmark-circle` / `warning` / `error-circle` / `subtract-circle` | Result status rows (semantic color) |

- Treeview: set the image per item (`item(image=...)`); `tag_configure(image=...)` is not drawn by sv-ttk. The `#0` column reserves ~32 px before the image.

### Review checklist

Before considering iconography complete:

- [ ] Only Fluent icons are used.
- [ ] Sizes follow the `16 / 20 / 24 px` scale.
- [ ] Regular/filled variants have semantic meaning.
- [ ] Every push button has icon + text; icon-only controls are compact list buttons with a tooltip.
- [ ] Light and dark mode remain readable.
- [ ] Disabled states are visible.
- [ ] The same action uses the same icon everywhere.
- [ ] Icons remain recognizable at actual UI size.
- [ ] No button duplicates a menu item.
- [ ] Context-menu rows carry icon + text; menu bar dropdowns are text-only.

---

# Forbidden patterns

Do not:

- invent a custom application palette when `sv-ttk` already solves the problem;
- add gradients for decoration;
- use saturated backgrounds;
- mix multiple accent colors without semantic meaning;
- use emojis as primary icons;
- use unexplained icon-only controls;
- put everything inside `LabelFrame`;
- center long paragraphs;
- fill empty space merely because it exists;
- add shadows/borders/lines without purpose;
- use inconsistent spacing;
- create one-off fonts or colors inside individual views;
- replace standard controls purely to make them look "more modern";
- sacrifice readability for density;
- claim visual quality was verified when it was not actually checked.

---

# Implementation workflow

## Before coding

For every meaningful GUI change, determine:

1. What is the primary user task?
2. What is the primary action?
3. Which controls belong together?
4. What expands when the window grows?
5. What happens in light and dark mode?
6. What happens using keyboard only?
7. What happens at high DPI?

For a non-trivial screen, state the intended layout hierarchy before implementation.

Do not begin by choosing colors.

---

## During implementation

Prefer, in order:

1. existing project components;
2. standard `ttk` widgets;
3. `sv-ttk` behavior;
4. minimal centralized overrides;
5. custom drawing only when technically necessary.

If a new helper/style abstraction is introduced, it must remove duplication or enforce consistency across multiple views.

Do not create abstractions solely for aesthetic experimentation.

---

# Mandatory verification

Before declaring GUI work complete, verify all applicable items.

## Visual

- [ ] Light mode is readable.
- [ ] Dark mode is readable.
- [ ] No accidental low-contrast text.
- [ ] No arbitrary colors.
- [ ] Spacing follows the defined scale.
- [ ] Alignment is visually consistent.
- [ ] Primary action is obvious.
- [ ] Secondary controls do not compete visually.

## Layout

- [ ] Window resize behaves correctly.
- [ ] Main content expands correctly.
- [ ] No unexpected clipping.
- [ ] Minimum useful size is enforced when needed.
- [ ] Long text does not break the view.

## Interaction

- [ ] `Tab` order follows visual order.
- [ ] Keyboard focus is visible.
- [ ] `Escape` behaves correctly.
- [ ] Disabled controls are truly disabled.
- [ ] Menus/dialogs close correctly.
- [ ] No menu close/reopen race.

## Scaling

When the environment permits, test:

- [ ] 100% DPI.
- [ ] 125% DPI.
- [ ] 150% DPI.
- [ ] 200% DPI.

If a DPI level or visual state was not actually tested, state that explicitly instead of claiming full verification.

---

# Review protocol

When reviewing GUI code, classify findings as:

### Critical

The UI is unusable or misleading.

Examples:

- unreadable text;
- inaccessible primary action;
- broken layout;
- controls unreachable by keyboard;
- dialog outside visible screen.

### Important

The UI works but violates consistency or expected desktop behavior.

Examples:

- inconsistent spacing;
- wrong resize behavior;
- competing primary actions;
- custom colors fighting the theme;
- missing focus state.

### Minor

Polish issue without meaningful usability impact.

Examples:

- slightly inconsistent padding;
- unnecessary separator;
- wording that can be clearer.

Fix `Critical` and `Important` findings before considering the GUI complete.

---

# Agent handoff contract

When multiple agents are used:

- the implementation agent must receive this skill or its rules;
- the reviewer must evaluate against this skill, not personal aesthetic taste;
- visual review findings must cite the violated rule;
- do not accept "looks good" as verification;
- use screenshots when the execution environment makes them available;
- use code inspection for layout/state rules that screenshots cannot prove.

Recommended sequence for non-trivial GUI work:

`requirements → layout plan → implementation → visual/behavior review → fixes → verification`

---

# Completion criteria

A screen is complete only when:

- the main task is understandable immediately;
- alignment and spacing look intentional;
- light and dark mode remain coherent;
- resize does not break the layout;
- keyboard navigation works;
- controls expose proper states;
- DPI scaling does not rely on fragile pixel assumptions;
- no decorative element lacks a clear function;
- the screen looks like part of the same application as every other screen.

## Final rule

**Prefer consistency, native behavior, readability, and simplicity over visual novelty.**

If a visual change does not improve hierarchy, readability, state communication, or usability, do not add it.
