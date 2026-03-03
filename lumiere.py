#!/usr/bin/env python3
"""lumiere — Minimal TUI for display brightness, keyboard backlight, and night mode."""
import curses
import os
import shutil
import subprocess
import sys

SCREEN_STEP = 5   # percent
TEMP_MIN = 1000   # K (max warm / red)
TEMP_MAX = 6500   # K (neutral daylight)
TEMP_STEP = 250   # K per keypress

def detect_devices():
    """Auto-detect backlight and keyboard LED devices."""
    screen = kbd = None
    r = subprocess.run(["brightnessctl", "-m", "--list"],
                       capture_output=True, text=True)
    for line in r.stdout.strip().splitlines():
        parts = line.split(",")
        name, cls = parts[0], parts[1]
        if cls == "backlight" and not screen:
            screen = name
        elif "kbd" in name.lower() and cls == "leds":
            kbd = name
    return screen, kbd

def has_gammastep():
    r = subprocess.run(["which", "gammastep"], capture_output=True)
    return r.returncode == 0

def get_brightness(device):
    r = subprocess.run(["brightnessctl", "-d", device, "-m"],
                       capture_output=True, text=True)
    parts = r.stdout.strip().split(",")
    return int(parts[2]), int(parts[4])

def set_brightness(device, value):
    subprocess.run(["brightnessctl", "-d", device, "set", value],
                   capture_output=True)

