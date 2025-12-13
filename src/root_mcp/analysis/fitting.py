"""Fitting module for ROOT-MCP."""

from __future__ import annotations

import logging
import ast
from typing import Any, Callable, TypedDict, cast

import numpy as np
from scipy.optimize import curve_fit

from root_mcp.analysis.expression import SafeExprEvaluator, translate_leaf_expr

logger = logging.getLogger(__name__)


class ModelInfo(TypedDict):
    """Type definition for model registry entries."""

    func: Callable[..., np.ndarray]
    n_params: int
    param_names: list[str]


def gaussian(x: np.ndarray, amp: float, mu: float, sigma: float) -> np.ndarray:
    """Gaussian function."""
    return cast(np.ndarray, amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2))


def exponential(x: np.ndarray, amp: float, decay: float) -> np.ndarray:
    """Exponential function."""
    return cast(np.ndarray, amp * np.exp(-x / decay))


def polynomial(x: np.ndarray, *coeffs: float) -> np.ndarray:
    """Polynomial function."""
    return cast(np.ndarray, np.polyval(coeffs, x))


def crystal_ball(
    x: np.ndarray, amp: float, mu: float, sigma: float, alpha: float, n: float
) -> np.ndarray:
    """Crystal Ball function."""
    z = (x - mu) / sigma
    abs_alpha = abs(alpha)

    # Gaussian part
    # Use np.where to handle the piecewise definition
    mask = z > -abs_alpha

    # Power-law part
    A = (n / abs_alpha) ** n * np.exp(-0.5 * abs_alpha**2)
    B = n / abs_alpha - abs_alpha

    result = np.zeros_like(x)
    result[mask] = amp * np.exp(-0.5 * z[mask] ** 2)
    result[~mask] = amp * A * (B - z[~mask]) ** (-n)

    return result


# Map model names to functions and their parameter counts (excluding x)
MODEL_REGISTRY: dict[str, ModelInfo] = {
    "gaussian": {"func": gaussian, "n_params": 3, "param_names": ["amp", "mu", "sigma"]},
    "exponential": {"func": exponential, "n_params": 2, "param_names": ["amp", "decay"]},
    "polynomial": {
        "func": polynomial,
        "n_params": 2,
        "param_names": ["c1", "c0"],
    },  # Linear default
    "crystal_ball": {
        "func": crystal_ball,
        "n_params": 5,
        "param_names": ["amp", "mu", "sigma", "alpha", "n"],
    },
}


class CompositeModel:
    """Represents a sum of multiple models."""

    def __init__(self, components: list[str | dict[str, Any]]):
        self.funcs: list[Callable[..., np.ndarray]] = []
        self.param_ranges: list[tuple[int, int]] = []
        self.total_params = 0
        self.component_names: list[str] = []
        self.param_names: list[str] = []

        for comp in components:
            if isinstance(comp, str):
                name = comp
                prefix = f"{name}_{len(self.funcs)}_"
            else:
                name = comp["model"]
                prefix = comp.get("prefix", f"{name}_{len(self.funcs)}_")

            if name not in MODEL_REGISTRY:
                raise ValueError(f"Unknown model: {name}")

            reg = MODEL_REGISTRY[name]
            func = reg["func"]
            n_params = reg["n_params"]
            p_names = reg["param_names"]

            self.funcs.append(func)
            self.param_ranges.append((self.total_params, self.total_params + n_params))
            self.component_names.append(name)
            self.param_names.extend([f"{prefix}{p}" for p in p_names])
            self.total_params += n_params

    def __call__(self, x: np.ndarray, *params: float) -> np.ndarray:
        """Evaluate the composite model."""
        result = np.zeros_like(x, dtype=float)

        for func, (start, end) in zip(self.funcs, self.param_ranges):
            p = params[start:end]
            result += func(x, *p)

        return result


