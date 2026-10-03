"""Dataset Adapters package for MoieRec."""

from .base import BaseDatasetAdapter, NormalizedDataset
from .csv_adapter import MovieLensCSVAdapter

__all__ = ["BaseDatasetAdapter", "NormalizedDataset", "MovieLensCSVAdapter"]