def set_temperature(temp, gs_proc):
    """Kill previous gammastep and start with new temperature."""
    if gs_proc and gs_proc.poll() is None:
        gs_proc.terminate()
        gs_proc.wait()
    if temp >= TEMP_MAX:
        return None  # neutral, no filter needed
    proc = subprocess.Popen(
        ["gammastep", "-O", str(temp), "-P"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc

def reset_temperature(gs_proc):
    """Reset screen to neutral color."""
    if gs_proc and gs_proc.poll() is None:
        gs_proc.terminate()
        gs_proc.wait()
    subprocess.run(["gammastep", "-x"],
                   capture_output=True, stderr=subprocess.DEVNULL)

def draw_bar(win, y, x, width, pct):
    filled = int(width * pct / 100)
    bar = "\u2588" * filled + "\u2591" * (width - filled)
    win.addstr(y, x, bar)

def main(stdscr):
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_YELLOW, -1)
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    curses.init_pair(3, curses.COLOR_RED, -1)
    curses.init_pair(4, curses.COLOR_WHITE, -1)
    stdscr.timeout(100)

    screen_dev, kbd_dev = detect_devices()
    if not screen_dev:
        stdscr.addstr(1, 2, "No backlight device found.")
        stdscr.getch()
        return

    gs_available = has_gammastep()
    gs_proc = None
    temp = TEMP_MAX  # start neutral

    devices = ["screen"]
    if kbd_dev:
        devices.append("kbd")
    if gs_available:
        devices.append("night")

    sel = 0

    def cleanup():
        reset_temperature(gs_proc)

    try:
        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            bar_w = min(40, w - 22)
            row = 1

            stdscr.addstr(row, 2, "LUMIERE",
                          curses.A_BOLD | curses.color_pair(4))
            help_txt = "  j/k select  h/l adjust  q quit"
            if w > len(help_txt) + 14:
                stdscr.addstr(row, 13, help_txt, curses.color_pair(4))
            row += 2

            # Screen
            scur, smax = get_brightness(screen_dev)
            spct = round(scur * 100 / smax)
            attr = curses.A_BOLD if sel == 0 else 0
            marker = "\u25b8 " if sel == 0 else "  "
            stdscr.addstr(row, 2, f"{marker}Display  ",
                          attr | curses.color_pair(1))
            draw_bar(stdscr, row, 14, bar_w, spct)
            stdscr.addstr(row, 15 + bar_w, f" {spct:3d}%",
                          curses.color_pair(1))
            row += 2

            # Keyboard
            if kbd_dev:
                kcur, kmax = get_brightness(kbd_dev)
                ki = devices.index("kbd")
                attr = curses.A_BOLD if sel == ki else 0
                marker = "\u25b8 " if sel == ki else "  "
                stdscr.addstr(row, 2, f"{marker}Keyboard ",
                              attr | curses.color_pair(2))
                if kmax <= 10:
                    for i in range(kmax):
                        ch = "\u2588" if i < kcur else "\u2591"
                        stdscr.addstr(row, 14 + i * 2, f"{ch} ",
                                      curses.color_pair(2))
                    label = "OFF" if kcur == 0 else f"{kcur}/{kmax}"
                    stdscr.addstr(row, 14 + kmax * 2 + 1, label,
                                  curses.color_pair(2))
                else:
                    kpct = round(kcur * 100 / kmax)
                    draw_bar(stdscr, row, 14, bar_w, kpct)
                    stdscr.addstr(row, 15 + bar_w, f" {kpct:3d}%",
                                  curses.color_pair(2))
                row += 2

            # Night mode
            if gs_available:
                ni = devices.index("night")
                attr = curses.A_BOLD if sel == ni else 0
                marker = "\u25b8 " if sel == ni else "  "
                stdscr.addstr(row, 2, f"{marker}Night    ",
                              attr | curses.color_pair(3))
                warmth = round((TEMP_MAX - temp) * 100
                               / (TEMP_MAX - TEMP_MIN))
                draw_bar(stdscr, row, 14, bar_w, warmth)
                if temp >= TEMP_MAX:
                    label = "  OFF"
                else:
                    label = f" {temp}K"
                stdscr.addstr(row, 15 + bar_w, label,
                              curses.color_pair(3))

            stdscr.refresh()

            key = stdscr.getch()
            if key == ord("q") or key == 27:
                break
            elif key in (curses.KEY_UP, ord("k")):
                sel = max(sel - 1, 0)
            elif key in (curses.KEY_DOWN, ord("j")):
                sel = min(sel + 1, len(devices) - 1)
            elif key in (curses.KEY_RIGHT, ord("l")):
                dev = devices[sel]
                if dev == "screen":
                    set_brightness(screen_dev, f"+{SCREEN_STEP}%")
                elif dev == "kbd":
                    kcur, kmax = get_brightness(kbd_dev)
                    step = max(1, kmax // 20) if kmax > 10 else 1
                    set_brightness(kbd_dev, str(min(kcur + step, kmax)))
                elif dev == "night":
                    temp = max(temp - TEMP_STEP, TEMP_MIN)
                    gs_proc = set_temperature(temp, gs_proc)
            elif key in (curses.KEY_LEFT, ord("h")):
                dev = devices[sel]
                if dev == "screen":
                    set_brightness(screen_dev, f"{SCREEN_STEP}%-")
                elif dev == "kbd":
                    kcur, kmax = get_brightness(kbd_dev)
                    step = max(1, kmax // 20) if kmax > 10 else 1
                    set_brightness(kbd_dev, str(max(kcur - step, 0)))
                elif dev == "night":
                    temp = min(temp + TEMP_STEP, TEMP_MAX)
                    gs_proc = set_temperature(temp, gs_proc)
    finally:
        cleanup()

def _find_terminal():
    """Find a terminal emulator using standard methods, then common fallbacks."""
    for term in (
        os.environ.get("TERMINAL"),     # user preference
        "xdg-terminal-exec",            # freedesktop standard
        "x-terminal-emulator",          # Debian/Ubuntu alternatives
        "alacritty", "foot", "kitty",   # modern
        "st", "urxvt", "xterm",         # classic
    ):
        if term and shutil.which(term):
            return term
    return None

def main_entry():
    if not os.isatty(sys.stdin.fileno()):
        term = _find_terminal()
        if not term:
            sys.exit("lumiere: no terminal emulator found (set $TERMINAL)")
        os.execvp(term, [term, "-e", sys.executable, __file__])
    curses.wrapper(main)

if __name__ == "__main__":
    main_entry()
