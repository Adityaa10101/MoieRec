"""Common utility functions for the dataset-agnostic data pipeline."""

import hashlib
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import pandas as pd
import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "datasets.yaml"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def get_project_root() -> Path:
    """Return the absolute path to the project root directory."""
    return PROJECT_ROOT


def load_dataset_config(dataset_name: str, config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load and validate dataset configuration from datasets.yaml.
    
    Args:
        dataset_name: Name of the dataset (e.g. 'ml-25m', 'ml-latest-small')
        config_path: Optional custom path to datasets.yaml
        
    Returns:
        Dictionary containing configuration parameters for the specified dataset.
        
    Raises:
        FileNotFoundError: If configuration file does not exist.
        ValueError: If dataset_name is not configured.
    """
    path = config_path or CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"Dataset configuration file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    datasets = data.get("datasets", {})
    if dataset_name not in datasets:
        available = list(datasets.keys())
        raise ValueError(
            f"Dataset '{dataset_name}' not found in configuration. "
            f"Available datasets: {available}"
        )

    cfg = datasets[dataset_name]
    # Ensure resolved absolute paths
    root = get_project_root()
    cfg["raw_dir_abs"] = root / cfg["raw_dir"]
    cfg["processed_dir_abs"] = root / cfg["processed_dir"]
    cfg["archive_path_abs"] = cfg["raw_dir_abs"] / cfg["archive_name"]
    cfg["extracted_dir_abs"] = cfg["raw_dir_abs"] / cfg["extracted_folder"]

    return cfg


def check_disk_space(required_bytes: int, target_dir: Path) -> Tuple[bool, int, int]:
    """Check whether sufficient disk space exists before downloading or processing.
    
    Args:
        required_bytes: Minimum bytes required (e.g. 3x archive size for zip + uncompressed + parquet).
        target_dir: Directory or drive path to check.
        
    Returns:
        Tuple of (has_space: bool, free_bytes: int, total_bytes: int)
    """
    check_path = target_dir
    while not check_path.exists() and check_path.parent != check_path:
        check_path = check_path.parent

    total, used, free = shutil.disk_usage(check_path)
    has_space = free >= required_bytes
    return has_space, free, total


def compute_file_md5(filepath: Path, chunk_size: int = 65536) -> str:
    """Compute MD5 checksum of a file in streaming chunks (memory efficient)."""
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_dataframe_content_hash(df: pd.DataFrame) -> str:
    """Compute a deterministic hash of dataframe content (values & column names).
    
    Independent of parquet metadata or file timestamps.
    Used for verifying determinism across pipeline runs.
    """
    hasher = hashlib.sha256()
    # Hash sorted column names
    col_str = ",".join(sorted([str(c) for c in df.columns]))
    hasher.update(col_str.encode("utf-8"))

    # Convert sorted representative values to string hash
    # To handle floating points consistently, format float to 4 decimal places
    records = []
    # Sort by primary key columns if present
    sort_cols = [c for c in ["user_id", "movie_id", "tag_id", "timestamp"] if c in df.columns]
    sorted_df = df.sort_values(by=sort_cols).reset_index(drop=True) if sort_cols else df

    # Sample or hash serialized CSV representation of sorted dataframe
    csv_bytes = sorted_df.to_csv(index=False).encode("utf-8")
    hasher.update(csv_bytes)
    return hasher.hexdigest()
