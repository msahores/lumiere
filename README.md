# lumière

Minimal TUI to control display brightness, keyboard backlight, and night mode on Linux.

```
LUMIERE   j/k select  h/l adjust  q quit

▸ Display   ██████████████████░░░░░░░░  65%
  Keyboard  ██ ░░                        1/2
  Night     ████████░░░░░░░░░░░░░░░░░░  3500K
```

## Features

- **Display brightness** — continuous slider (5% steps)
- **Keyboard backlight** — auto-adapts to hardware levels (discrete blocks for ≤10 levels, continuous bar for more)
- **Night mode** — color temperature from 6500K (daylight) to 1000K (deep red), resets on exit
- **Auto-detection** — finds your backlight and keyboard devices automatically
- **Zero dependencies** — just Python 3.8+ and standard library (curses)
- **Graceful degradation** — keyboard row hidden if no kbd backlight, night row hidden if gammastep not installed

## Requirements

- [brightnessctl](https://github.com/Hummer12007/brightnessctl) — screen and keyboard control
- [gammastep](https://gitlab.com/chinstrap/gammastep) *(optional)* — night mode / color temperature

### Arch Linux

```sh
sudo pacman -S brightnessctl gammastep
```

## Install

```sh
pip install .
```

Or run directly:

```sh
python3 lumiere.py
```

## Controls

| Key | Action |
|---|---|
| `j` / `↓` | Select next |
| `k` / `↑` | Select previous |
| `l` / `→` | Increase |
| `h` / `←` | Decrease |
| `q` / `Esc` | Quit |

## License

MIT
