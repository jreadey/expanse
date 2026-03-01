"""Solar system body data, orbital mechanics helpers, and Simulation class."""

import math
import warnings
from datetime import datetime

import astropy.units as u
from astropy.constants import au as _au
from astropy.time import Time, TimeDelta
from astropy.coordinates import CartesianRepresentation, get_body_barycentric, solar_system_ephemeris
from erfa import ErfaWarning

warnings.filterwarnings("ignore", category=ErfaWarning)


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

# ---------------------------------------------------------------------------
# Ship definitions
# ---------------------------------------------------------------------------

SHIPS = [
    {
        "name": "Starship v2",
        "length_m": 52,           # metres
        "width_m": 9,             # metres
        "dry_mass_t": 52,         # metric tons
        "max_fuel_t": 1500,       # metric tons
        "max_thrust_N": 15e6,     # Newtons (15 MN)
        "isp_s": 350,             # specific impulse (s) — chemical (Raptor-class)
        "color": (0.85, 0.95, 1.0),
        "min_px": 20,             # drawn nose-to-base length in pixels
    },
]

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

AU_M  = _au.value        # metres per AU (IAU 2012: 149 597 870 700 m exactly)
AU_KM = AU_M / 1e3      # km per AU

# Standard gravitational parameters μ = G·M (m³/s²) for bodies that
# exert meaningful gravity on the ship.
GRAVITY_GM = {
    "Sun":     1.32712440018e20,
    "Mercury": 2.2032e13,
    "Venus":   3.24859e14,
    "Earth":   3.986004418e14,
    "Moon":    4.9048695e12,
    "Mars":    4.282837e13,
    "Jupiter": 1.26686534e17,
    "Saturn":  3.7931187e16,
    "Uranus":  5.793987e15,
    "Neptune": 6.836529e15,
}

# Surface radii in metres — used as minimum safe distance in the gravity loop
# to prevent singularities when the ship passes near a body.
_BODY_RADIUS_M = {
    "Sun":     696_340e3,
    "Mercury":   2_439e3,
    "Venus":     6_051e3,
    "Earth":     6_371e3,
    "Moon":      1_737e3,
    "Mars":      3_389e3,
    "Jupiter":  69_911e3,
    "Saturn":   58_232e3,
    "Uranus":   25_362e3,
    "Neptune":  24_622e3,
}
BODY_MIN_DIST_SQ_M = {name: r * r for name, r in _BODY_RADIUS_M.items()}


