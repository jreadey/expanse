"""Virtual Orrery - Interactive Solar System Simulator using Kivy and Astropy."""

import math
import os
from datetime import datetime

# Disable Kivy's multitouch emulation (red dot on right-click / multi-touch)
os.environ["KIVY_NO_ENV_CONFIG"] = "1"

from kivy.config import Config
Config.set("input", "mouse", "mouse,multitouch_on_demand")
Config.set("graphics", "resizable", "1")

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.metrics import dp

import astropy.units as u
from astropy.time import Time, TimeDelta
from astropy.coordinates import get_body_barycentric, solar_system_ephemeris


# ---------------------------------------------------------------------------
# Body definitions
# ---------------------------------------------------------------------------

PLANETS = [
    {"name": "Sun",     "color": (1.0, 0.9, 0.2),  "radius_km": 696340,  "min_px": 9},
    {"name": "Mercury", "color": (0.7, 0.7, 0.7),  "radius_km": 2439,   "min_px": 3},
    {"name": "Venus",   "color": (0.9, 0.85, 0.5), "radius_km": 6051,   "min_px": 4},
    {"name": "Earth",   "color": (0.2, 0.5, 1.0),  "radius_km": 6371,   "min_px": 4},
    {"name": "Mars",    "color": (0.9, 0.3, 0.2),  "radius_km": 3389,   "min_px": 3.5},
    {"name": "Jupiter", "color": (0.8, 0.7, 0.5),  "radius_km": 69911,  "min_px": 7},
    {"name": "Saturn",  "color": (0.9, 0.8, 0.5),  "radius_km": 58232,  "min_px": 6},
    {"name": "Uranus",  "color": (0.5, 0.8, 0.9),  "radius_km": 25362,  "min_px": 5},
    {"name": "Neptune", "color": (0.3, 0.4, 0.9),  "radius_km": 24622,  "min_px": 5},
]

# Named asteroids with Keplerian orbital elements (J2000 epoch)
# a (AU), e, i (deg), Omega (deg), omega (deg), M0 (deg), period (years)
ASTEROIDS = [
    {
        "name": "Ceres",  "color": (0.6, 0.6, 0.5), "min_px": 3,
        "a": 2.7691, "e": 0.0760, "i": 10.594, "Omega": 80.394,
        "omega": 73.597, "M0": 77.37, "epoch_jd": 2451545.0, "period_y": 4.60,
    },
    {
        "name": "Vesta",  "color": (0.7, 0.65, 0.55), "min_px": 3,
        "a": 2.3615, "e": 0.0887, "i": 7.134, "Omega": 103.851,
        "omega": 149.855, "M0": 20.86, "epoch_jd": 2451545.0, "period_y": 3.63,
    },
    {
        "name": "Pallas", "color": (0.55, 0.55, 0.6), "min_px": 3,
        "a": 2.7720, "e": 0.2313, "i": 34.832, "Omega": 173.096,
        "omega": 310.202, "M0": 259.88, "epoch_jd": 2451545.0, "period_y": 4.61,
    },
    {
        "name": "Juno",   "color": (0.65, 0.6, 0.5), "min_px": 3,
        "a": 2.6691, "e": 0.2562, "i": 12.991, "Omega": 169.851,
        "omega": 248.066, "M0": 18.28, "epoch_jd": 2451545.0, "period_y": 4.36,
    },
    {
        "name": "Hygiea", "color": (0.5, 0.5, 0.55), "min_px": 3,
        "a": 3.1421, "e": 0.1146, "i": 3.842, "Omega": 283.411,
        "omega": 312.303, "M0": 156.08, "epoch_jd": 2451545.0, "period_y": 5.57,
    },
]

# Minor (dwarf) planets with Keplerian orbital elements
MINOR_PLANETS = [
    {
        "name": "Pluto", "color": (0.75, 0.65, 0.55), "min_px": 3,
        "a": 39.482, "e": 0.2488, "i": 17.16, "Omega": 110.299,
        "omega": 113.834, "M0": 14.53, "epoch_jd": 2451545.0, "period_y": 247.94,
    },
    {
        "name": "Eris", "color": (0.8, 0.8, 0.85), "min_px": 3,
        "a": 67.781, "e": 0.4407, "i": 44.04, "Omega": 35.87,
        "omega": 151.43, "M0": 205.99, "epoch_jd": 2451545.0, "period_y": 558.04,
    },
    {
        "name": "Haumea", "color": (0.7, 0.7, 0.75), "min_px": 3,
        "a": 43.218, "e": 0.1912, "i": 28.19, "Omega": 122.17,
        "omega": 239.18, "M0": 218.21, "epoch_jd": 2451545.0, "period_y": 284.12,
    },
    {
        "name": "Makemake", "color": (0.75, 0.6, 0.55), "min_px": 3,
        "a": 45.436, "e": 0.1613, "i": 28.98, "Omega": 79.38,
        "omega": 296.53, "M0": 153.94, "epoch_jd": 2451545.0, "period_y": 306.21,
    },
    {
        "name": "Sedna", "color": (0.85, 0.5, 0.4), "min_px": 3,
        "a": 506.8, "e": 0.8496, "i": 11.93, "Omega": 144.26,
        "omega": 311.02, "M0": 358.12, "epoch_jd": 2451545.0, "period_y": 11408.0,
    },
]

