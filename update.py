#!/usr/bin/env python3
import os
import io
import glob
import hashlib
import tarfile
import subprocess
import lzma
import bz2

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
DEBS_DIR = os.path.join(REPO_DIR, "debs")

REPO_NAME = "xvoide's Repo"
REPO_DESCRIPTION = "Личный репозиторий твиков для Dopamine и Sileo"
ARCHITECTURES = "iphoneos-arm64"

def get_hash(data, algo):
    h = getattr(hashlib, algo)()
    h.update(data)
    return h.hexdigest()

def extract_control_from_deb(deb_path):
    # Узнаем содержимое ar-архива
    ar_list = subprocess.check_output(["ar", "t", deb_path]).decode().splitlines()
    control_archive_name = None
    for item in ar_list:
        if item.startswith("control.tar"):
            control_archive_name = item
            break
    
    if not control_archive_name:
        raise ValueError(f"Не найден control.tar в {deb_path}")

    # Извлекаем control.tar.* в память
    raw_tar = subprocess.check_output(["ar", "p", deb_path, control_archive_name])
    
    # Открываем tar
    with tarfile.open(fileobj=io.BytesIO(raw_tar)) as tar:
        for member in tar.getmembers():
            if member.name.strip("./") == "control":
                f = tar.extractfile(member)
                return f.read().decode("utf-8", errors="replace").strip()

    raise ValueError(f"Файл control не найден внутри {control_archive_name}")

def main():
    deb_files = sorted(glob.glob(os.path.join(DEBS_DIR, "*.deb")))
    if not deb_files:
        print("В папке debs/ нет ни одного .deb файла!")
        return

    packages_entries = []

    for deb_path in deb_files:
        deb_filename = os.path.basename(deb_path)
        rel_path = f"debs/{deb_filename}"
        
        with open(deb_path, "rb") as f:
            deb_bytes = f.read()

        size = len(deb_bytes)
        md5 = get_hash(deb_bytes, "md5")
        sha1 = get_hash(deb_bytes, "sha1")
        sha256 = get_hash(deb_bytes, "sha256")

        control_text = extract_control_from_deb(deb_path)

        entry = f"{control_text}\nFilename: {rel_path}\nSize: {size}\nMD5sum: {md5}\nSHA1: {sha1}\nSHA256: {sha256}\n"
        packages_entries.append(entry)
        print(f"Обработан: {deb_filename}")

    packages_content = "\n".join(packages_entries) + "\n"
    packages_bytes = packages_content.encode("utf-8")

    # Сохраняем Packages
    packages_file = os.path.join(REPO_DIR, "Packages")
    with open(packages_file, "wb") as f:
        f.write(packages_bytes)

    # Сохраняем Packages.xz
    packages_xz_file = os.path.join(REPO_DIR, "Packages.xz")
    with open(packages_xz_file, "wb") as f:
        f.write(lzma.compress(packages_bytes))

    # Сохраняем Packages.bz2
    packages_bz2_file = os.path.join(REPO_DIR, "Packages.bz2")
    with open(packages_bz2_file, "wb") as f:
        f.write(bz2.compress(packages_bytes))

    # Генерируем Release
    release_lines = [
        f"Origin: {REPO_NAME}",
        f"Label: {REPO_NAME}",
        f"Suite: stable",
        f"Version: 1.0",
        f"Codename: ios",
        f"Architectures: {ARCHITECTURES}",
        f"Components: main",
        f"Description: {REPO_DESCRIPTION}",
        "MD5Sum:",
    ]

    tracked_files = ["Packages", "Packages.xz", "Packages.bz2"]

    for tf in tracked_files:
        with open(os.path.join(REPO_DIR, tf), "rb") as f:
            data = f.read()
        release_lines.append(f" {get_hash(data, 'md5')} {len(data)} {tf}")

    release_lines.append("SHA1:")
    for tf in tracked_files:
        with open(os.path.join(REPO_DIR, tf), "rb") as f:
            data = f.read()
        release_lines.append(f" {get_hash(data, 'sha1')} {len(data)} {tf}")

    release_lines.append("SHA256:")
    for tf in tracked_files:
        with open(os.path.join(REPO_DIR, tf), "rb") as f:
            data = f.read()
        release_lines.append(f" {get_hash(data, 'sha256')} {len(data)} {tf}")

    release_content = "\n".join(release_lines) + "\n"
    with open(os.path.join(REPO_DIR, "Release"), "w", encoding="utf-8") as f:
        f.write(release_content)

    print("\nУспешно сформированы файлы репозитория:")
    print(" - Packages")
    print(" - Packages.xz")
    print(" - Packages.bz2")
    print(" - Release")

if __name__ == "__main__":
    main()