def _get_default_guess(model: str, x: np.ndarray, y: np.ndarray) -> list[float]:
    """Generate basic initial guess for a single model."""
    if model == "gaussian":
        mean = np.average(x, weights=y)
        sigma = np.sqrt(np.average((x - mean) ** 2, weights=y))
        amp = np.max(y)
        return [amp, mean, sigma]
    elif model == "exponential":
        return [np.max(y), (x[-1] - x[0]) / 2]
    elif model == "polynomial":
        return [0.0] * 2
    elif model == "crystal_ball":
        mean = np.average(x, weights=y)
        sigma = np.sqrt(np.average((x - mean) ** 2, weights=y))
        amp = np.max(y)
        return [amp, mean, sigma, 1.0, 2.0]
    return [1.0] * MODEL_REGISTRY[model]["n_params"]


class CustomModel:
    """Model defined by a string expression."""

    def __init__(self, expr: str, params: list[str]):
        """
        Initialize custom model.

        Args:
            expr: Mathematical expression string
            params: List of parameter names in order
        """
        self.expr = translate_leaf_expr(expr)
        self.params = params
        self.tree = ast.parse(self.expr, mode="eval")

    def __call__(self, x: np.ndarray, *args: float) -> np.ndarray:
        if len(args) != len(self.params):
            raise ValueError(f"Expected {len(self.params)} parameters, got {len(args)}")

        # Create context with x variable and parameters
        context: dict[str, Any] = {"x": x}
        for name, value in zip(self.params, args):
            context[name] = value

        return cast(np.ndarray, SafeExprEvaluator(context).visit(self.tree))


