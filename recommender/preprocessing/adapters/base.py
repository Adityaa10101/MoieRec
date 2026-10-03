"""Base Dataset Adapter Interface for MoieRec.

All dataset adapters must implement this interface to produce uniform, normalized
in-memory tables. Downstream modules (filtering, statistics, splitting, feature extraction)
interact strictly with NormalizedDataset and remain completely agnostic to raw source formats.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd


@dataclass
class NormalizedDataset:
    """Container holding normalized tables conforming to standard schema."""
    dataset_name: str
    ratings: pd.DataFrame
    movies: pd.DataFrame
    tags: Optional[pd.DataFrame] = None
    links: Optional[pd.DataFrame] = None
    genome_scores: Optional[pd.DataFrame] = None
    genome_tags: Optional[pd.DataFrame] = None
    parsing_metadata: Optional[Dict[str, Any]] = None


class BaseDatasetAdapter(ABC):
    """Abstract base adapter for ingestion and normalization of recommendation datasets."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.dataset_name = config["name"]

    @abstractmethod
    def load_normalized(self, raw_data_dir: Path) -> NormalizedDataset:
        """Parse raw files and return standard normalized tables.
        
        Args:
            raw_data_dir: Path to directory containing raw files.
            
        Returns:
            NormalizedDataset with normalized DataFrames and parsing metadata.
        """
        pass
