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
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
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

# Moons keyed by parent planet name.
# Keplerian elements are approximate ecliptic-plane values (J2000).
# a_km: semi-major axis in km; period_d: orbital period in days.
MOONS = {
    "Earth": [
        {"name": "Moon",     "color": (0.80, 0.80, 0.80), "min_px": 2, "radius_km": 1_737,
         "a_km": 384_400, "e": 0.0549, "i": 5.145,
         "Omega": 125.08, "omega": 318.15, "M0": 134.96,
         "epoch_jd": 2451545.0, "period_d": 27.3217},
    ],
    "Mars": [
        {"name": "Phobos",   "color": (0.65, 0.55, 0.50), "min_px": 2, "radius_km": 11,
         "a_km":  9_376, "e": 0.0151, "i": 26.04,
         "Omega": 207.3,  "omega": 359.2, "M0":  92.5,
         "epoch_jd": 2451545.0, "period_d": 0.31891},
        {"name": "Deimos",   "color": (0.60, 0.52, 0.47), "min_px": 2, "radius_km": 6,
         "a_km": 23_463, "e": 0.00033, "i": 27.58,
         "Omega":  24.5,  "omega":  53.9, "M0":  95.8,
         "epoch_jd": 2451545.0, "period_d": 1.26244},
    ],
    "Jupiter": [
        {"name": "Io",       "color": (0.92, 0.85, 0.52), "min_px": 2, "radius_km": 1_821,
         "a_km":   421_800, "e": 0.0041, "i": 3.1,
         "Omega":  43.98, "omega":  84.13, "M0": 342.02,
         "epoch_jd": 2451545.0, "period_d":  1.76914},
        {"name": "Europa",   "color": (0.80, 0.75, 0.70), "min_px": 2, "radius_km": 1_561,
         "a_km":   671_100, "e": 0.009,  "i": 3.1,
         "Omega": 219.11, "omega":  88.97, "M0": 171.02,
         "epoch_jd": 2451545.0, "period_d":  3.55182},
        {"name": "Ganymede", "color": (0.70, 0.65, 0.55), "min_px": 2, "radius_km": 2_634,
         "a_km": 1_070_400, "e": 0.0013, "i": 3.1,
         "Omega":  63.55, "omega": 192.42, "M0": 317.54,
         "epoch_jd": 2451545.0, "period_d":  7.15455},
        {"name": "Callisto", "color": (0.55, 0.50, 0.45), "min_px": 2, "radius_km": 2_410,
         "a_km": 1_882_700, "e": 0.0074, "i": 3.1,
         "Omega": 298.85, "omega":  52.64, "M0": 181.41,
         "epoch_jd": 2451545.0, "period_d": 16.68900},
    ],
    "Saturn": [
        {"name": "Mimas",     "color": (0.72, 0.70, 0.67), "min_px": 2, "radius_km": 198,
         "a_km":   185_520, "e": 0.0202, "i": 28.1,
         "Omega": 174.8, "omega": 330.0, "M0":  30.0,
         "epoch_jd": 2451545.0, "period_d":  0.94242},
        {"name": "Enceladus", "color": (0.92, 0.93, 0.95), "min_px": 2, "radius_km": 252,
         "a_km":   238_020, "e": 0.0045, "i": 28.1,
         "Omega": 169.6, "omega": 112.0, "M0": 100.0,
         "epoch_jd": 2451545.0, "period_d":  1.37022},
        {"name": "Tethys",    "color": (0.76, 0.74, 0.71), "min_px": 2, "radius_km": 531,
         "a_km":   294_660, "e": 0.0001, "i": 27.3,
         "Omega":   9.7, "omega":  45.0, "M0": 170.0,
         "epoch_jd": 2451545.0, "period_d":  1.88780},
        {"name": "Dione",     "color": (0.73, 0.71, 0.69), "min_px": 2, "radius_km": 562,
         "a_km":   377_400, "e": 0.0022, "i": 28.0,
         "Omega": 169.7, "omega": 284.0, "M0": 240.0,
         "epoch_jd": 2451545.0, "period_d":  2.73692},
        {"name": "Rhea",      "color": (0.76, 0.73, 0.69), "min_px": 2, "radius_km": 763,
         "a_km":   527_040, "e": 0.0013, "i": 28.2,
         "Omega": 311.5, "omega": 120.0, "M0": 310.0,
         "epoch_jd": 2451545.0, "period_d":  4.51750},
        {"name": "Titan",     "color": (0.86, 0.72, 0.42), "min_px": 2, "radius_km": 2_576,
         "a_km": 1_221_830, "e": 0.0288, "i": 28.3,
         "Omega":  28.1, "omega": 185.0, "M0":  50.0,
         "epoch_jd": 2451545.0, "period_d": 15.94540},
        {"name": "Iapetus",   "color": (0.66, 0.61, 0.56), "min_px": 2, "radius_km": 735,
         "a_km": 3_560_820, "e": 0.0283, "i": 18.3,
         "Omega":  81.1, "omega": 271.0, "M0": 130.0,
         "epoch_jd": 2451545.0, "period_d": 79.33180},
    ],
    "Uranus": [
        {"name": "Miranda", "color": (0.62, 0.72, 0.76), "min_px": 2, "radius_km": 236,
         "a_km":  129_390, "e": 0.0013, "i": 97.77,
         "Omega": 326.4, "omega":  68.0, "M0":  10.0,
         "epoch_jd": 2451545.0, "period_d":  1.41348},
        {"name": "Ariel",   "color": (0.66, 0.74, 0.79), "min_px": 2, "radius_km": 579,
         "a_km":  191_020, "e": 0.0012, "i": 97.72,
         "Omega": 167.6, "omega": 115.0, "M0":  65.0,
         "epoch_jd": 2451545.0, "period_d":  2.52038},
        {"name": "Umbriel", "color": (0.46, 0.46, 0.51), "min_px": 2, "radius_km": 585,
         "a_km":  266_300, "e": 0.0039, "i": 97.87,
         "Omega": 108.4, "omega":  84.0, "M0": 140.0,
         "epoch_jd": 2451545.0, "period_d":  4.14418},
        {"name": "Titania", "color": (0.62, 0.66, 0.71), "min_px": 2, "radius_km": 789,
         "a_km":  435_910, "e": 0.0011, "i": 98.09,
         "Omega": 284.4, "omega": 284.0, "M0": 210.0,
         "epoch_jd": 2451545.0, "period_d":  8.70588},
        {"name": "Oberon",  "color": (0.56, 0.53, 0.51), "min_px": 2, "radius_km": 762,
         "a_km":  583_520, "e": 0.0014, "i": 97.83,
         "Omega": 104.4, "omega": 104.0, "M0": 280.0,
         "epoch_jd": 2451545.0, "period_d": 13.46324},
    ],
    "Neptune": [
        {"name": "Triton", "color": (0.62, 0.67, 0.82), "min_px": 2, "radius_km": 1_353,
         "a_km": 354_759, "e": 0.000016, "i": 156.885,
         "Omega": 172.4, "omega": 352.0, "M0": 275.0,
         "epoch_jd": 2451545.0, "period_d": 5.87685},
    ],
    "Pluto": [
        {"name": "Charon", "color": (0.66, 0.61, 0.56), "min_px": 2, "radius_km": 606,
         "a_km": 19_591, "e": 0.0022, "i": 119.6,
         "Omega": 223.0, "omega": 188.0, "M0": 0.0,
         "epoch_jd": 2451545.0, "period_d": 6.38723},
    ],
}

