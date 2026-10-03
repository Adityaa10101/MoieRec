"""Download and verify official GroupLens MovieLens datasets.

Ensures safe, idempotent downloads:
1. Validates disk space prior to fetching.
2. Skips download if archive already exists and matches expected checksum.
3. Downloads directly from official GroupLens mirrors with SSL certificates.
4. Verifies MD5 checksum against published GroupLens metadata.
5. Extracts files into raw directory (data/raw/<dataset-name>/).
"""

import argparse
import os
import shutil
import ssl
import sys
import urllib.request
import zipfile
from pathlib import Path

try:
    import certifi
    HAS_CERTIFI = True
except ImportError:
    HAS_CERTIFI = False

from recommender.preprocessing.utils import (
    check_disk_space,
    compute_file_md5,
    get_project_root,
    load_dataset_config,
)


def get_ssl_context() -> ssl.SSLContext:
    """Create a verified SSL context using certifi CA bundle if available."""
    if HAS_CERTIFI:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()


def download_file(url: str, dest_path: Path, expected_bytes: int = 0) -> None:
    """Download a file with streaming chunks and progress display."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(".tmp")

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MoieRec/1.0"}
    req = urllib.request.Request(url, headers=headers)
    ctx = get_ssl_context()

    print(f"Downloading from {url} ...")
    try:
        with urllib.request.urlopen(req, context=ctx) as response, open(temp_path, "wb") as out_file:
            total_size = int(response.headers.get("Content-Length", expected_bytes or 0))
            downloaded = 0
            chunk_size = 1024 * 1024  # 1MB chunks

            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    pct = (downloaded / total_size) * 100
                    mb_down = downloaded / (1024 * 1024)
                    mb_tot = total_size / (1024 * 1024)
                    sys.stdout.write(f"\r  -> Progress: {mb_down:.1f} MB / {mb_tot:.1f} MB ({pct:.1f}%)")
                    sys.stdout.flush()
                else:
                    mb_down = downloaded / (1024 * 1024)
                    sys.stdout.write(f"\r  -> Downloaded: {mb_down:.1f} MB")
                    sys.stdout.flush()
        print()
        temp_path.replace(dest_path)
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise RuntimeError(f"Download failed from {url}: {e}") from e


def download_and_extract(dataset_name: str, force: bool = False) -> Path:
    """Download, verify, and unpack specified dataset archive."""
    cfg = load_dataset_config(dataset_name)
    raw_dir = cfg["raw_dir_abs"]
    archive_path = cfg["archive_path_abs"]
    url = cfg["url"]
    expected_md5 = cfg.get("expected_md5")
    expected_size = cfg.get("expected_size_bytes", 0)

    # 1. Check disk space (require at least 4x archive size for download + extraction + parquet)
    required_space = max(expected_size * 4, 100 * 1024 * 1024)
    has_space, free_bytes, total_bytes = check_disk_space(required_space, raw_dir)
    print(f"Disk space check: {free_bytes / (1024**3):.2f} GB free on target drive.")
    if not has_space:
        raise OSError(
            f"Insufficient disk space to download and extract {dataset_name}. "
            f"Required: {required_space / (1024**2):.1f} MB, Free: {free_bytes / (1024**2):.1f} MB."
        )

    # 2. Check if archive already downloaded and verified
    need_download = force or not archive_path.exists()
    if not need_download and archive_path.exists():
        print(f"Archive already present at: {archive_path}")
        if expected_md5:
            print("Verifying existing archive checksum...")
            current_md5 = compute_file_md5(archive_path)
            if current_md5.lower() == expected_md5.lower():
                print(f"Archive MD5 verified: {current_md5}")
            else:
                print(f"MD5 mismatch (found {current_md5}, expected {expected_md5}). Re-downloading...")
                need_download = True

    if need_download:
        download_file(url, archive_path, expected_size)
        # Verify MD5
        if expected_md5:
            print("Verifying downloaded archive MD5 checksum...")
            downloaded_md5 = compute_file_md5(archive_path)
            if downloaded_md5.lower() != expected_md5.lower():
                archive_path.unlink()
                raise ValueError(
                    f"Checksum verification failed for {archive_path.name}!\n"
                    f"Expected MD5: {expected_md5}\n"
                    f"Calculated MD5: {downloaded_md5}"
                )
            print(f"Checksum verification PASSED: {downloaded_md5}")

    # 3. Extract archive into raw_dir
    print(f"Extracting archive to: {raw_dir} ...")
    with zipfile.ZipFile(archive_path, "r") as zip_ref:
        zip_ref.extractall(raw_dir)

    extracted_dir = cfg["extracted_dir_abs"]
    print(f"Dataset successfully unpacked to: {extracted_dir}")
    return extracted_dir


def main():
    parser = argparse.ArgumentParser(description="Download and verify GroupLens MovieLens datasets.")
    parser.add_argument(
        "--dataset",
        type=str,
        default="ml-25m",
        choices=["ml-25m", "ml-latest-small"],
        help="Dataset name configured in datasets.yaml (default: ml-25m)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if archive already exists",
    )
    args = parser.parse_args()

    print(f"=== Downloading Dataset: {args.dataset} ===")
    try:
        download_and_extract(args.dataset, force=args.force)
        print(f"Download and extraction completed successfully for {args.dataset}.\n")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
