"""Virtual Orrery - Interactive Solar System Simulator using Kivy and Astropy."""

import math
import os

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
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp

from simulation import (
    Simulation, xy,
    PLANETS, ASTEROIDS, MINOR_PLANETS, MOONS, MOON_PARENT, BODY_INFO,
    AU_KM, AU_M,
)


# ---------------------------------------------------------------------------
# UI constants
# ---------------------------------------------------------------------------

DEFAULT_SCALE = 120.0  # pixels per AU
COI_ARM_PX = 13   # half-length of each arm of the COI '+' marker (screen pixels)
COI_HIT_PX = 15   # drag-detection radius around COI centre (screen pixels)

HELP_TEXT = """[b]Virtual Orrery - Controls[/b]

[b]View:[/b]
  Down Arrow / Scroll Up    Zoom in
  Up Arrow / Scroll Down    Zoom out
  Mouse Drag                Pan view
  Mouse Drag on +           Move COI marker
  R                         Reset view

[b]Time:[/b]
  F    Speed up time (10x)
  S    Slow down time (10x)
  P    Pause / unpause

[b]Window:[/b]
  F11  Toggle fullscreen

[b]Other:[/b]
  H          Toggle this help overlay
  W          Toggle ship status overlay
  Click body Show body info
  Escape     Close body info
"""


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
        self._drag_origin = None
        self._last_touch = None

        # Centre of Interest marker
        self.coi_au = (0.0, 0.0)        # heliocentric position in AU
        self._drag_coi = False           # True when the current drag is moving the COI
        self._coi_grab_offset = (0, 0)   # screen-space offset from COI centre to grab point

        # COI body lock
        self._locked_body = None         # name of body COI is locked to, or None
        self._locked_target_rx = 0.5    # target x as fraction of widget width (0=left, 1=right)
        self._locked_target_ry = 0.5    # target y as fraction of widget height (0=bottom, 1=top)

        # Fullscreen state
        self._fullscreen = False

        # Help overlay visible on startup
        self.show_help = True
        self._update_help_visibility()

        # Info overlay state
        self.selected_body = None
        self._overlay_rect = None
        self._image_cache = {}
        self.show_ship_overlay = False  # Hidden on startup (press W to toggle)

        # Ship overlay slider state
        self._ship_overlay_rect  = None  # full panel bounding rect
        self._ship_slider_rects = {}   # {"thrust": (x, y, w, h), ...} — track hit rects
        self._dragging_slider = None   # name of slider currently being dragged

        # Ship trail and predicted trajectory
        self._ship_trail      = []   # list of (x_au, y_au) — recent history
        self._predicted_traj  = []   # list of (x_au, y_au) — ballistic future
        self._pred_tick       = 0    # frame counter for throttling prediction

        # Celestial mechanics
        self.sim = Simulation()

        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)

        # Lock COI to Earth at startup, centred on screen.
        # Store target as relative (0.5 = centre) so it stays correct even
        # before the widget receives its final size from the layout pass.
        if "Earth" in self.sim.positions:
            self._locked_body = "Earth"
            self._locked_target_rx = 0.5
            self._locked_target_ry = 0.5
            self.coi_au = xy(self.sim.positions["Earth"])
            ex, ey = self.coi_au
            self.pan_x = -ex * self.scale
            self.pan_y = -ey * self.scale

        Clock.schedule_interval(self._update, 1.0 / 30.0)

    # -- Keyboard ----------------------------------------------------------

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_key_down)
        self._keyboard = None

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        key_name = keycode[1] if keycode else None
        if key_name == "up":
            self._zoom(0.8)
        elif key_name == "down":
            self._zoom(1.25)
        elif key_name == "f" and "shift" not in modifiers:
            self.sim.time_factor = min(self.sim.time_factor * 10, 1e7)
        elif key_name == "s":
            self.sim.time_factor = max(self.sim.time_factor / 10, 1.0)
        elif key_name == "w":
            self.show_ship_overlay = not self.show_ship_overlay
        elif key_name == "p":
            self.sim.paused = not self.sim.paused
        elif key_name == "h":
            self.show_help = not self.show_help
            self._update_help_visibility()
        elif key_name == "r":
            self.scale = DEFAULT_SCALE
            self.sim._crashed = False
            self.sim._crash_body = None
            self.sim.init_ship()
            self.sim.paused = False
            self._lock_to("Earth")
            self._ship_trail = []
            self._predicted_traj = []
        elif key_name == "f11":
            self._fullscreen = not self._fullscreen
            Window.fullscreen = "auto" if self._fullscreen else False
        elif key_name == "escape":
            self.selected_body = None
        return True

    # -- Mouse / touch -----------------------------------------------------

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        if touch.is_mouse_scrolling:
            if touch.button == "scrolldown":
                self._zoom(0.9)
            elif touch.button == "scrollup":
                self._zoom(1.1)
            return True

        # Clicking on the info overlay dismisses it
        if (self.selected_body and self._overlay_rect and
                self._point_in_rect(touch.pos, self._overlay_rect)):
            self.selected_body = None
            return True

        # Ship overlay — consume any touch that starts inside the panel so it
        # never falls through to pan/COI logic.  Only start a slider drag when
        # the touch actually lands on a slider track.
        if (self.show_ship_overlay and self.sim.ship
                and self._ship_overlay_rect
                and self._point_in_rect(touch.pos, self._ship_overlay_rect)):
            for sname, rect in self._ship_slider_rects.items():
                if self._point_in_rect(touch.pos, rect):
                    self._dragging_slider = sname
                    self._apply_slider_touch(sname, touch.x, rect)
                    break
            touch.grab(self)
            return True

        # Only begin a drag when the touch is on or near the COI marker
        coi_sx, coi_sy = self.world_to_screen(*self.coi_au)
        coi_dist = math.hypot(touch.x - coi_sx, touch.y - coi_sy)
        self._drag_coi = coi_dist <= COI_HIT_PX
        if self._drag_coi:
            # Record the vector from the touch point to the COI centre so the
            # marker doesn't jump when dragging starts
            self._coi_grab_offset = (coi_sx - touch.x, coi_sy - touch.y)
            # Release any existing body lock so the drag is uncontested
            self._locked_body = None

        self._dragging = False
        self._drag_origin = touch.pos
        self._last_touch = touch.pos
        touch.grab(self)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return False
        if self._dragging_slider:
            rect = self._ship_slider_rects.get(self._dragging_slider)
            if rect:
                self._apply_slider_touch(self._dragging_slider, touch.x, rect)
            return True
        if self._last_touch:
            if not self._dragging and self._drag_origin:
                if math.hypot(touch.x - self._drag_origin[0],
                              touch.y - self._drag_origin[1]) > 5:
                    self._dragging = True
            if self._dragging and self._drag_coi:
                # Move the COI to where the marker is being dragged
                new_sx = touch.x + self._coi_grab_offset[0]
                new_sy = touch.y + self._coi_grab_offset[1]
                self.coi_au = self.screen_to_world(new_sx, new_sy)
            elif self._dragging and not self._drag_coi:
                # Pan the view
                dx = touch.x - self._last_touch[0]
                dy = touch.y - self._last_touch[1]
                self.pan_x += dx
                self.pan_y += dy
                # Keep the locked target position in sync so locking still works
                if self._locked_body and self.width > 0 and self.height > 0:
                    self._locked_target_rx += dx / self.width
                    self._locked_target_ry += dy / self.height
            self._last_touch = touch.pos
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            if self._dragging_slider:
                self._dragging_slider = None
            elif not self._dragging and self._drag_origin:
                self._handle_click(touch.pos)
            elif self._dragging and self._drag_coi:
                self._check_coi_lock()
            self._dragging = False
            self._last_touch = None
            self._drag_origin = None
        return True

    # -- Click / selection -------------------------------------------------

    def _handle_click(self, pos):
        """Select the nearest visible body within click range, or deselect."""
        tx, ty = pos
        candidates = list(PLANETS + ASTEROIDS + MINOR_PLANETS)
        # Include moons only when they are rendered
        for planet_name, moons in MOONS.items():
            if self._should_show_moons(planet_name):
                candidates.extend(moons)

        best_body = None
        best_dist = float("inf")
        for body in candidates:
            name = body["name"]
            if name not in self.sim.positions:
                continue
            sx, sy = self.world_to_screen(*xy(self.sim.positions[name]))
            radius_km = body.get("radius_km", 0)
            min_px = body.get("min_px", 2)
            px = max(radius_km / AU_KM * self.scale, min_px) if radius_km > 0 else min_px
            dist = math.hypot(tx - sx, ty - sy)
            if dist <= max(px, 10) and dist < best_dist:
                best_dist = dist
                best_body = body

        self.selected_body = best_body["name"] if best_body else None

    def _should_show_moons(self, planet_name):
        """True when the outermost moon's orbit is larger than the planet's drawn disc."""
        moons = MOONS.get(planet_name, [])
        if not moons:
            return False
        all_bodies = PLANETS + ASTEROIDS + MINOR_PLANETS
        planet_body = next((b for b in all_bodies if b["name"] == planet_name), None)
        if not planet_body:
            return False
        radius_km = planet_body.get("radius_km", 0)
        min_px = planet_body.get("min_px", 3)
        planet_px = max(radius_km / AU_KM * self.scale, min_px) if radius_km > 0 else min_px
        outer_au = max(m["a_km"] for m in moons) / AU_KM
        return outer_au * self.scale > planet_px

    def _point_in_rect(self, pos, rect):
        rx, ry, rw, rh = rect
        px, py = pos
        return rx <= px <= rx + rw and ry <= py <= ry + rh

    def _lock_to(self, name):
        """Lock the COI to a named body, pinning it to the current screen centre."""
        if name not in self.sim.positions:
            return
        self._locked_body = name
        self.coi_au = xy(self.sim.positions[name])
        self._locked_target_rx = 0.5
        self._locked_target_ry = 0.5

    def _check_coi_lock(self):
        """After a COI drop, lock onto the nearest body within 5× its drawn radius."""
        self._locked_body = None
        coi_sx, coi_sy = self.world_to_screen(*self.coi_au)

        candidates = list(PLANETS + ASTEROIDS + MINOR_PLANETS)
        for planet_name in MOONS:
            if self._should_show_moons(planet_name):
                candidates.extend(MOONS[planet_name])

        best_name = None
        best_dist = float("inf")
        for body in candidates:
            name = body["name"]
            if name not in self.sim.positions:
                continue
            sx, sy = self.world_to_screen(*xy(self.sim.positions[name]))
            radius_km = body.get("radius_km", 0)
            min_px = body.get("min_px", 2)
            px = max(radius_km / AU_KM * self.scale, min_px) if radius_km > 0 else min_px
            dist = math.hypot(coi_sx - sx, coi_sy - sy)
            if dist <= px * 5 and dist < best_dist:
                best_dist = dist
                best_name = name

        if best_name:
            self._locked_body = best_name
            # Snap COI to body centre; record its current screen position as
            # a fraction of widget size so it remains valid after any resize.
            self.coi_au = xy(self.sim.positions[best_name])
            sx, sy = self.world_to_screen(*self.coi_au)
            self._locked_target_rx = sx / self.width  if self.width  > 0 else 0.5
            self._locked_target_ry = sy / self.height if self.height > 0 else 0.5

    def _update_coi_lock(self):
        """Move COI with locked body and pan so it stays at the recorded screen position."""
        if self._locked_body not in self.sim.positions:
            self._locked_body = None
            return
        self.coi_au = xy(self.sim.positions[self._locked_body])
        coi_x, coi_y = self.coi_au
        self.pan_x = self._locked_target_rx * self.width  - self.width  / 2 - coi_x * self.scale
        self.pan_y = self._locked_target_ry * self.height - self.height / 2 - coi_y * self.scale

    # -- Helpers -----------------------------------------------------------

    def _zoom(self, factor):
        # Adjust pan so the COI marker stays fixed on screen while everything
        # else zooms around it.
        coi_x, coi_y = self.coi_au
        self.pan_x += coi_x * self.scale * (1 - factor)
        self.pan_y += coi_y * self.scale * (1 - factor)
        self.scale *= factor

    def _update_help_visibility(self):
        if self.help_label:
            self.help_label.opacity = 1.0 if self.show_help else 0.0

    def world_to_screen(self, x_au, y_au):
        cx = self.width / 2 + self.pan_x
        cy = self.height / 2 + self.pan_y
        return cx + x_au * self.scale, cy + y_au * self.scale

    def screen_to_world(self, sx, sy):
        cx = self.width / 2 + self.pan_x
        cy = self.height / 2 + self.pan_y
        return (sx - cx) / self.scale, (sy - cy) / self.scale

    # -- Image helpers -----------------------------------------------------

    def _find_image_path(self, name):
        images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
        for ext in ("jpg", "jpeg", "png", "gif"):
            for candidate in (name, name.lower(), name.upper()):
                path = os.path.join(images_dir, f"{candidate}.{ext}")
                if os.path.isfile(path):
                    return path
        return None

    def _get_image_texture(self, name):
        if name not in self._image_cache:
            path = self._find_image_path(name)
            if path:
                try:
                    from kivy.core.image import Image as CoreImage
                    self._image_cache[name] = CoreImage(path)
                except Exception:
                    self._image_cache[name] = None
            else:
                self._image_cache[name] = None
        obj = self._image_cache[name]
        return obj.texture if obj is not None else None

    # -- Main update loop --------------------------------------------------

    def _update(self, dt):
        self.sim.tick(dt)
        if self._locked_body:
            self._update_coi_lock()

        # Append ship position to historical trail (skip when crashed/paused)
        if self.sim.ship and not self.sim._crashed:
            self._ship_trail.append(xy(self.sim.ship.pos))
            if len(self._ship_trail) > 3000:
                del self._ship_trail[:len(self._ship_trail) - 3000]

        # Recompute predicted trajectory every 5 frames (~6 Hz)
        self._pred_tick += 1
        if self._pred_tick >= 5:
            self._pred_tick = 0
            if self.sim.ship and not self.sim._crashed:
                self._predicted_traj = self.sim.predict_trajectory()
            else:
                self._predicted_traj = []

        self._draw()
        self._update_info()

    def _update_info(self):
        iso = self.sim.sim_time.iso[:19]
        state = "PAUSED" if self.sim.paused else f"x{self.sim.time_factor:g}"
        self.info_label.text = f"{iso} UTC  [{state}]"

    # -- Drawing -----------------------------------------------------------

    def _draw(self):
        self.canvas.clear()
        with self.canvas:
            Color(0.02, 0.02, 0.06, 1)
            Rectangle(pos=self.pos, size=self.size)

            self._draw_orbits()

            # Moon orbit paths — only for planets zoomed in enough
            for planet_name in MOONS:
                if self._should_show_moons(planet_name):
                    self._draw_moon_orbits(planet_name)

            # Main bodies
            for body in PLANETS + ASTEROIDS + MINOR_PLANETS:
                self._draw_body(body)

            # Moon bodies — only when zoomed in enough
            for planet_name, moons in MOONS.items():
                if self._should_show_moons(planet_name):
                    for moon in moons:
                        self._draw_body(moon)

            self._draw_ship_trail()
            self._draw_ship()
            self._draw_coi_marker()
            self._draw_info_overlay()
            self._draw_ship_overlay()
            self._draw_crash_overlay()

    def _draw_crash_overlay(self):
        """Full-screen CRASH! banner shown when the ship hits a body."""
        if not self.sim._crashed:
            return
        from kivy.core.text import Label as CoreLabel
        # Dim the scene
        Color(0, 0, 0, 0.65)
        Rectangle(pos=self.pos, size=self.size)
        # Large red "CRASH!" centred on screen
        lbl = CoreLabel(text="CRASH!", font_size=dp(110), bold=True)
        lbl.refresh()
        tex = lbl.texture
        cx = self.x + (self.width  - tex.width)  / 2
        cy = self.y + (self.height - tex.height) / 2 + dp(30)
        Color(1.0, 0.15, 0.15, 1)
        Rectangle(texture=tex, pos=(cx, cy), size=tex.size)
        # Which body was hit
        body_lbl = CoreLabel(
            text=f"Crashed into {self.sim._crash_body}",
            font_size=dp(28),
        )
        body_lbl.refresh()
        btex = body_lbl.texture
        bx = self.x + (self.width  - btex.width)  / 2
        by = cy - btex.height - dp(16)
        Color(1.0, 0.6, 0.6, 1)
        Rectangle(texture=btex, pos=(bx, by), size=btex.size)
        # Hint
        hint_lbl = CoreLabel(text="Press R to reset", font_size=dp(18))
        hint_lbl.refresh()
        htex = hint_lbl.texture
        hx = self.x + (self.width  - htex.width)  / 2
        hy = self.y + dp(30)
        Color(0.75, 0.75, 0.75, 1)
        Rectangle(texture=htex, pos=(hx, hy), size=htex.size)

    def _draw_orbits(self):
        for body in PLANETS[1:]:
            path = self.sim.orbit_paths.get(body["name"], [])
            if len(path) < 2:
                continue
            r, g, b = body["color"]
            Color(r, g, b, 0.25)
            pts = []
            for pt in path:
                pts.extend(self.world_to_screen(*xy(pt)))
            Line(points=pts, width=1.1)

        for body in ASTEROIDS + MINOR_PLANETS:
            path = self.sim.orbit_paths.get(body["name"], [])
            if len(path) < 2:
                continue
            r, g, b = body["color"]
            Color(r, g, b, 0.2)
            pts = []
            for pt in path:
                pts.extend(self.world_to_screen(*xy(pt)))
            Line(points=pts, width=1.1, dash_length=4, dash_offset=4)

    def _draw_moon_orbits(self, planet_name):
        """Draw orbit rings for all moons of planet_name, centered on the planet."""
        p_sx, p_sy = self.world_to_screen(*xy(self.sim.positions[planet_name]))
        for moon in MOONS[planet_name]:
            path = self.sim.moon_orbit_paths.get(moon["name"], [])
            if len(path) < 2:
                continue
            r, g, b = moon["color"]
            Color(r, g, b, 0.35)
            pts = []
            for offset in path:
                dx_au, dy_au = xy(offset)
                pts.append(p_sx + dx_au * self.scale)
                pts.append(p_sy + dy_au * self.scale)
            Line(points=pts, width=1)

    def _draw_body(self, body):
        name = body["name"]
        if name not in self.sim.positions:
            return
        sx, sy = self.world_to_screen(*xy(self.sim.positions[name]))

        radius_km = body.get("radius_km", 0)
        min_px = body.get("min_px", 2)
        px = max(radius_km / AU_KM * self.scale, min_px) if radius_km > 0 else min_px

        if name == self.selected_body:
            Color(1, 1, 1, 0.5)
            ring = px + 4
            Ellipse(pos=(sx - ring, sy - ring), size=(ring * 2, ring * 2))

        r, g, b = body["color"]
        Color(r, g, b, 1)
        Ellipse(pos=(sx - px, sy - px), size=(px * 2, px * 2))
        self._draw_label(name, sx + px + 4, sy - 6, body["color"])

    def _draw_ship_trail(self):
        """Draw the historical trail (solid) and predicted trajectory (dashed)."""
        ship = self.sim.ship
        if ship is None:
            return

        # Historical trail — ship color at 40% alpha
        if len(self._ship_trail) >= 2:
            pts = []
            for x_au, y_au in self._ship_trail:
                pts.extend(self.world_to_screen(x_au, y_au))
            r, g, b = ship.defn["color"]
            Color(r, g, b, 0.4)
            Line(points=pts, width=1.0)

        # Predicted ballistic trajectory — amber dashed
        if len(self._predicted_traj) >= 2:
            pts = []
            for x_au, y_au in self._predicted_traj:
                pts.extend(self.world_to_screen(x_au, y_au))
            Color(0.95, 0.80, 0.2, 0.55)
            Line(points=pts, width=1.0, dash_length=8, dash_offset=8)

    def _draw_ship(self):
        """Draw the ship as a narrow isoceles triangle (30° apex angle)."""
        ship = self.sim.ship
        defn = ship.defn
        sx, sy = self.world_to_screen(*xy(ship.pos))

        L = defn["min_px"]                        # nose-to-base length in pixels
        hw = L * math.tan(math.radians(15))       # half-width at base (30° apex → 15° half-angle)

        # Local frame: centroid at origin, nose pointing +y (north)
        #   centroid divides median 2:1, so nose is 2L/3 above and base is L/3 below
        local = [
            (0.0,  2 * L / 3),   # nose
            (-hw, -L / 3),        # base left
            ( hw, -L / 3),        # base right
        ]

        # Rotate clockwise by orientation_deg from north in a y-up coordinate system
        angle = math.radians(ship.orientation)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        pts = []
        for lx, ly in local:
            pts.append(sx + lx * cos_a + ly * sin_a)
            pts.append(sy - lx * sin_a + ly * cos_a)
        pts += pts[:2]  # close the triangle

        r, g, b = defn["color"]
        Color(r, g, b, 1.0)
        Line(points=pts, width=1.5)
        self._draw_label(defn["name"], sx + hw + 4, sy - 6, defn["color"])

    def _apply_slider_touch(self, name, tx, rect):
        """Map a touch x position onto the slider's value range and update the ship."""
        rx, ry, rw, rh = rect
        frac = max(0.0, min(1.0, (tx - rx) / rw))
        ship = self.sim.ship
        if name == "thrust":
            try:
                ship.set_thrust(frac * 100.0)
            except ValueError:
                pass
        elif name == "orientation":
            ship.set_orientation(frac * 359.9)
        elif name == "elevation":
            ship.set_orientation(ship.orientation, elevation=(frac - 0.5) * 180.0)

    def _draw_ship_overlay(self):
        """Bottom-right panel showing live ship state."""
        if not self.show_ship_overlay:
            return
        from kivy.core.text import Label as CoreLabel

        ship = self.sim.ship
        defn = ship.defn

        ref_name = self._locked_body if self._locked_body else "Sun"
        ref_vel  = self.sim.body_vel_ms.get(ref_name, (0.0, 0.0))
        rel_vx   = ship.vel[0] - ref_vel[0]
        rel_vy   = ship.vel[1] - ref_vel[1]
        speed_ms      = math.hypot(rel_vx, rel_vy)
        total_mass_kg = (defn["dry_mass_t"] + ship.fuel) * 1000.0
        thrust_N      = ship.thrust / 100.0 * defn["max_thrust_N"]
        accel_g       = (thrust_N / total_mass_kg) / 9.80665 if total_mass_kg > 0 else 0.0

        lines = [
            f"Speed:        {speed_ms:,.1f} m/s  (re. {ref_name})",
            f"Orientation:  {ship.orientation:.1f}\u00b0 / {ship.elevation:.1f}\u00b0",
            f"Acceleration: {accel_g:.2f} g",
        ]

        title_cl = CoreLabel(text=defn["name"], font_size=dp(23), bold=True)
        title_cl.refresh()
        title_t = title_cl.texture

        line_ts = []
        for line in lines:
            cl = CoreLabel(text=line, font_size=dp(18))
            cl.refresh()
            line_ts.append(cl.texture)

        PAD        = 14
        LINE_GAP   = 3
        GAP        = 6
        OVERLAY_W  = 1100
        LEFT_W     = 480   # info text column (much wider to prevent overlap)
        COL_SEP    = 24    # gap (incl. separator line) between each column pair
        LABEL_W    = 100   # slider label column (increased to prevent overlap)
        VAL_W      = 70    # slider value column (increased for degree symbols)
        FUEL_COL_W = 64    # fuel indicator column
        TRACK_W    = OVERLAY_W - 2*PAD - LEFT_W - COL_SEP - LABEL_W - VAL_W - COL_SEP - FUEL_COL_W
        TRACK_T    = 20    # track thickness (4x thicker: was 5, now 20)
        THUMB_R    = 12    # thumb radius (bigger to match thicker track)
        SLIDER_H   = 40    # slider row height (increased to accommodate thicker sliders)

        # Battery icon dimensions
        BATT_W      = 30
        NUB_W       = 16
        NUB_H       = 6
        BATT_BORDER = 2

        left_h  = title_t.height + GAP + sum(t.height + LINE_GAP for t in line_ts)
        right_h = 3 * SLIDER_H
        total_h = max(left_h, right_h) + 2 * PAD

        ox = max(20, self.width - OVERLAY_W - 40)
        oy = 20

        # Column x origins
        slider_x = ox + PAD + LEFT_W + COL_SEP
        track_x  = slider_x + LABEL_W
        fuel_x   = slider_x + LABEL_W + TRACK_W + VAL_W + COL_SEP

        self._ship_overlay_rect = (ox, oy, OVERLAY_W, total_h)

        Color(0.07, 0.07, 0.12, 0.93)
        RoundedRectangle(pos=(ox, oy), size=(OVERLAY_W, total_h), radius=[10])
        Color(0.3, 0.3, 0.45, 0.6)
        Line(rounded_rectangle=(ox, oy, OVERLAY_W, total_h, 10), width=1)

        # Vertical separators
        Color(0.3, 0.3, 0.45, 0.7)
        sep1_x = ox + PAD + LEFT_W + COL_SEP // 2
        Line(points=[sep1_x, oy + PAD, sep1_x, oy + total_h - PAD], width=1)
        sep2_x = fuel_x - COL_SEP // 2
        Line(points=[sep2_x, oy + PAD, sep2_x, oy + total_h - PAD], width=1)

        # Left column: title + info lines
        draw_y = oy + total_h - PAD
        draw_y -= title_t.height
        r, g, b = defn["color"]
        Color(r, g, b, 1)
        Rectangle(texture=title_t, pos=(ox + PAD, draw_y), size=title_t.size)
        draw_y -= GAP

        for t in line_ts:
            draw_y -= t.height
            Color(0.82, 0.82, 0.88, 1)
            Rectangle(texture=t, pos=(ox + PAD, draw_y), size=t.size)
            draw_y -= LINE_GAP

        # Middle column: sliders, top-aligned
        slider_defs = [
            ("thrust",      "Thrust",
             ship.thrust / 100.0,
             f"{ship.thrust:.0f}%"),
            ("orientation", "Heading",
             ship.orientation / 359.9,
             f"{ship.orientation:.1f}\u00b0"),
            ("elevation",   "Elevation",
             (ship.elevation + 90.0) / 180.0,
             f"{ship.elevation:.1f}\u00b0"),
        ]

        draw_y = oy + total_h - PAD
        self._ship_slider_rects = {}
        for sname, slabel, frac, sval in slider_defs:
            row_cy = draw_y - SLIDER_H // 2
            draw_y -= SLIDER_H

            self._ship_slider_rects[sname] = (
                track_x, row_cy - THUMB_R - 2, TRACK_W, (THUMB_R + 2) * 2
            )

            lbl_cl = CoreLabel(text=slabel, font_size=dp(16))
            lbl_cl.refresh()
            lbl_t = lbl_cl.texture
            Color(0.7, 0.7, 0.8, 1)
            Rectangle(texture=lbl_t,
                      pos=(slider_x, row_cy - lbl_t.height // 2),
                      size=lbl_t.size)

            track_y = row_cy - TRACK_T // 2
            Color(0.2, 0.2, 0.3, 1)
            RoundedRectangle(pos=(track_x, track_y),
                             size=(TRACK_W, TRACK_T), radius=[3])

            if frac > 0:
                Color(0.35, 0.55, 0.95, 0.85)
                RoundedRectangle(pos=(track_x, track_y),
                                 size=(TRACK_W * frac, TRACK_T), radius=[3])

            thumb_x = track_x + TRACK_W * frac
            Color(0.85, 0.92, 1.0, 1)
            Ellipse(pos=(thumb_x - THUMB_R, row_cy - THUMB_R),
                    size=(THUMB_R * 2, THUMB_R * 2))

            val_cl = CoreLabel(text=sval, font_size=dp(16))
            val_cl.refresh()
            val_t = val_cl.texture
            Color(0.82, 0.82, 0.88, 1)
            Rectangle(texture=val_t,
                      pos=(track_x + TRACK_W + 8, row_cy - val_t.height // 2),
                      size=val_t.size)

        # Right column: fuel battery icon, vertically centred
        fuel_pct = max(0.0, min(100.0,
                       ship.fuel / defn["max_fuel_t"] * 100.0))

        pct_cl = CoreLabel(text=f"{fuel_pct:.0f}%", font_size=dp(14))
        pct_cl.refresh()
        pct_t  = pct_cl.texture

        # Lay out the block: nub (top) → body → gap → pct text (bottom)
        avail_h   = total_h - 2 * PAD
        BATT_H    = max(20, avail_h - NUB_H - 4 - pct_t.height)
        block_h   = NUB_H + BATT_H + 4 + pct_t.height
        block_bot = oy + PAD + (avail_h - block_h) // 2   # bottom of pct text
        batt_y    = block_bot + 4 + pct_t.height           # bottom of battery body
        nub_y     = batt_y + BATT_H                        # bottom of nub
        batt_x    = fuel_x + (FUEL_COL_W - BATT_W) // 2
        nub_x     = fuel_x + (FUEL_COL_W - NUB_W) // 2

        # Terminal nub
        Color(0.45, 0.45, 0.60, 0.9)
        RoundedRectangle(pos=(nub_x, nub_y), size=(NUB_W, NUB_H), radius=[2])

        # Battery outline
        Color(0.45, 0.45, 0.60, 0.9)
        Line(rounded_rectangle=(batt_x, batt_y, BATT_W, BATT_H, 3),
             width=BATT_BORDER)

        # Fill colour: green → amber → red
        if fuel_pct > 50:
            fc = (0.15, 0.80, 0.25, 0.9)
        elif fuel_pct > 20:
            fc = (0.95, 0.75, 0.05, 0.9)
        else:
            fc = (0.90, 0.18, 0.18, 0.9)

        inner_margin = BATT_BORDER + 2
        inner_x = batt_x + inner_margin
        inner_w = BATT_W - 2 * inner_margin
        fill_h  = int((BATT_H - 2 * inner_margin) * fuel_pct / 100.0)
        if fill_h > 0:
            Color(*fc)
            RoundedRectangle(
                pos=(inner_x, batt_y + inner_margin),
                size=(inner_w, fill_h),
                radius=[2],
            )

        # Percentage text, centred below the battery
        Color(0.82, 0.82, 0.88, 1)
        Rectangle(texture=pct_t,
                  pos=(fuel_x + (FUEL_COL_W - pct_t.width) // 2, block_bot),
                  size=pct_t.size)

    def _draw_coi_marker(self):
        """Draw the Centre of Interest '+' marker in screen space."""
        sx, sy = self.world_to_screen(*self.coi_au)
        arm = COI_ARM_PX
        Color(1, 1, 1, 0.9)
        Line(points=[sx - arm, sy, sx + arm, sy], width=1.5)
        Line(points=[sx, sy - arm, sx, sy + arm], width=1.5)

    def _draw_label(self, text, x, y, color):
        from kivy.core.text import Label as CoreLabel
        cl = CoreLabel(text=text, font_size=dp(17))
        cl.refresh()
        t = cl.texture
        r, g, b = color
        Color(r, g, b, 0.85)
        Rectangle(texture=t, pos=(x, y), size=t.size)

    # -- Info overlay ------------------------------------------------------

    def _draw_info_overlay(self):
        if not self.selected_body:
            self._overlay_rect = None
            return

        from kivy.core.text import Label as CoreLabel

        name = self.selected_body
        info = BODY_INFO.get(name, {})
        pos = self.sim.positions.get(name)
        pos_au = xy(pos) if pos is not None else (0.0, 0.0)
        dist_au = math.hypot(*pos_au)
        parent = MOON_PARENT.get(name)

        info_lines = []

        if parent:
            info_lines.append(f"Orbits:           {parent}")

        diam = info.get("diameter_km")
        if diam is not None:
            info_lines.append(f"Diameter:         {diam:,} km")

        mass = info.get("mass_kg")
        if mass is not None:
            exp = int(math.floor(math.log10(mass)))
            info_lines.append(f"Mass:             {mass / 10**exp:.2f} \u00d7 10^{exp} kg")

        period_y = info.get("orbital_period_y")

        rot = info.get("rotation_days")
        if rot is not None:
            # For tidally locked moons rotation period == orbital period
            tidally_locked = (
                parent is not None and period_y is not None and
                abs(rot - period_y * 365.25) / max(period_y * 365.25, 1e-10) < 0.01
            )
            suffix = " (tidally locked)" if tidally_locked else ""
            info_lines.append(f"Rotation period:  {rot:.4g} days{suffix}")
        if period_y is not None:
            if period_y < 1.0:
                info_lines.append(f"Orbital period:   {period_y * 365.25:.4g} days")
            else:
                info_lines.append(f"Orbital period:   {period_y:.4g} yr")
        else:
            info_lines.append("Orbital period:   N/A")

        if name == "Sun":
            info_lines.append("Dist. from Sun:   0 AU")
        else:
            info_lines.append(f"Dist. from Sun:   {dist_au:.3f} AU")

        vel = info.get("orbital_velocity_kms")
        if vel is not None:
            label = "Orb. vel. (parent)" if parent else "Orbital velocity"
            info_lines.append(f"{label}: {vel:.3g} km/s")
        else:
            info_lines.append("Orbital velocity: N/A")

        # Pre-render to measure sizes
        title_cl = CoreLabel(text=name, font_size=dp(23), bold=True)
        title_cl.refresh()
        title_t = title_cl.texture

        hint_cl = CoreLabel(text="(click to close)", font_size=dp(15), italic=True)
        hint_cl.refresh()
        hint_t = hint_cl.texture

        line_ts = []
        for line in info_lines:
            cl = CoreLabel(text=line, font_size=dp(18))
            cl.refresh()
            line_ts.append(cl.texture)

        body_tex = self._get_image_texture(name)

        PAD, GAP, LINE_GAP = 14, 8, 3
        IMG_SIZE, OVERLAY_W = 160, 300

        total_h = PAD + title_t.height + 4 + hint_t.height + GAP
        if body_tex:
            total_h += IMG_SIZE + GAP
        for t in line_ts:
            total_h += t.height + LINE_GAP
        total_h += PAD

        ox, oy = 20, 20

        Color(0.07, 0.07, 0.12, 0.93)
        RoundedRectangle(pos=(ox, oy), size=(OVERLAY_W, total_h), radius=[10])
        Color(0.3, 0.3, 0.45, 0.6)
        Line(rounded_rectangle=(ox, oy, OVERLAY_W, total_h, 10), width=1)

        self._overlay_rect = (ox, oy, OVERLAY_W, total_h)

        draw_y = oy + total_h - PAD

        draw_y -= title_t.height
        Color(1.0, 0.92, 0.55, 1)
        Rectangle(texture=title_t, pos=(ox + PAD, draw_y), size=title_t.size)

        draw_y -= hint_t.height + 2
        Color(0.55, 0.55, 0.65, 1)
        Rectangle(texture=hint_t, pos=(ox + PAD, draw_y), size=hint_t.size)

        draw_y -= GAP

        if body_tex:
            draw_y -= IMG_SIZE
            Color(1, 1, 1, 1)
            Rectangle(texture=body_tex,
                      pos=(ox + (OVERLAY_W - IMG_SIZE) // 2, draw_y),
                      size=(IMG_SIZE, IMG_SIZE))
            draw_y -= GAP

        for t in line_ts:
            draw_y -= t.height
            Color(0.82, 0.82, 0.88, 1)
            Rectangle(texture=t, pos=(ox + PAD, draw_y), size=t.size)
            draw_y -= LINE_GAP


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class OrreryApp(App):
    def build(self):
        Window.clearcolor = (0.02, 0.02, 0.06, 1)

        root = FloatLayout()

        info_label = Label(
            text="",
            size_hint=(None, None),
            size=(500, 30),
            pos_hint={"right": 0.985, "top": 0.99},
            halign="right",
            valign="middle",
            color=(0.8, 0.8, 0.8, 1),
            font_size=dp(20),
        )
        info_label.bind(size=info_label.setter("text_size"))

        help_label = Label(
            text=HELP_TEXT,
            markup=True,
            size_hint=(None, None),
            size=(380, 360),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            halign="left",
            valign="top",
            color=(0.9, 0.9, 0.9, 1),
            font_size=dp(21),
        )
        help_label.bind(size=help_label.setter("text_size"))

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