# Orbital periods in years for path precomputation
ORBITAL_PERIODS = {
    "Mercury": 0.241, "Venus": 0.615, "Earth": 1.0, "Mars": 1.881,
    "Jupiter": 11.86, "Saturn": 29.46, "Uranus": 84.01, "Neptune": 164.8,
}

HELP_TEXT = """[b]Virtual Orrery - Controls[/b]

[b]View:[/b]
  Down Arrow / Scroll Up    Zoom in
  Up Arrow / Scroll Down    Zoom out
  Mouse Drag                Pan view
  R                         Reset view

[b]Time:[/b]
  F    Speed up time (10x)
  S    Slow down time (10x)
  P    Pause / unpause

[b]Window:[/b]
  F11  Toggle fullscreen

[b]Other:[/b]
  H    Toggle this help overlay
"""

AU_KM = 1.496e8  # km per AU
DEFAULT_SCALE = 120.0  # pixels per AU


# ---------------------------------------------------------------------------
# Keplerian propagation helpers
# ---------------------------------------------------------------------------

def solve_kepler(M, e, tol=1e-8):
    """Solve Kepler's equation M = E - e*sin(E) for E using Newton's method."""
    E = M if e < 0.8 else math.pi
    for _ in range(50):
        dE = (E - e * math.sin(E) - M) / (1.0 - e * math.cos(E))
        E -= dE
        if abs(dE) < tol:
            break
    return E


def kepler_pos_heliocentric(a, e, i_deg, Omega_deg, omega_deg, M0_deg,
                            epoch_jd, period_y, jd):
    """Return (x, y) heliocentric ecliptic coordinates in AU via Keplerian propagation."""
    period_days = period_y * 365.25
    n = 2.0 * math.pi / period_days  # mean motion
    dt = jd - epoch_jd
    M = math.radians(M0_deg) + n * dt
    M = M % (2.0 * math.pi)

    E = solve_kepler(M, e)
    nu = 2.0 * math.atan2(math.sqrt(1 + e) * math.sin(E / 2),
                           math.sqrt(1 - e) * math.cos(E / 2))
    r = a * (1 - e * math.cos(E))

    i = math.radians(i_deg)
    Om = math.radians(Omega_deg)
    w = math.radians(omega_deg)

    # Heliocentric ecliptic coordinates
    cos_Om, sin_Om = math.cos(Om), math.sin(Om)
    cos_w_nu, sin_w_nu = math.cos(w + nu), math.sin(w + nu)
    cos_i = math.cos(i)

    x = r * (cos_Om * cos_w_nu - sin_Om * sin_w_nu * cos_i)
    y = r * (sin_Om * cos_w_nu + cos_Om * sin_w_nu * cos_i)
    return x, y


def kepler_orbit_points(body, n_points=120):
    """Return list of (x, y) points tracing one full orbit."""
    period_days = body["period_y"] * 365.25
    points = []
    for k in range(n_points + 1):
        jd = body["epoch_jd"] + (k / n_points) * period_days
        x, y = kepler_pos_heliocentric(
            body["a"], body["e"], body["i"], body["Omega"], body["omega"],
            body["M0"], body["epoch_jd"], body["period_y"], jd)
        points.append((x, y))
    return points


# ---------------------------------------------------------------------------
# Orrery Widget
# ---------------------------------------------------------------------------