def xy(pos):
    """Project a CartesianRepresentation to a plain (x_au, y_au) float tuple."""
    return pos.x.to(u.AU).value, pos.y.to(u.AU).value


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
    """Return a CartesianRepresentation (x, y, z) in AU via Keplerian propagation.

    For planets/asteroids the origin is the Sun; for moons the origin is the
    parent planet.  All components are in AU.
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
    cos_i, sin_i = math.cos(i), math.sin(i)

    x = r * (cos_Om * cos_wnu - sin_Om * sin_wnu * cos_i)
    y = r * (sin_Om * cos_wnu + cos_Om * sin_wnu * cos_i)
    z = r * sin_i * sin_wnu
    return CartesianRepresentation(x * u.AU, y * u.AU, z * u.AU)


# Keep the old name as an alias so nothing else breaks
kepler_pos_heliocentric = kepler_pos


def kepler_orbit_points(body, n_points=360):
    """Return list of CartesianRepresentation points tracing one full closed orbit."""
    period_days = body["period_y"] * 365.25
    pts = []
    for k in range(n_points):
        jd = body["epoch_jd"] + (k / n_points) * period_days
        pts.append(kepler_pos(body["a"], body["e"], body["i"], body["Omega"],
                              body["omega"], body["M0"], body["epoch_jd"],
                              body["period_y"], jd))
    if pts:
        pts.append(pts[0])
    return pts


def moon_orbit_points(moon, n_points=120):
    """Return list of CartesianRepresentation offsets in AU tracing one full moon orbit."""
    period_y = moon["period_d"] / 365.25
    a_au = moon["a_km"] / AU_KM
    pts = []
    for k in range(n_points):
        jd = moon["epoch_jd"] + (k / n_points) * moon["period_d"]
        pts.append(kepler_pos(a_au, moon["e"], moon["i"], moon["Omega"],
                              moon["omega"], moon["M0"], moon["epoch_jd"],
                              period_y, jd))
    if pts:
        pts.append(pts[0])
    return pts


# ---------------------------------------------------------------------------
# Ship
# ---------------------------------------------------------------------------

class Ship:
    """A player-controlled spacecraft."""

    def __init__(self, defn, pos_au, vel_ms):
        self.defn = defn               # ship definition dict (from SHIPS)
        self.pos  = pos_au             # CartesianRepresentation (heliocentric AU)
        self.vel  = vel_ms             # (vx_ms, vy_ms, vz_ms) — updated each physics tick
        self._orientation_deg = 0.0   # degrees CW from north (in the x-y plane)
        self._elevation_deg   = 0.0   # degrees above the x-y plane (-90 to +90)
        self._thrust_pct      = 0.0   # throttle 0–100 %
        self._fuel_t          = defn["max_fuel_t"]  # metric tons remaining
        self._sim             = None  # back-reference set by Simulation.init_ship()

    @property
    def position(self):
        """Current position as a CartesianRepresentation in AU (heliocentric)."""
        return self.pos
    
    @property
    def velocity(self):
        """Current velocity as a (vx_ms, vy_ms, vz_ms) tuple in m/s."""
        return self.vel
    
    @property
    def orientation(self):
        """Orientation in degrees clockwise from north (in the x-y ecliptic plane)."""
        return self._orientation_deg

    @property
    def elevation(self):
        """Elevation above the x-y ecliptic plane in degrees (-90 to +90)."""
        return self._elevation_deg

    @property
    def thrust(self):
        """Throttle level as a percentage (0–100)."""
        return self._thrust_pct

    @property
    def fuel(self):
        """Remaining fuel in metric tons."""
        return self._fuel_t

    def set_orientation(self, degrees, elevation=None):
        """Set orientation in degrees CW from north (x-y plane).

        If *elevation* is provided it is clamped to [-90, +90] degrees.
        If omitted, the current elevation is unchanged.
        """
        self._orientation_deg = degrees % 360
        if elevation is not None:
            self._elevation_deg = max(-90.0, min(90.0, float(elevation)))

    def set_thrust(self, pct):
        """Set throttle level, clamped to 0–100 %.

        Raises ValueError if pct > 0 and the tank is empty.
        """
        if pct > 0.0 and self._fuel_t <= 0.0:
            raise ValueError("Cannot set thrust: fuel is empty")
        self._thrust_pct = max(0.0, min(100.0, pct))

    def dist(self, name):
        """Return distance in AU between the ship and *name*.

        Raises ValueError if the body name is not recognised.
        """
        if self._sim is None:
            raise RuntimeError("Ship has no Simulation reference")
        body_pos = self._sim.positions.get(name)
        if body_pos is None:
            raise ValueError(f"Unknown body: {name!r}")
        dx = (self.pos.x - body_pos.x).to(u.AU).value
        dy = (self.pos.y - body_pos.y).to(u.AU).value
        dz = (self.pos.z - body_pos.z).to(u.AU).value
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def relative_velocity(self, name):
        """Return speed in m/s of the ship relative to *name*.

        Raises ValueError if the body name is not recognised.
        """
        if self._sim is None:
            raise RuntimeError("Ship has no Simulation reference")
        if name not in self._sim.positions:
            raise ValueError(f"Unknown body: {name!r}")
        bv = self._sim.body_vel_ms.get(name, (0.0, 0.0))
        dvx = self.vel[0] - bv[0]
        dvy = self.vel[1] - bv[1]
        dvz = self.vel[2] - (bv[2] if len(bv) > 2 else 0.0)
        return math.sqrt(dvx * dvx + dvy * dvy + dvz * dvz)


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

class Simulation:
    """All orbital mechanics and ship physics, independent of any GUI framework."""

    def __init__(self, sim_time=None, time_factor=1.0, paused=False):
        if sim_time:
            self.sim_time = sim_time
        else:
            self.sim_time = Time(datetime.utcnow(), scale="utc")
        self.time_factor = time_factor
        self.paused = paused
        self._crashed = False
        self._crash_body = None
        self._last_computed_jd = 0.0

        # Body positions: name -> CartesianRepresentation (heliocentric AU)
        self.positions = {"Sun": CartesianRepresentation(0.0, 0.0, 0.0, unit=u.AU)}
        # Estimated body velocities (m/s) from position diffs, updated each compute cycle
        self.body_vel_ms = {}
        # Precomputed orbit paths
        self.orbit_paths = {}       # planet/asteroid: name -> [(x,y) AU heliocentric]
        self.moon_orbit_paths = {}  # moon: name -> [(dx,dy) AU relative to parent]

        self.ship = None  # set by init_ship()

        self.precompute_orbits()
        self.precompute_moon_orbits()
        self.compute_positions(force=True)
        self._bootstrap_body_velocities()
        self.init_ship()

    # -- Orbit precomputation ----------------------------------------------

    def precompute_orbits(self):
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
                        points.append(CartesianRepresentation(
                            (body_pos.x - sun_pos.x).to(u.AU),
                            (body_pos.y - sun_pos.y).to(u.AU),
                            (body_pos.z - sun_pos.z).to(u.AU),
                        ))
                    except Exception:
                        pass
                if points:
                    points.append(points[0])
                self.orbit_paths[body["name"]] = points

        for body in ASTEROIDS + MINOR_PLANETS:
            self.orbit_paths[body["name"]] = kepler_orbit_points(body, n_points=360)

    def precompute_moon_orbits(self):
        """Precompute planet-relative orbit paths for all moons (done once)."""
        for moons in MOONS.values():
            for moon in moons:
                self.moon_orbit_paths[moon["name"]] = moon_orbit_points(moon)

    # -- Position computation ----------------------------------------------

    def _bootstrap_body_velocities(self):
        """Seed body_vel_ms at startup using a 60-second ephemeris finite-diff.

        compute_positions() derives velocities from successive position snapshots,
        but its first snapshot only contains the Sun (the initial placeholder), so
        planet velocities are never populated until the simulation has advanced
        0.1 JD.  This method fills body_vel_ms with accurate values immediately
        so that Ship.relative_velocity() is correct from the first frame.
        """
        dt_s = 60.0
        t0 = self.sim_time
        t1 = t0 + TimeDelta(dt_s, format="sec")
        with solar_system_ephemeris.set("builtin"):
            try:
                sun0 = get_body_barycentric("sun", t0)
                sun1 = get_body_barycentric("sun", t1)
            except Exception:
                return
            for body in PLANETS[1:]:
                try:
                    p0 = get_body_barycentric(body["name"].lower(), t0)
                    p1 = get_body_barycentric(body["name"].lower(), t1)
                    dx_m = ((p1.x - p0.x) - (sun1.x - sun0.x)).to(u.m).value
                    dy_m = ((p1.y - p0.y) - (sun1.y - sun0.y)).to(u.m).value
                    dz_m = ((p1.z - p0.z) - (sun1.z - sun0.z)).to(u.m).value
                    self.body_vel_ms[body["name"]] = (dx_m / dt_s, dy_m / dt_s, dz_m / dt_s)
                except Exception:
                    pass

    def compute_positions(self, force=False):
        jd = self.sim_time.jd
        if not force and abs(jd - self._last_computed_jd) < 0.001:
            return
        prev_jd  = self._last_computed_jd
        prev_pos = dict(self.positions)
        self._last_computed_jd = jd

        with solar_system_ephemeris.set("builtin"):
            try:
                sun_pos = get_body_barycentric("sun", self.sim_time)
            except Exception:
                sun_pos = None

            self.positions["Sun"] = CartesianRepresentation(0.0, 0.0, 0.0, unit=u.AU)
            for body in PLANETS[1:]:
                try:
                    pos = get_body_barycentric(body["name"].lower(), self.sim_time)
                    if sun_pos is not None:
                        self.positions[body["name"]] = CartesianRepresentation(
                            (pos.x - sun_pos.x).to(u.AU),
                            (pos.y - sun_pos.y).to(u.AU),
                            (pos.z - sun_pos.z).to(u.AU),
                        )
                    else:
                        self.positions[body["name"]] = CartesianRepresentation(
                            pos.x.to(u.AU), pos.y.to(u.AU), pos.z.to(u.AU),
                        )
                except Exception:
                    self.positions[body["name"]] = CartesianRepresentation(0.0, 0.0, 0.0, unit=u.AU)

        for body in ASTEROIDS + MINOR_PLANETS:
            self.positions[body["name"]] = kepler_pos(
                body["a"], body["e"], body["i"], body["Omega"], body["omega"],
                body["M0"], body["epoch_jd"], body["period_y"], jd)

        # Moon positions = parent heliocentric + Keplerian offset from parent
        _zero = CartesianRepresentation(0.0, 0.0, 0.0, unit=u.AU)
        for planet_name, moons in MOONS.items():
            parent_pos = self.positions.get(planet_name, _zero)
            for moon in moons:
                a_au = moon["a_km"] / AU_KM
                offset = kepler_pos(
                    a_au, moon["e"], moon["i"], moon["Omega"], moon["omega"],
                    moon["M0"], moon["epoch_jd"], moon["period_d"] / 365.25, jd)
                self.positions[moon["name"]] = CartesianRepresentation(
                    parent_pos.x + offset.x,
                    parent_pos.y + offset.y,
                    parent_pos.z + offset.z,
                )

        # Estimate body velocities from position change since last compute.
        dt_s = (jd - prev_jd) * 86400.0
        if dt_s > 0.0 and prev_pos:
            for name, new_pos in self.positions.items():
                if name in prev_pos:
                    dx_m = (new_pos.x - prev_pos[name].x).to(u.m).value
                    dy_m = (new_pos.y - prev_pos[name].y).to(u.m).value
                    dz_m = (new_pos.z - prev_pos[name].z).to(u.m).value
                    self.body_vel_ms[name] = (dx_m / dt_s, dy_m / dt_s, dz_m / dt_s)

    # -- Ship --------------------------------------------------------------

    def init_ship(self):
        """Place the ship 200 km above Earth, nose pointing north, engine off."""
        defn = SHIPS[0]
        earth_pos = self.positions.get("Earth")
        ex, ey = xy(earth_pos) if earth_pos is not None else (1.0, 0.0)
        dist = math.hypot(ex, ey)
        ux, uy = (ex / dist, ey / dist) if dist > 0 else (1.0, 0.0)
        # Offset from Earth centre: Earth radius + 200 km, in AU
        offset_au = (6371 + 200) / AU_KM
        # Prograde direction: 90° CCW from the radial (Sun→Earth) unit vector.
        pg_x, pg_y = -uy, ux

        # Earth's velocity must be taken as a full vector, not just a magnitude
        # applied in the tangential direction.  Near perihelion Earth has a
        # ~374 m/s radial (outward) component (flight-path angle ~0.7°).
        # Applying only the tangential component gives the ship 374 m/s inward
        # relative to Earth, putting the orbit's periapsis inside Earth's surface
        # and triggering the singularity guard.
        # Solution: finite-difference the ephemeris over 60 s to get the exact
        # heliocentric velocity vector, then add the LEO circular speed on top.
        jd    = self.sim_time.jd
        dt_s  = 60.0
        with solar_system_ephemeris.set("builtin"):
            t0     = Time(jd,                format="jd")
            t1     = Time(jd + dt_s/86400., format="jd")
            sun0   = get_body_barycentric("Sun",   t0)
            sun1   = get_body_barycentric("Sun",   t1)
            earth0 = get_body_barycentric("Earth", t0)
            earth1 = get_body_barycentric("Earth", t1)
        vex = ((earth1.x - earth0.x) - (sun1.x - sun0.x)).to(u.m).value / dt_s
        vey = ((earth1.y - earth0.y) - (sun1.y - sun0.y)).to(u.m).value / dt_s
        vez = ((earth1.z - earth0.z) - (sun1.z - sun0.z)).to(u.m).value / dt_s

        # Add circular LEO speed prograde around Earth
        r_ship_m = (6371 + 200) * 1e3
        v_circ   = math.sqrt(GRAVITY_GM["Earth"] / r_ship_m)

        # Use Earth's actual ICRS z — get_body_barycentric returns equatorial
        # (ICRS) coordinates; the ecliptic is tilted ~23.4° so Earth's z is
        # non-zero (~0.134 AU today).  Hardcoding z=0 would place the ship
        # ~0.134 AU away from Earth in the z direction.
        ez = earth_pos.z if earth_pos is not None else 0.0 * u.AU

        self.ship = Ship(
            defn   = defn,
            pos_au = CartesianRepresentation(
                (ex + ux * offset_au) * u.AU,
                (ey + uy * offset_au) * u.AU,
                ez,
            ),
            vel_ms = (vex + v_circ * pg_x, vey + v_circ * pg_y, vez),
        )
        self.ship._sim = self

    def update_ship_physics(self, sim_dt):
        """Integrate ship motion under gravity using symplectic Euler.

        sim_dt  -- total simulated time for this frame, in seconds.

        Uses sub-steps so that near-Earth orbits remain reasonably accurate
        even at elevated time factors.  Body positions are held fixed across
        the sub-steps (they change slowly compared with the ship).
        """
        if sim_dt <= 0.0:
            return

        # Extrapolate body positions to the start of this tick using their
        # velocities.  compute_positions() only fires every 0.1 JD (8 640 s),
        # so self.positions[] can be stale by that much.  For a ship in LEO
        # (~6 600 km altitude) Earth moves ~268 000 km between updates — far
        # enough to destroy the orbit entirely.  Linear extrapolation reduces
        # the error to O(a·dt_sub²) ≈ a few metres per sub-step.
        #
        # tick() advances sim_time by sim_dt BEFORE calling us, so:
        #   _last_computed_jd → time of the stored positions
        #   sim_time          → end of this tick
        #   tick start        → sim_time − sim_dt
        # Offset from stored positions to tick start:
        dt_to_tick_start = (self.sim_time.jd - self._last_computed_jd) * 86400.0 - sim_dt

        body_pos0_m = {}   # body position (m) extrapolated to tick start
        body_vel3d  = {}   # body velocity (m/s) as (vx, vy, vz)
        for name in GRAVITY_GM:
            if name not in self.positions:
                continue
            bx = self.positions[name].x.to(u.m).value
            by = self.positions[name].y.to(u.m).value
            bz = self.positions[name].z.to(u.m).value
            bv = self.body_vel_ms.get(name, (0.0, 0.0, 0.0))
            bvx = bv[0]; bvy = bv[1]; bvz = bv[2] if len(bv) > 2 else 0.0
            body_pos0_m[name] = (
                bx + bvx * dt_to_tick_start,
                by + bvy * dt_to_tick_start,
                bz + bvz * dt_to_tick_start,
            )
            body_vel3d[name] = (bvx, bvy, bvz)

        # Thrust setup — precompute direction unit vector and exhaust velocity.
        # These are constant across all sub-steps (orientation/throttle don't
        # change mid-tick and the mass change per step is negligible).
        defn = self.ship.defn
        _G0 = 9.80665  # m/s²
        exhaust_v = defn.get("isp_s", 100_000) * _G0
        az_rad = math.radians(self.ship._orientation_deg)
        el_rad = math.radians(self.ship._elevation_deg)
        cos_el = math.cos(el_rad)
        tux = cos_el * math.cos(az_rad)
        tuy = cos_el * math.sin(az_rad)
        tuz = math.sin(el_rad)

        # Sub-step sizing: target ≤30 s per step, hard cap at 200 steps/frame
        n_steps = min(200, max(1, int(sim_dt / 30.0)))
        dt = sim_dt / n_steps

        px_m = self.ship.pos.x.to(u.m).value
        py_m = self.ship.pos.y.to(u.m).value
        pz_m = self.ship.pos.z.to(u.m).value
        vx, vy, vz = self.ship.vel

        for step_i in range(n_steps):
            # Extrapolate each body to the current sub-step time
            t_offset = step_i * dt
            ax = ay = az = 0.0
            hit_body = None
            for name, (bx0, by0, bz0) in body_pos0_m.items():
                bvx, bvy, bvz = body_vel3d[name]
                bx = bx0 + bvx * t_offset
                by = by0 + bvy * t_offset
                bz = bz0 + bvz * t_offset
                dx = bx - px_m
                dy = by - py_m
                dz = bz - pz_m
                r2 = dx * dx + dy * dy + dz * dz
                r_min_sq = BODY_MIN_DIST_SQ_M.get(name, 1e6)
                if r2 < r_min_sq:
                    if name in BODY_MIN_DIST_SQ_M:   # real body surface → crash
                        hit_body = name
                    continue
                inv_r = 1.0 / math.sqrt(r2)
                a_mag = GRAVITY_GM[name] * inv_r * inv_r   # GM / r²
                ax += a_mag * dx * inv_r                   # a_mag * (dx/r)
                ay += a_mag * dy * inv_r
                az += a_mag * dz * inv_r

            if hit_body:
                self._crashed    = True
                self._crash_body = hit_body
                self.paused      = True
                break  # stop sub-stepping on impact

            # Thrust — apply engine acceleration and consume fuel
            if self.ship._fuel_t > 0.0 and self.ship._thrust_pct > 0.0:
                total_mass_kg = (defn["dry_mass_t"] + self.ship._fuel_t) * 1000.0
                thrust_N      = self.ship._thrust_pct / 100.0 * defn["max_thrust_N"]
                thrust_accel  = thrust_N / total_mass_kg
                ax += thrust_accel * tux
                ay += thrust_accel * tuy
                az += thrust_accel * tuz
                fuel_consumed_kg  = (thrust_N / exhaust_v) * dt
                self.ship._fuel_t = max(0.0, self.ship._fuel_t - fuel_consumed_kg / 1000.0)
                if self.ship._fuel_t <= 0.0:
                    self.ship._thrust_pct = 0.0   # auto cut-off on empty tank

            # Symplectic Euler: update velocity first, then position
            vx += ax * dt
            vy += ay * dt
            vz += az * dt
            px_m += vx * dt
            py_m += vy * dt
            pz_m += vz * dt
        self.ship.pos = CartesianRepresentation(
            (px_m / AU_M) * u.AU,
            (py_m / AU_M) * u.AU,
            (pz_m / AU_M) * u.AU,
        )
        self.ship.vel = (vx, vy, vz)

    # -- Time step ---------------------------------------------------------

    def tick(self, real_dt):
        """Advance simulation by real_dt wall-clock seconds (no-op when paused)."""
        if self.paused:
            return
        sim_dt = real_dt * self.time_factor
        self.sim_time += TimeDelta(sim_dt, format="sec")
        self.compute_positions()
        self.update_ship_physics(sim_dt)
