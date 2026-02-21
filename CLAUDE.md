# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Single-file Python application (`orrery.py`) — an interactive solar system simulator with a real-time GUI built on **Kivy** and **Astropy**.

## Running

```bash
pip install kivy astropy
python orrery.py
```

No tests, no build step, no CLI arguments.

## Architecture

Everything lives in `orrery.py`. Two classes:

- **`OrreryWidget(Widget)`** — Main simulation widget. Owns all state: view (`scale`, `pan_x/y`), time (`sim_time`, `time_factor`, `paused`), body positions (`self.positions`), precomputed orbit paths (`self.orbit_paths`, `self.moon_orbit_paths`), info overlay state (`selected_body`, `_overlay_rect`, `_image_cache`). Runs a 30 fps Kivy `Clock` loop via `_update()` → `_compute_positions()` + `_draw()`.
- **`OrreryApp(App)`** — Kivy entry point. Builds a `FloatLayout` with the `OrreryWidget`, a timestamp label (upper-right), and a help overlay label (center).

### Coordinate system

All positions stored as **heliocentric AU** (x, y). `world_to_screen()` converts AU → pixels using `self.scale` (pixels/AU) and `self.pan_x/pan_y` offsets. Moon positions are stored as full heliocentric coordinates (planet position + Keplerian offset).

### Three position backends

| Body type | Source |
|---|---|
| 8 planets | Astropy `get_body_barycentric()` with builtin ephemeris, subtract Sun's barycentric position |
| Asteroids + minor/dwarf planets | `kepler_pos()` using J2000 elements in `ASTEROIDS` / `MINOR_PLANETS` |
| Moons | `kepler_pos()` for planet-relative offset, added to parent's heliocentric position |

### Body data structures

Module-level lists/dicts of body descriptors:
- `PLANETS` — Sun + 8 planets: `name`, `color`, `radius_km`, `min_px`
- `ASTEROIDS` — 5 major asteroids: Keplerian elements (`a`, `e`, `i`, `Omega`, `omega`, `M0`, `epoch_jd`, `period_y`)
- `MINOR_PLANETS` — Pluto + 4 dwarf planets: same Keplerian schema
- `MOONS` — dict keyed by parent planet name; each moon has `a_km`, `period_d` (days), plus Keplerian elements; moon orbit paths stored as planet-relative AU offsets in `self.moon_orbit_paths`
- `MOON_PARENT` — flat `{moon_name: planet_name}` lookup built at module load
- `BODY_INFO` — physical/orbital data for the info overlay (diameter, mass, rotation, orbital period, velocity)
- `ORBITAL_PERIODS` — used to scale orbit path resolution for planets

### Rendering pipeline (per frame)

`_draw()` clears and redraws the entire canvas each frame:
1. Background rectangle
2. Planet/asteroid orbit paths via `_draw_orbits()`
3. Moon orbit paths via `_draw_moon_orbits()` — **only for planets where `_should_show_moons()` is True**
4. All main bodies via `_draw_body()`
5. Moon bodies — **only when `_should_show_moons()` is True**
6. Info overlay via `_draw_info_overlay()`

### Moon visibility gating

`_should_show_moons(planet_name)` returns True when the outermost moon's orbit in pixels (`a_km / AU_KM * scale`) exceeds the planet's drawn pixel radius. This prevents rendering moon orbits at solar-system scale where they'd be invisible, and also gates click detection for moons.

### Info overlay

Clicking a body (click = mouse-up without >5px drag) calls `_handle_click()`, which sets `self.selected_body`. `_draw_info_overlay()` renders a lower-left panel each frame using `CoreLabel` textures. Clicking the panel or pressing Escape deselects. Images loaded from `images/<Name>.jpg` (or `.png`, case-insensitive) relative to the script, cached in `self._image_cache`.

### Controls

| Key/action | Effect |
|---|---|
| Scroll up/down | Zoom in/out |
| Mouse drag | Pan |
| Arrow up/down | Zoom out/in |
| R | Reset view |
| F / S | Speed up / slow down time (10× steps, range 1×–10⁷×) |
| P | Pause/unpause |
| H | Toggle help overlay |
| F11 | Toggle fullscreen |
| Click body | Show info overlay |
| Escape | Close info overlay |
