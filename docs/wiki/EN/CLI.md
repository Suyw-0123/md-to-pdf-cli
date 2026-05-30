# CLI (`cli.py`)

The command-line interface is built with [Typer](https://typer.tiangolo.com/).
Its job is thin: parse arguments, load + override config, call
`converter.convert()`, and present clean success/error output.

## Commands

| Command | Purpose |
|---------|---------|
| `md2pdf <file.md>` | Convert (shorthand — see *default command* below). |
| `md2pdf convert <file.md>` | Convert, explicit form. |
| `md2pdf init [DIR]` | Scaffold `md2pdf.toml` + `theme.css`. |
| `md2pdf --version` | Print version and exit. |

## The default-command trick: `DefaultGroup`

By default Typer/Click would reject `md2pdf report.md` because `report.md` is not
a known subcommand. We want `md2pdf <file>` to mean `md2pdf convert <file>`
without losing real subcommands like `init`.

`DefaultGroup(TyperGroup)` (cli.py:31) overrides `resolve_command`:

```python
def resolve_command(self, ctx, args):
    try:
        return super().resolve_command(ctx, args)   # real subcommand?
    except UsageError:
        if args and not args[0].startswith("-"):     # looks like a file, not a flag
            return super().resolve_command(ctx, [self.default_command, *args])
        raise
```

So an unknown first arg that isn't a flag is retried as `convert <arg>`. A bare
`-o` with no command still raises (correctly), because the guard requires the
first arg to not start with `-`.

### Typer vendors Click

Typer 0.26.3 vendors Click under `typer._click`. That is why the imports are:

```python
from typer._click.core import Context as ClickContext
from typer._click.exceptions import UsageError
```

Importing the top-level `click` package would fail (`ModuleNotFoundError: No
module named 'click'`) in this environment. If you bump Typer, re-check these
import paths.

## Flags and how they override config

`convert` declares one Typer `Option` per overridable setting. Each defaults to
`None`, meaning "not provided on the CLI." `_apply_overrides()` (cli.py:130) then
mutates the loaded `Config` **only for the flags the user actually passed** —
this is what implements *CLI > file > defaults* precedence.

Notable details:

- `--margin 2cm` expands into a `Margin(top, bottom, left, right)` all-sides
  value.
- `--css` is repeatable and **appended** to the config's CSS list, so CLI CSS
  wins (later files override earlier ones). CLI CSS paths resolve against the
  **CWD** (`p.resolve()`), unlike config-file CSS which resolves against the
  config file's directory.
- `--header`/`--footer` both *enable* the banner and set its template in one go.
- Boolean pairs like `--toc/--no-toc` are tri-state (`None`/`True`/`False`) so we
  can tell "unset" from "explicitly off."

> **B008 note:** ruff's B008 ("function call in default argument") is *ignored*
> project-wide because calling `typer.Option(...)`/`typer.Argument(...)` in
> defaults is Typer's required idiom, not a bug.

## `init`

`init` writes two starter files from the in-module `_SAMPLE_TOML` and
`_SAMPLE_CSS` constants. It skips existing files unless `--force` is given, and
prints the next step (install Chromium, then run). If you change the default
config shape, update `_SAMPLE_TOML` to match.

## Output and error presentation

- Success: `✓ input → output` (green) via a stdout `rich.Console`.
- Errors: a separate stderr `Console`. Three `except` arms map exceptions to
  messages and exit code 1 (see [Architecture → Failure handling](Architecture.md)).
  Note the `raise typer.Exit(code=1) from exc` form — `from exc` satisfies ruff
  B904 and preserves the cause.
