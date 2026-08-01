"""Extended analysis operations."""

from .correlations import CorrelationAnalysis
from .expression import SafeExprEvaluator, strip_outer_parens, translate_leaf_expr
from .fitting import MODEL_REGISTRY, MODEL_REGISTRY_2D, fit_histogram, fit_histogram_2d
from .histograms import HistogramOperations
from .kinematics import KinematicsOperations
from .operations import AnalysisOperations
from .plotting import generate_plot

__all__ = [
    "MODEL_REGISTRY",
    "MODEL_REGISTRY_2D",
    "AnalysisOperations",
    "CorrelationAnalysis",
    "HistogramOperations",
    "KinematicsOperations",
    "SafeExprEvaluator",
    "fit_histogram",
    "fit_histogram_2d",
    "generate_plot",
    "strip_outer_parens",
    "translate_leaf_expr",
]
