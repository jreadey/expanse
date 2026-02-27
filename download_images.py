"""Download body images for the orrery from Wikimedia Commons."""

import os
import urllib.request

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# Wikimedia Commons URLs for public domain / CC images (sized thumbnails)
URLS = {
    "Sun": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/The_Sun_by_the_Atmospheric_Imaging_Assembly_of_NASA%27s_Solar_Dynamics_Observatory_-_20100819.jpg/240px-The_Sun_by_the_Atmospheric_Imaging_Assembly_of_NASA%27s_Solar_Dynamics_Observatory_-_20100819.jpg",
    "Mercury": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Mercury_in_true_color.jpg/240px-Mercury_in_true_color.jpg",
    "Venus": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b2/Venus_2_Approach_Image.jpg/240px-Venus_2_Approach_Image.jpg",
    "Earth": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cb/The_Blue_Marble_%28remastered%29.jpg/240px-The_Blue_Marble_%28remastered%29.jpg",
    "Mars": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Mars_-_August_30_2021_-_Flickr_-_Kevin_M._Gill.png/240px-Mars_-_August_30_2021_-_Flickr_-_Kevin_M._Gill.png",
    "Jupiter": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Jupiter_New_Horizons.jpg/240px-Jupiter_New_Horizons.jpg",
    "Saturn": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Saturn_during_Equinox.jpg/300px-Saturn_during_Equinox.jpg",
    "Uranus": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c9/Uranus_as_seen_by_NASA%27s_Voyager_2_%28reprocessed%29_-_JPEG_converted.jpg/240px-Uranus_as_seen_by_NASA%27s_Voyager_2_%28reprocessed%29_-_JPEG_converted.jpg",
    "Neptune": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b9/Neptune_Voyager2_color_calibrated.png/240px-Neptune_Voyager2_color_calibrated.png",
    "Pluto": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/Pluto_in_True_Color_-_High-Res.jpg/240px-Pluto_in_True_Color_-_High-Res.jpg",
    "Ceres": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/76/Ceres_-_RC3_-_Haulani_Crater_%2822381131691%29_%28cropped%29.jpg/240px-Ceres_-_RC3_-_Haulani_Crater_%2822381131691%29_%28cropped%29.jpg",
    "Eris": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Eris_and_dysnomia2.jpg/240px-Eris_and_dysnomia2.jpg",
    "Haumea": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2b/Haumea_Hubble.png/240px-Haumea_Hubble.png",
    "Makemake": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Makemake_and_its_moon.jpg/240px-Makemake_and_its_moon.jpg",
}

for name, url in URLS.items():
    ext = ".jpg" if ".jpg" in url.lower() else ".png"
    path = os.path.join(IMAGES_DIR, f"{name.lower()}{ext}")
    if os.path.exists(path):
        print(f"  skip {name} (already exists)")
        continue
    print(f"  downloading {name}...")
    try:
        req = urllib.request.Request(url) #, headers={"User-Agent": "OrreryApp/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        with open(path, "wb") as f:
            f.write(data)
        print(f"  saved {path} ({len(data)} bytes)")
    except Exception as e:
        print(f"  FAILED {name}: {e}")

print("Done.")
