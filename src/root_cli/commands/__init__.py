"""Commands package for root-cli."""

from .analysis import correlation, fit, histogram, histogram2d, invariant_mass
from .data_access import export, read, sample, stats
from .file_ops import branches, inspect, ls, validate
from .plotting import hist_arithmetic, plot1d, plot2d

__all__ = [
    "branches",
    "correlation",
    "export",
    "fit",
    "hist_arithmetic",
    "histogram",
    "histogram2d",
    "inspect",
    "invariant_mass",
    "ls",
    "plot1d",
    "plot2d",
    "read",
    "sample",
    "stats",
    "validate",
]
