import os
from PIL import Image, ImageStat
import subprocess

IMG_DIR = "docs/img"
THRESHOLD_VAR = 5.0  # variance trop basse → image quasi plate

def is_flat_image(path):
    try:
        with Image.open(path) as img:
            img = img.convert("L")  # niveaux de gris
            stat = ImageStat.Stat(img)
            variance = stat.var[0]
            return variance < THRESHOLD_VAR, variance
    except Exception as e:
        print(f"⚠️ Erreur {path}: {e}")
        return False, None

def main():
    removed = []
    for fname in os.listdir(IMG_DIR):
        if not fname.lower().endswith(".png"):
            continue
        fpath = os.path.join(IMG_DIR, fname)
        flat, var = is_flat_image(fpath)
        if flat:
            print(f"🗑 Suppression {fname} (variance={var:.3f})")
            subprocess.run(["git", "rm", fpath])
            removed.append(fname)
        else:
            print(f"✅ Garde {fname} (variance={var:.3f})")

    if removed:
        msg = "chore(docs): remove empty plots"
        subprocess.run(["git", "commit", "-m", msg])
        subprocess.run(["git", "push"])
    else:
        print("👌 Aucun plot vide détecté.")

if __name__ == "__main__":
    main()
