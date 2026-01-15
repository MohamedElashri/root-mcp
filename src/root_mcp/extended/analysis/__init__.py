"""Extended analysis operations."""

from .expression import SafeExprEvaluator, translate_leaf_expr, strip_outer_parens
from .fitting import fit_histogram, fit_histogram_2d, MODEL_REGISTRY, MODEL_REGISTRY_2D
from .operations import AnalysisOperations
from .plotting import generate_plot
from .histograms import HistogramOperations
from .kinematics import KinematicsOperations
from .correlations import CorrelationAnalysis

__all__ = [
    "SafeExprEvaluator",
    "translate_leaf_expr",
    "strip_outer_parens",
    "fit_histogram",
    "fit_histogram_2d",
    "MODEL_REGISTRY",
    "MODEL_REGISTRY_2D",
    "AnalysisOperations",
    "generate_plot",
    "HistogramOperations",
    "KinematicsOperations",
    "CorrelationAnalysis",
]