# Flat lookup: moon name -> parent planet name (built at module load)
MOON_PARENT = {
    moon["name"]: planet
    for planet, moons in MOONS.items()
    for moon in moons
}

# Physical and orbital data shown in the info overlay
BODY_INFO = {
    # ---- Planets ----
    "Sun": {
        "diameter_km": 1_392_700,
        "mass_kg": 1.989e30,
        "rotation_days": 25.38,
        "orbital_period_y": None,
        "orbital_velocity_kms": None,
    },
    "Mercury": {
        "diameter_km": 4_879,
        "mass_kg": 3.285e23,
        "rotation_days": 58.65,
        "orbital_period_y": 0.241,
        "orbital_velocity_kms": 47.87,
    },
    "Venus": {
        "diameter_km": 12_104,
        "mass_kg": 4.867e24,
        "rotation_days": 243.02,
        "orbital_period_y": 0.615,
        "orbital_velocity_kms": 35.02,
    },
    "Earth": {
        "diameter_km": 12_742,
        "mass_kg": 5.972e24,
        "rotation_days": 1.0,
        "orbital_period_y": 1.0,
        "orbital_velocity_kms": 29.78,
    },
    "Mars": {
        "diameter_km": 6_779,
        "mass_kg": 6.39e23,
        "rotation_days": 1.026,
        "orbital_period_y": 1.881,
        "orbital_velocity_kms": 24.07,
    },
    "Jupiter": {
        "diameter_km": 139_820,
        "mass_kg": 1.898e27,
        "rotation_days": 0.414,
        "orbital_period_y": 11.86,
        "orbital_velocity_kms": 13.07,
    },
    "Saturn": {
        "diameter_km": 116_460,
        "mass_kg": 5.683e26,
        "rotation_days": 0.444,
        "orbital_period_y": 29.46,
        "orbital_velocity_kms": 9.69,
    },
    "Uranus": {
        "diameter_km": 50_724,
        "mass_kg": 8.681e25,
        "rotation_days": 0.718,
        "orbital_period_y": 84.01,
        "orbital_velocity_kms": 6.81,
    },
    "Neptune": {
        "diameter_km": 49_244,
        "mass_kg": 1.024e26,
        "rotation_days": 0.671,
        "orbital_period_y": 164.8,
        "orbital_velocity_kms": 5.43,
    },
    # ---- Asteroids ----
    "Ceres": {
        "diameter_km": 939,
        "mass_kg": 9.38e20,
        "rotation_days": 0.378,
        "orbital_period_y": 4.60,
        "orbital_velocity_kms": 17.9,
    },
    "Vesta": {
        "diameter_km": 525,
        "mass_kg": 2.59e20,
        "rotation_days": 0.223,
        "orbital_period_y": 3.63,
        "orbital_velocity_kms": 19.3,
    },
    "Pallas": {
        "diameter_km": 512,
        "mass_kg": 2.04e20,
        "rotation_days": 0.329,
        "orbital_period_y": 4.61,
        "orbital_velocity_kms": 17.9,
    },
    "Juno": {
        "diameter_km": 246,
        "mass_kg": 2.67e19,
        "rotation_days": 0.300,
        "orbital_period_y": 4.36,
        "orbital_velocity_kms": 18.3,
    },
    "Hygiea": {
        "diameter_km": 434,
        "mass_kg": 8.74e19,
        "rotation_days": 0.568,
        "orbital_period_y": 5.57,
        "orbital_velocity_kms": 16.8,
    },
    # ---- Minor/dwarf planets ----
    "Pluto": {
        "diameter_km": 2_376,
        "mass_kg": 1.303e22,
        "rotation_days": 6.387,
        "orbital_period_y": 247.94,
        "orbital_velocity_kms": 4.74,
    },
    "Eris": {
        "diameter_km": 2_326,
        "mass_kg": 1.66e22,
        "rotation_days": 15.79,
        "orbital_period_y": 558.04,
        "orbital_velocity_kms": 3.44,
    },
    "Haumea": {
        "diameter_km": 1_400,
        "mass_kg": 4.006e21,
        "rotation_days": 0.163,
        "orbital_period_y": 284.12,
        "orbital_velocity_kms": 4.53,
    },
    "Makemake": {
        "diameter_km": 1_430,
        "mass_kg": 3.1e21,
        "rotation_days": 0.951,
        "orbital_period_y": 306.21,
        "orbital_velocity_kms": 4.42,
    },
    "Sedna": {
        "diameter_km": 995,
        "mass_kg": 1.0e21,
        "rotation_days": 0.417,
        "orbital_period_y": 11408.0,
        "orbital_velocity_kms": 1.04,
    },
    # ---- Moons (orbital_period_y stored as days/365.25; velocity around parent) ----
    "Moon": {
        "diameter_km": 3_474,
        "mass_kg": 7.342e22,
        "rotation_days": 27.32,
        "orbital_period_y": 27.3217 / 365.25,
        "orbital_velocity_kms": 1.022,
    },
    "Phobos": {
        "diameter_km": 22,
        "mass_kg": 1.065e16,
        "rotation_days": 0.31891,
        "orbital_period_y": 0.31891 / 365.25,
        "orbital_velocity_kms": 2.138,
    },
    "Deimos": {
        "diameter_km": 12,
        "mass_kg": 1.476e15,
        "rotation_days": 1.26244,
        "orbital_period_y": 1.26244 / 365.25,
        "orbital_velocity_kms": 1.352,
    },
    "Io": {
        "diameter_km": 3_643,
        "mass_kg": 8.932e22,
        "rotation_days": 1.76914,
        "orbital_period_y": 1.76914 / 365.25,
        "orbital_velocity_kms": 17.334,
    },
    "Europa": {
        "diameter_km": 3_122,
        "mass_kg": 4.800e22,
        "rotation_days": 3.55182,
        "orbital_period_y": 3.55182 / 365.25,
        "orbital_velocity_kms": 13.740,
    },
    "Ganymede": {
        "diameter_km": 5_268,
        "mass_kg": 1.482e23,
        "rotation_days": 7.15455,
        "orbital_period_y": 7.15455 / 365.25,
        "orbital_velocity_kms": 10.880,
    },
    "Callisto": {
        "diameter_km": 4_821,
        "mass_kg": 1.076e23,
        "rotation_days": 16.6890,
        "orbital_period_y": 16.6890 / 365.25,
        "orbital_velocity_kms": 8.204,
    },
    "Mimas": {
        "diameter_km": 396,
        "mass_kg": 3.75e19,
        "rotation_days": 0.94242,
        "orbital_period_y": 0.94242 / 365.25,
        "orbital_velocity_kms": 14.28,
    },
    "Enceladus": {
        "diameter_km": 504,
        "mass_kg": 1.08e20,
        "rotation_days": 1.37022,
        "orbital_period_y": 1.37022 / 365.25,
        "orbital_velocity_kms": 12.63,
    },
    "Tethys": {
        "diameter_km": 1_062,
        "mass_kg": 6.18e20,
        "rotation_days": 1.88780,
        "orbital_period_y": 1.88780 / 365.25,
        "orbital_velocity_kms": 11.35,
    },
    "Dione": {
        "diameter_km": 1_123,
        "mass_kg": 1.096e21,
        "rotation_days": 2.73692,
        "orbital_period_y": 2.73692 / 365.25,
        "orbital_velocity_kms": 10.03,
    },
    "Rhea": {
        "diameter_km": 1_527,
        "mass_kg": 2.307e21,
        "rotation_days": 4.51750,
        "orbital_period_y": 4.51750 / 365.25,
        "orbital_velocity_kms": 8.48,
    },
    "Titan": {
        "diameter_km": 5_149,
        "mass_kg": 1.345e23,
        "rotation_days": 15.94540,
        "orbital_period_y": 15.94540 / 365.25,
        "orbital_velocity_kms": 5.57,
    },
    "Iapetus": {
        "diameter_km": 1_469,
        "mass_kg": 1.806e21,
        "rotation_days": 79.33180,
        "orbital_period_y": 79.33180 / 365.25,
        "orbital_velocity_kms": 3.26,
    },
    "Miranda": {
        "diameter_km": 471,
        "mass_kg": 6.59e19,
        "rotation_days": 1.41348,
        "orbital_period_y": 1.41348 / 365.25,
        "orbital_velocity_kms": 6.66,
    },
    "Ariel": {
        "diameter_km": 1_158,
        "mass_kg": 1.353e21,
        "rotation_days": 2.52038,
        "orbital_period_y": 2.52038 / 365.25,
        "orbital_velocity_kms": 5.51,
    },
    "Umbriel": {
        "diameter_km": 1_169,
        "mass_kg": 1.172e21,
        "rotation_days": 4.14418,
        "orbital_period_y": 4.14418 / 365.25,
        "orbital_velocity_kms": 4.67,
    },
    "Titania": {
        "diameter_km": 1_577,
        "mass_kg": 3.527e21,
        "rotation_days": 8.70588,
        "orbital_period_y": 8.70588 / 365.25,
        "orbital_velocity_kms": 3.64,
    },
    "Oberon": {
        "diameter_km": 1_523,
        "mass_kg": 3.014e21,
        "rotation_days": 13.46324,
        "orbital_period_y": 13.46324 / 365.25,
        "orbital_velocity_kms": 3.15,
    },
    "Triton": {
        "diameter_km": 2_707,
        "mass_kg": 2.139e22,
        "rotation_days": 5.87685,
        "orbital_period_y": 5.87685 / 365.25,
        "orbital_velocity_kms": 4.39,
    },
    "Charon": {
        "diameter_km": 1_212,
        "mass_kg": 1.586e21,
        "rotation_days": 6.38723,
        "orbital_period_y": 6.38723 / 365.25,
        "orbital_velocity_kms": 0.21,
    },
}

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
  Click body Show body info
  Escape     Close body info