class OrreryWidget(Widget):
    def __init__(self, info_label, help_label, **kwargs):
        super().__init__(**kwargs)
        self.info_label = info_label
        self.help_label = help_label

        # View state
        self.scale = DEFAULT_SCALE
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._dragging = False
        self._last_touch = None

        # Time state
        self.sim_time = Time(datetime.utcnow(), scale="utc")
        self.time_factor = 1.0
        self.paused = False
        self._last_computed_jd = 0.0

        # Fullscreen state
        self._fullscreen = False

        # Help overlay visible on startup
        self.show_help = True
        self._update_help_visibility()

        # Body positions: name -> (x_au, y_au)
        self.positions = {}
        # Precomputed orbit paths: name -> [(x_au, y_au), ...]
        self.orbit_paths = {}

        # Sun position is always origin for our heliocentric view
        self.positions["Sun"] = (0.0, 0.0)

        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)

        # Precompute orbits and initial positions
        self._precompute_orbits()
        self._compute_positions(force=True)

        Clock.schedule_interval(self._update, 1.0 / 30.0)

    # -- Keyboard ----------------------------------------------------------

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_key_down)
        self._keyboard = None

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        key_name = keycode[1] if keycode else None
        if key_name == "up":
            self.scale *= 0.8
        elif key_name == "down":
            self.scale *= 1.25
        elif key_name == "f" and "shift" not in modifiers:
            self.time_factor = min(self.time_factor * 10, 1e7)
        elif key_name == "s":
            self.time_factor = max(self.time_factor / 10, 1.0)
        elif key_name == "p":
            self.paused = not self.paused
        elif key_name == "h":
            self.show_help = not self.show_help
            self._update_help_visibility()
        elif key_name == "r":
            self.scale = DEFAULT_SCALE
            self.pan_x = 0.0
            self.pan_y = 0.0
        elif key_name == "f11":
            self._fullscreen = not self._fullscreen
            Window.fullscreen = "auto" if self._fullscreen else False
        return True

    # -- Mouse / touch -----------------------------------------------------

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        if touch.is_mouse_scrolling:
            if touch.button == "scrolldown":
                self.scale *= 0.9
            elif touch.button == "scrollup":
                self.scale *= 1.1
            return True
        self._dragging = True
        self._last_touch = touch.pos
        touch.grab(self)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return False
        if self._dragging and self._last_touch:
            dx = touch.x - self._last_touch[0]
            dy = touch.y - self._last_touch[1]
            self.pan_x += dx
            self.pan_y += dy
            self._last_touch = touch.pos
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self._dragging = False
            self._last_touch = None
        return True

    # -- Helpers -----------------------------------------------------------

    def _update_help_visibility(self):
        if self.help_label:
            self.help_label.opacity = 1.0 if self.show_help else 0.0

    def world_to_screen(self, x_au, y_au):
        cx = self.width / 2 + self.pan_x
        cy = self.height / 2 + self.pan_y
        sx = cx + x_au * self.scale
        sy = cy + y_au * self.scale
        return sx, sy

    # -- Orbit precomputation ----------------------------------------------

    def _precompute_orbits(self):
        with solar_system_ephemeris.set("builtin"):
            for body in PLANETS[1:]:  # skip Sun
                name = body["name"].lower()
                period = ORBITAL_PERIODS.get(body["name"], 1.0)
                n_points = max(60, int(period * 60))
                n_points = min(n_points, 600)
                t0 = self.sim_time
                points = []
                for k in range(n_points + 1):
                    frac = k / n_points
                    t = t0 + TimeDelta(frac * period * 365.25, format="jd")
                    try:
                        pos = get_body_barycentric(name, t)
                        points.append((pos.x.to(u.AU).value, pos.y.to(u.AU).value))
                    except Exception:
                        pass
                self.orbit_paths[body["name"]] = points

        # Asteroid and minor planet orbits from Keplerian elements
        for body in ASTEROIDS + MINOR_PLANETS:
            self.orbit_paths[body["name"]] = kepler_orbit_points(body)

    # -- Position computation ----------------------------------------------

    def _compute_positions(self, force=False):
        jd = self.sim_time.jd
        if not force and abs(jd - self._last_computed_jd) < 0.1:
            return
        self._last_computed_jd = jd

        with solar_system_ephemeris.set("builtin"):
            # Get Sun barycentric position so we can convert to heliocentric
            try:
                sun_pos = get_body_barycentric("sun", self.sim_time)
                sun_x = sun_pos.x.to(u.AU).value
                sun_y = sun_pos.y.to(u.AU).value
            except Exception:
                sun_x, sun_y = 0.0, 0.0

            self.positions["Sun"] = (0.0, 0.0)

            for body in PLANETS[1:]:
                name = body["name"].lower()
                try:
                    pos = get_body_barycentric(name, self.sim_time)
                    x = pos.x.to(u.AU).value - sun_x
                    y = pos.y.to(u.AU).value - sun_y
                    self.positions[body["name"]] = (x, y)
                except Exception:
                    self.positions[body["name"]] = (0.0, 0.0)

        # Asteroids and minor planets via Keplerian propagation
        for body in ASTEROIDS + MINOR_PLANETS:
            x, y = kepler_pos_heliocentric(
                body["a"], body["e"], body["i"], body["Omega"], body["omega"],
                body["M0"], body["epoch_jd"], body["period_y"], jd)
            self.positions[body["name"]] = (x, y)

    # -- Main update loop --------------------------------------------------

    def _update(self, dt):
        if not self.paused:
            self.sim_time += TimeDelta(dt * self.time_factor, format="sec")
            self._compute_positions()

        self._draw()
        self._update_info()

    # -- Info label --------------------------------------------------------

    def _update_info(self):
        iso = self.sim_time.iso[:19]
        state = "PAUSED" if self.paused else f"x{self.time_factor:g}"
        self.info_label.text = f"{iso} UTC  [{state}]"

    # -- Drawing -----------------------------------------------------------

    def _draw(self):
        self.canvas.clear()
        with self.canvas:
            # Background
            Color(0.02, 0.02, 0.06, 1)
            Rectangle(pos=self.pos, size=self.size)

            # Draw orbit paths
            self._draw_orbits()

            # Draw bodies
            all_bodies = PLANETS + ASTEROIDS + MINOR_PLANETS
            for body in all_bodies:
                name = body["name"]
                if name not in self.positions:
                    continue
                x_au, y_au = self.positions[name]
                sx, sy = self.world_to_screen(x_au, y_au)

                # Determine pixel radius
                radius_km = body.get("radius_km", 0)
                min_px = body.get("min_px", 3)
                if radius_km > 0:
                    radius_au = radius_km / AU_KM
                    px = max(radius_au * self.scale, min_px)
                else:
                    px = min_px

                r, g, b = body["color"]
                Color(r, g, b, 1)
                Ellipse(pos=(sx - px, sy - px), size=(px * 2, px * 2))

                # Label
                self._draw_label(name, sx + px + 4, sy - 6, body["color"])

    def _draw_orbits(self):
        for body in PLANETS[1:]:
            name = body["name"]
            path = self.orbit_paths.get(name, [])
            if len(path) < 2:
                continue
            r, g, b = body["color"]
            Color(r, g, b, 0.25)
            pts = []
            for x_au, y_au in path:
                sx, sy = self.world_to_screen(x_au, y_au)
                pts.extend([sx, sy])
            Line(points=pts, width=1)

        for body in ASTEROIDS + MINOR_PLANETS:
            name = body["name"]
            path = self.orbit_paths.get(name, [])
            if len(path) < 2:
                continue
            r, g, b = body["color"]
            Color(r, g, b, 0.2)
            pts = []
            for x_au, y_au in path:
                sx, sy = self.world_to_screen(x_au, y_au)
                pts.extend([sx, sy])
            Line(points=pts, width=1, dash_length=4, dash_offset=4)

    def _draw_label(self, text, x, y, body_color):
        from kivy.core.text import Label as CoreLabel
        cl = CoreLabel(text=text, font_size=dp(11))
        cl.refresh()
        texture = cl.texture
        r, g, b = body_color
        Color(r, g, b, 0.85)
        Rectangle(texture=texture, pos=(x, y), size=texture.size)


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class OrreryApp(App):
    def build(self):
        Window.clearcolor = (0.02, 0.02, 0.06, 1)

        root = FloatLayout()

        # Info label (upper-right)
        info_label = Label(
            text="",
            size_hint=(None, None),
            size=(400, 30),
            pos_hint={"right": 0.99, "top": 0.99},
            halign="right",
            valign="middle",
            color=(0.8, 0.8, 0.8, 1),
            font_size=dp(13),
        )
        info_label.bind(size=info_label.setter("text_size"))

        # Help overlay
        help_label = Label(
            text=HELP_TEXT,
            markup=True,
            size_hint=(None, None),
            size=(380, 340),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            halign="left",
            valign="top",
            color=(0.9, 0.9, 0.9, 1),
            font_size=dp(14),
        )
        help_label.bind(size=help_label.setter("text_size"))

        # Dark background for help
        with help_label.canvas.before:
            from kivy.graphics import Color as GColor, RoundedRectangle
            GColor(0.1, 0.1, 0.15, 0.85)
            self._help_bg = RoundedRectangle(
                pos=(help_label.x - 20, help_label.y - 20),
                size=(help_label.width + 40, help_label.height + 40),
                radius=[10],
            )
        help_label.bind(pos=self._update_help_bg, size=self._update_help_bg)

        orrery = OrreryWidget(info_label=info_label, help_label=help_label)

        root.add_widget(orrery)
        root.add_widget(info_label)
        root.add_widget(help_label)

        return root

    def _update_help_bg(self, instance, value):
        self._help_bg.pos = (instance.x - 20, instance.y - 20)
        self._help_bg.size = (instance.width + 40, instance.height + 40)


if __name__ == "__main__":
    OrreryApp().run()