def fit_histogram(
    data: dict[str, Any],
    model: str | list[str | dict[str, Any]] | dict[str, Any],
    initial_guess: list[float] | None = None,
    bounds: list[list[float]] | None = None,
    fixed_parameters: dict[str | int, float] | None = None,
) -> dict[str, Any]:
    """
    Fit a model to histogram data.

    Args:
        data: Histogram data dictionary
        model: Model definition. Can be:
            - str: Name of built-in model (e.g., "gaussian")
            - list[str]: List of built-in models (e.g., ["gaussian", "exponential"])
            - list[dict]: List of models with config (e.g., [{"name": "gaussian", "prefix": "s_"}])
            - dict: Custom model definition (e.g. {"expr": "A*x + B", "params": ["A", "B"]})
        initial_guess: Initial parameter values
        bounds: List of [min, max] pairs for each parameter. Use [-np.inf, np.inf] for no bound.
        fixed_parameters: Dictionary of parameters to fix. Keys can be index (int) or name (str).

    Returns:
        Dictionary with fitted parameters, errors, and stats
    """
    # Extract x and y
    bin_edges = np.array(data["data"]["bin_edges"])
    y = np.array(data["data"]["bin_counts"])
    x = (bin_edges[:-1] + bin_edges[1:]) / 2

    # Errors
    if "bin_errors" in data["data"]:
        sigma = np.array(data["data"]["bin_errors"])
        # Handle zero errors to avoid div by zero in chi2
        sigma[sigma == 0] = 1.0
    else:
        sigma = np.sqrt(y)
        sigma[sigma == 0] = 1.0

    # Determine Model Function, Parameters, and Bounds
    fit_func: Callable
    param_names: list[str]

    # 1. Parse Model Input
    if isinstance(model, dict) and "expr" in model:
        # Custom String Model
        expr = model["expr"]
        params = model.get("params", [])
        if not params:
            # Try to auto-detect if not provided, but explicit is safer
            raise ValueError("Custom model must specify 'params' list")

        fit_instance = CustomModel(expr, params)
        fit_func = fit_instance
        param_names = params

    elif isinstance(model, str):
        # Single built-in model
        if model not in MODEL_REGISTRY:
            raise ValueError(f"Unknown model: {model}. Available: {list(MODEL_REGISTRY.keys())}")
        fit_func = MODEL_REGISTRY[model]["func"]
        param_names = MODEL_REGISTRY[model]["param_names"]

    elif isinstance(model, list):
        # Composite Model logic (as before)
        comp_model = CompositeModel(model)
        fit_func = comp_model
        param_names = comp_model.param_names
    else:
        raise ValueError("Invalid model format")

    num_params = len(param_names)

    # Validation
    # 2. Handle Fixed Parameters
    # We create a wrapper function that injects fixed values
    # and only exposes free parameters to curve_fit

    fixed_indices = {}  # index -> value
    if fixed_parameters:
        for key, val in fixed_parameters.items():
            idx = -1
            if isinstance(key, int):
                idx = key
            elif isinstance(key, str):
                try:
                    idx = param_names.index(key)
                except ValueError:
                    logger.warning(
                        f"Fixed parameter '{key}' not found in model parameters: {param_names}"
                    )
                    continue

            if 0 <= idx < num_params:
                fixed_indices[idx] = float(val)

    free_indices = [i for i in range(num_params) if i not in fixed_indices]

    if not free_indices:
        raise ValueError("All parameters are fixed! Nothing to fit.")

    # Create wrapper
    def wrapped_fit_func(x_data: np.ndarray, *free_params: float) -> np.ndarray:
        full_params = [0.0] * num_params

        # Fill free
        for i, val in enumerate(free_params):
            full_params[free_indices[i]] = val

        # Fill fixed
        for idx, val in fixed_indices.items():
            full_params[idx] = val

        return fit_func(x_data, *full_params)

    # 3. Prepare Initial Guess for Free Params
    if initial_guess is None:
        # Default fallback
        full_p0: list[float] = [1.0] * num_params

        # If single built-in, try its guesser
        if isinstance(model, str) and model in MODEL_REGISTRY:
            full_p0 = _get_default_guess(model, x, y)
        elif isinstance(model, list) and all(isinstance(m, str) for m in model) and len(model) == 1:
            # Single model in list
            full_p0 = _get_default_guess(cast(str, model[0]), x, y)

        # For others (custom, composite), calculating a good guess is hard without more info
    else:
        if len(initial_guess) != num_params:
            raise ValueError(
                f"Initial guess length {len(initial_guess)} != num params {num_params}"
            )
        full_p0 = initial_guess

    p0_free = [full_p0[i] for i in free_indices]

    # 4. Prepare Bounds for Free Params
    bounds_free_min: list[float] = []
    bounds_free_max: list[float] = []

    fit_bounds: tuple[list[float], list[float]] | tuple[float, float]

    if bounds:
        # bounds is list of [min, max] for ALL params (or None)
        if len(bounds) != num_params:
            raise ValueError(f"Bounds length {len(bounds)} != num params {num_params}")

        for i in free_indices:
            mn, mx = bounds[i]
            bounds_free_min.append(mn if mn is not None else -np.inf)
            bounds_free_max.append(mx if mx is not None else np.inf)

        fit_bounds = (bounds_free_min, bounds_free_max)
    else:
        fit_bounds = (-np.inf, np.inf)

    # 5. Perform Fit
    try:
        popt_free, pcov_free = curve_fit(
            wrapped_fit_func,
            x,
            y,
            p0=p0_free,
            sigma=sigma,
            absolute_sigma=True,
            bounds=fit_bounds,
            maxfev=10000,
        )
    except Exception as e:
        raise RuntimeError(f"Fit failed: {e}")

    # 6. Reconstruct Full Parameters and Covariance
    popt_full = [0.0] * num_params
    pcov_full = np.zeros((num_params, num_params))

    # Fill free
    for i, free_idx in enumerate(free_indices):
        popt_full[free_idx] = popt_free[i]
        for j, free_jdx in enumerate(free_indices):
            pcov_full[free_idx, free_jdx] = pcov_free[i, j]

    # Fill fixed
    for idx, val in fixed_indices.items():
        popt_full[idx] = val
        # Errors are 0 for fixed params

    # Calculate statistics
    y_fit = fit_func(x, *popt_full)
    chi2 = np.sum(((y - y_fit) / sigma) ** 2)
    ndof = len(x) - len(free_indices)

    return {
        "parameters": popt_full,
        "parameter_names": param_names,
        "errors": np.sqrt(np.diag(pcov_full)).tolist(),
        "chi2": chi2,
        "ndof": ndof,
        "fitted_values": y_fit.tolist(),
        "model": str(model),
        "fixed_parameters": list(fixed_indices.keys()),
    }