"""

AU_KM = 1.496e8  # km per AU
DEFAULT_SCALE = 120.0  # pixels per AU
COI_ARM_PX = 13   # half-length of each arm of the COI '+' marker (screen pixels)
COI_HIT_PX = 15   # drag-detection radius around COI centre (screen pixels)


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


def kepler_pos(a, e, i_deg, Omega_deg, omega_deg, M0_deg, epoch_jd, period_y, jd):
    """Return (x, y) ecliptic-plane coordinates in AU via Keplerian propagation.

    For planets/asteroids the origin is the Sun; for moons the origin is the
    parent planet.  The returned offsets are in AU.
    """
    period_days = period_y * 365.25
    n = 2.0 * math.pi / period_days
    M = math.radians(M0_deg) + n * (jd - epoch_jd)
    M = M % (2.0 * math.pi)

    E = solve_kepler(M, e)
    nu = 2.0 * math.atan2(math.sqrt(1 + e) * math.sin(E / 2),
                           math.sqrt(1 - e) * math.cos(E / 2))
    r = a * (1 - e * math.cos(E))

    i   = math.radians(i_deg)
    Om  = math.radians(Omega_deg)
    w   = math.radians(omega_deg)

    cos_Om, sin_Om = math.cos(Om), math.sin(Om)
    cos_wnu, sin_wnu = math.cos(w + nu), math.sin(w + nu)
    cos_i = math.cos(i)

    x = r * (cos_Om * cos_wnu - sin_Om * sin_wnu * cos_i)
    y = r * (sin_Om * cos_wnu + cos_Om * sin_wnu * cos_i)
    return x, y


# Keep the old name as an alias so nothing else breaks
kepler_pos_heliocentric = kepler_pos


def kepler_orbit_points(body, n_points=360):
    """Return list of (x, y) points tracing one full closed orbit."""
    period_days = body["period_y"] * 365.25
    pts = []
    for k in range(n_points):
        jd = body["epoch_jd"] + (k / n_points) * period_days
        x, y = kepler_pos(body["a"], body["e"], body["i"], body["Omega"],
                          body["omega"], body["M0"], body["epoch_jd"],
                          body["period_y"], jd)
        pts.append((x, y))
    if pts:
        pts.append(pts[0])
    return pts


def moon_orbit_points(moon, n_points=120):
    """Return list of (dx, dy) offsets in AU tracing one full moon orbit."""
    period_y = moon["period_d"] / 365.25
    a_au = moon["a_km"] / AU_KM
    pts = []
    for k in range(n_points):
        jd = moon["epoch_jd"] + (k / n_points) * moon["period_d"]
        dx, dy = kepler_pos(a_au, moon["e"], moon["i"], moon["Omega"],
                            moon["omega"], moon["M0"], moon["epoch_jd"],
                            period_y, jd)
        pts.append((dx, dy))
    if pts:
        pts.append(pts[0])
    return pts


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
        self._locked_target_sx = 0.0    # screen x we want the locked body to stay at
        self._locked_target_sy = 0.0    # screen y we want the locked body to stay at

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

        # Body positions: name -> (x_au, y_au)  — includes moons (heliocentric)
        self.positions = {}
        # Precomputed orbit paths
        self.orbit_paths = {}       # planet/asteroid: name -> [(x,y) AU heliocentric]
        self.moon_orbit_paths = {}  # moon: name -> [(dx,dy) AU relative to parent]

        # Info overlay state
        self.selected_body = None
        self._overlay_rect = None
        self._image_cache = {}

        self.positions["Sun"] = (0.0, 0.0)

        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)

        self._precompute_orbits()
        self._precompute_moon_orbits()
        self._compute_positions(force=True)

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
            self.coi_au = (0.0, 0.0)
            self._locked_body = None
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
                if self._locked_body:
                    self._locked_target_sx += dx
                    self._locked_target_sy += dy
            self._last_touch = touch.pos
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            if not self._dragging and self._drag_origin:
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
            if name not in self.positions:
                continue
            sx, sy = self.world_to_screen(*self.positions[name])
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
            if name not in self.positions:
                continue
            sx, sy = self.world_to_screen(*self.positions[name])
            radius_km = body.get("radius_km", 0)
            min_px = body.get("min_px", 2)
            px = max(radius_km / AU_KM * self.scale, min_px) if radius_km > 0 else min_px
            dist = math.hypot(coi_sx - sx, coi_sy - sy)
            if dist <= px * 5 and dist < best_dist:
                best_dist = dist
                best_name = name

        if best_name:
            self._locked_body = best_name
            # Snap COI to body centre and record its current screen position
            self.coi_au = self.positions[best_name]
            self._locked_target_sx, self._locked_target_sy = self.world_to_screen(*self.coi_au)

    def _update_coi_lock(self):
        """Move COI with locked body and pan so it stays at the recorded screen position."""
        if self._locked_body not in self.positions:
            self._locked_body = None
            return
        self.coi_au = self.positions[self._locked_body]
        coi_x, coi_y = self.coi_au
        self.pan_x = self._locked_target_sx - self.width / 2 - coi_x * self.scale
        self.pan_y = self._locked_target_sy - self.height / 2 - coi_y * self.scale

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

    # -- Orbit precomputation ----------------------------------------------

    def _precompute_orbits(self):
        with solar_system_ephemeris.set("builtin"):
            for body in PLANETS[1:]:
                name = body["name"].lower()
                period = ORBITAL_PERIODS.get(body["name"], 1.0)
                n_points = min(max(360, int(period * 120)), 1800)
                t0 = self.sim_time
                times = [t0 + TimeDelta(k / n_points * period * 365.25, format="jd")
                         for k in range(n_points)]
                points = []
                for t in times:
                    try:
                        sun_pos  = get_body_barycentric("sun", t)
                        body_pos = get_body_barycentric(name, t)
                        x = body_pos.x.to(u.AU).value - sun_pos.x.to(u.AU).value
                        y = body_pos.y.to(u.AU).value - sun_pos.y.to(u.AU).value
                        points.append((x, y))
                    except Exception:
                        pass
                if points:
                    points.append(points[0])
                self.orbit_paths[body["name"]] = points

        for body in ASTEROIDS + MINOR_PLANETS:
            self.orbit_paths[body["name"]] = kepler_orbit_points(body, n_points=360)

    def _precompute_moon_orbits(self):
        """Precompute planet-relative orbit paths for all moons (done once)."""
        for moons in MOONS.values():
            for moon in moons:
                self.moon_orbit_paths[moon["name"]] = moon_orbit_points(moon)

    # -- Position computation ----------------------------------------------

    def _compute_positions(self, force=False):
        jd = self.sim_time.jd
        if not force and abs(jd - self._last_computed_jd) < 0.1:
            return
        self._last_computed_jd = jd

        with solar_system_ephemeris.set("builtin"):
            try:
                sun_pos = get_body_barycentric("sun", self.sim_time)
                sun_x = sun_pos.x.to(u.AU).value
                sun_y = sun_pos.y.to(u.AU).value
            except Exception:
                sun_x, sun_y = 0.0, 0.0

            self.positions["Sun"] = (0.0, 0.0)
            for body in PLANETS[1:]:
                try:
                    pos = get_body_barycentric(body["name"].lower(), self.sim_time)
                    self.positions[body["name"]] = (
                        pos.x.to(u.AU).value - sun_x,
                        pos.y.to(u.AU).value - sun_y,
                    )
                except Exception:
                    self.positions[body["name"]] = (0.0, 0.0)

        for body in ASTEROIDS + MINOR_PLANETS:
            self.positions[body["name"]] = kepler_pos(
                body["a"], body["e"], body["i"], body["Omega"], body["omega"],
                body["M0"], body["epoch_jd"], body["period_y"], jd)

        # Moon positions = parent heliocentric + Keplerian offset from parent
        for planet_name, moons in MOONS.items():
            px, py = self.positions.get(planet_name, (0.0, 0.0))
            for moon in moons:
                a_au = moon["a_km"] / AU_KM
                dx, dy = kepler_pos(
                    a_au, moon["e"], moon["i"], moon["Omega"], moon["omega"],
                    moon["M0"], moon["epoch_jd"], moon["period_d"] / 365.25, jd)
                self.positions[moon["name"]] = (px + dx, py + dy)

    # -- Main update loop --------------------------------------------------

    def _update(self, dt):
        if not self.paused:
            self.sim_time += TimeDelta(dt * self.time_factor, format="sec")
            self._compute_positions()
        if self._locked_body:
            self._update_coi_lock()
        self._draw()
        self._update_info()

    def _update_info(self):
        iso = self.sim_time.iso[:19]
        state = "PAUSED" if self.paused else f"x{self.time_factor:g}"
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

            self._draw_coi_marker()
            self._draw_info_overlay()

    def _draw_orbits(self):
        for body in PLANETS[1:]:
            path = self.orbit_paths.get(body["name"], [])
            if len(path) < 2:
                continue
            r, g, b = body["color"]
            Color(r, g, b, 0.25)
            pts = []
            for x_au, y_au in path:
                pts.extend(self.world_to_screen(x_au, y_au))
            Line(points=pts, width=1.1)

        for body in ASTEROIDS + MINOR_PLANETS:
            path = self.orbit_paths.get(body["name"], [])
            if len(path) < 2:
                continue
            r, g, b = body["color"]
            Color(r, g, b, 0.2)
            pts = []
            for x_au, y_au in path:
                pts.extend(self.world_to_screen(x_au, y_au))
            Line(points=pts, width=1.1, dash_length=4, dash_offset=4)

    def _draw_moon_orbits(self, planet_name):
        """Draw orbit rings for all moons of planet_name, centered on the planet."""
        planet_pos = self.positions.get(planet_name, (0.0, 0.0))
        p_sx, p_sy = self.world_to_screen(*planet_pos)
        for moon in MOONS[planet_name]:
            path = self.moon_orbit_paths.get(moon["name"], [])
            if len(path) < 2:
                continue
            r, g, b = moon["color"]
            Color(r, g, b, 0.35)
            pts = []
            for dx_au, dy_au in path:
                pts.append(p_sx + dx_au * self.scale)
                pts.append(p_sy + dy_au * self.scale)
            Line(points=pts, width=1)

    def _draw_body(self, body):
        name = body["name"]
        if name not in self.positions:
            return
        sx, sy = self.world_to_screen(*self.positions[name])

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
        pos_au = self.positions.get(name, (0.0, 0.0))
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
            size=(400, 30),
            pos_hint={"right": 0.99, "top": 0.99},
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
