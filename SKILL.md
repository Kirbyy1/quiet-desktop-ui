---
name: quiet-desktop-ui
description: >-
  The user's own design system for desktop app UIs: flat, calm, dark-first, one green accent,
  no card boxes, with a ready-made Qt kit. Use it whenever you build, restyle or review a desktop
  app's interface, window, settings page, dialog or popup, wizard, progress or run view, toast or
  error message. This covers PyQt5, PyQt6, PySide6, Qt/QSS, Tkinter, Electron, Tauri and
  webview-based desktop apps, as well as HTML pages meant to look like a desktop app. Also use it
  when the user asks for "my design", "my style", "the quiet UI" or "like my other apps".
---

# Quiet desktop UI

This skill is the user's design system. Follow it instead of your own defaults.

## Steps

1. Read [DESIGN.md](DESIGN.md) in this folder first: tokens, type, layout, components, and
   "Flows and feedback" for any app that runs jobs. Look at the screenshots in `images/` to see
   the target.
2. **Qt app (PyQt5 or PySide6):**
   - Copy [qt/quiet_ui.py](qt/quiet_ui.py) into the project **unchanged**, next to the app's own
     modules. Do not rewrite, trim or restyle it.
   - Build every window, page, settings row, popup and progress view from its widgets:
     `make_app`, `QuietWindow`, `Page`, `CategoryView`, `SettingsSection`, `SaveState`,
     `StepDialog`, `Segmented`, `ToggleSwitch`, `DurationInput`, `CountOf`, `ItemList` /
     `ItemRow`, `Stat`, `LookupField`, `button`, `label`, and `show_error` for errors.
   - "Copy the kit" in DESIGN.md has the table of which widget fits which need, and a working
     example. [qt/demo.py](qt/demo.py) is a complete app built with the kit, to copy patterns from.
   - Change colours only through `TOKENS`, and replace `app_mark()` with the app's logo.
   - If the app already uses PyQt6 or another toolkit, keep it, and copy the values, sizes and
     behaviour from the kit and DESIGN.md.
3. **Web or webview UI:** use the CSS tokens, type scale and components from DESIGN.md exactly,
   with system fonts only.
4. **Before finishing:**
   - Run the app and take a screenshot. For Qt, `demo.py --shots` shows how to render hidden
     windows with `grab()`.
   - Compare it with the images in `images/`, and fix anything that differs.

## Rules that are easy to miss

- **Flat:** rows sit on the page background with 1px dividers. Never wrap settings rows or
  sections in "card" boxes (a lighter fill with a rounded border). Use a boxed panel only for real
  emphasis, and ask the user first.
- **One accent:** at most one primary (accent-filled) button per screen. Everything else is a
  ghost or outline button.
- **Before a job starts:** show a plain sentence of what will happen, how long it takes ("≈ 25
  min") and what it costs. Durations are typed as a number and a unit, never raw seconds.
- **While it runs:** one row per item with a step track. At the end, one honest line where items
  that were stopped count as "not done", not failed.
- **Errors:** write them in plain words in the error note (bottom right), and keep the raw text in
  the log.
- **Writing:** sentence case, short labels, and one helper line under each label.
