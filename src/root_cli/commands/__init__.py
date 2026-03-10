"""Commands package for root-cli."""

from .file_ops import ls, inspect, branches, validate
from .data_access import read, stats, export, sample
from .analysis import histogram, histogram2d, fit, invariant_mass, correlation
from .plotting import plot1d, plot2d, hist_arithmetic

__all__ = [
    "ls",
    "inspect",
    "branches",
    "validate",
    "read",
    "stats",
    "export",
    "sample",
    "histogram",
    "histogram2d",
    "fit",
    "invariant_mass",
    "correlation",
    "plot1d",
    "plot2d",
    "hist_arithmetic",
]
