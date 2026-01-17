"""Fitting module for ROOT-MCP."""

from __future__ import annotations

import logging
import ast
from typing import Any, Callable, TypedDict, cast

import numpy as np
from scipy.optimize import curve_fit

from root_mcp.extended.analysis.expression import SafeExprEvaluator, translate_leaf_expr

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
    "polynomial_2": {
        "func": polynomial,
        "n_params": 3,
        "param_names": ["c2", "c1", "c0"],
    },  # Quadratic
    "polynomial_3": {
        "func": polynomial,
        "n_params": 4,
        "param_names": ["c3", "c2", "c1", "c0"],
    },  # Cubic
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
    elif model.startswith("polynomial"):
        n_params = MODEL_REGISTRY[model]["n_params"]
        return [0.0] * n_params
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
    # Handle both formats:
    # 1. Full histogram result: {"data": {...}, "metadata": {...}}
    # 2. Just the data dict: {"bin_edges": [...], "bin_counts": [...]}
    if "data" in data and "bin_edges" not in data:
        hist_data = data["data"]
    else:
        hist_data = data

    # Extract x and y
    bin_edges = np.array(hist_data["bin_edges"])
    y = np.array(hist_data["bin_counts"])
    x = (bin_edges[:-1] + bin_edges[1:]) / 2

    # Errors
    if "bin_errors" in hist_data:
        sigma = np.array(hist_data["bin_errors"])
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
        # Check for dynamic polynomial (inferred from initial guess)
        if model == "polynomial" and initial_guess is not None:
            n = len(initial_guess)
            fit_func = MODEL_REGISTRY["polynomial"]["func"]
            # Create param names cN-1 ... c0
            param_names = [f"c{n - 1 - i}" for i in range(n)]

        # Single built-in model
        elif model in MODEL_REGISTRY:
            fit_func = MODEL_REGISTRY[model]["func"]
            param_names = MODEL_REGISTRY[model]["param_names"]

        # Try auto-detect custom formula
        else:
            try:
                # Attempt to extract parameters from expression
                import re

                expr = model
                # Use same reserved keywords as operations.py
                reserved = {
                    "sqrt",
                    "abs",
                    "log",
                    "exp",
                    "sin",
                    "cos",
                    "tan",
                    "arcsin",
                    "arccos",
                    "arctan",
                    "arctan2",
                    "sinh",
                    "cosh",
                    "tanh",
                    "min",
                    "max",
                    "where",
                    "sum",
                    "any",
                    "all",
                    "pi",
                    "e",
                }

                # Extract all identifiers
                tokens = re.findall(r"[A-Za-z_]\w*", expr)

                # Filter for parameters (exclude 'x' and reserved)
                params_seen = set()
                params = []
                for t in tokens:
                    if t != "x" and t not in reserved and t not in params_seen:
                        params.append(t)
                        params_seen.add(t)

                if not params:
                    # If no params found (e.g. "x**2"), technically valid with 0 params,
                    # but likely user error or simple func. Use CustomModel.
                    pass

                # Create custom model
                fit_instance = CustomModel(expr, params)
                fit_func = fit_instance
                param_names = params

            except Exception:
                # If parsing fails or logic fails, raise original error
                raise ValueError(
                    f"Unknown model: '{model}'. For custom formulas, use a dictionary "
                    f'(e.g., {{"expr": "a*x+b", "params": ["a", "b"]}}). '
                    f"Available built-ins: {list(MODEL_REGISTRY.keys())}"
                )

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


# 2D Fitting Functions
def gaussian_2d(
    xy: tuple[np.ndarray, np.ndarray],
    amp: float,
    mu_x: float,
    mu_y: float,
    sigma_x: float,
    sigma_y: float,
    rho: float = 0.0,
) -> np.ndarray:
    """
    2D Gaussian function with correlation.

    Args:
        xy: Tuple of (x, y) coordinate arrays
        amp: Amplitude
        mu_x: Mean in x
        mu_y: Mean in y
        sigma_x: Standard deviation in x
        sigma_y: Standard deviation in y
        rho: Correlation coefficient (-1 to 1)

    Returns:
        Function values at (x, y) points
    """
    x, y = xy
    dx = x - mu_x
    dy = y - mu_y

    # Exponent
    exponent = (
        -0.5
        / (1 - rho**2)
        * ((dx / sigma_x) ** 2 + (dy / sigma_y) ** 2 - 2 * rho * dx * dy / (sigma_x * sigma_y))
    )

    return amp * np.exp(exponent)


def polynomial_2d(
    xy: tuple[np.ndarray, np.ndarray],
    *coeffs: float,
) -> np.ndarray:
    """
    2D polynomial function.

    Args:
        xy: Tuple of (x, y) coordinate arrays
        coeffs: Polynomial coefficients [c00, c10, c01, c20, c11, c02, ...]

    Returns:
        Function values at (x, y) points
    """
    x, y = xy
    result = np.zeros_like(x)

    # Determine polynomial degree from number of coefficients
    # For degree d: (d+1)(d+2)/2 coefficients
    n_coeffs = len(coeffs)
    degree = int((-3 + np.sqrt(9 + 8 * (n_coeffs - 1))) / 2)

    idx = 0
    for d in range(degree + 1):
        for i in range(d + 1):
            j = d - i
            if idx < n_coeffs:
                result += coeffs[idx] * (x**i) * (y**j)
                idx += 1

    return result


MODEL_REGISTRY_2D: dict[str, ModelInfo] = {
    "gaussian_2d": {
        "func": gaussian_2d,
        "n_params": 6,
        "param_names": ["amp", "mu_x", "mu_y", "sigma_x", "sigma_y", "rho"],
    },
    "polynomial_2d": {
        "func": polynomial_2d,
        "n_params": 6,  # Quadratic default
        "param_names": ["c00", "c10", "c01", "c20", "c11", "c02"],
    },
}


def fit_histogram_2d(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    z_errors: np.ndarray | None = None,
    model: str = "gaussian_2d",
    initial_params: list[float] | None = None,
    fixed_params: dict[str, float] | None = None,
    bounds: tuple[list[float], list[float]] | None = None,
) -> dict[str, Any]:
    """
    Fit a 2D histogram with a model function.

    Args:
        x: X-coordinate array (flattened)
        y: Y-coordinate array (flattened)
        z: Z-values (bin contents, flattened)
        z_errors: Errors on z-values
        model: Model name from MODEL_REGISTRY_2D
        initial_params: Initial parameter guesses
        fixed_params: Dictionary of {param_name: value} for fixed parameters
        bounds: Tuple of (lower_bounds, upper_bounds)

    Returns:
        Dictionary with fit results
    """
    if model not in MODEL_REGISTRY_2D:
        raise ValueError(f"Unknown 2D model: {model}. Available: {list(MODEL_REGISTRY_2D.keys())}")

    model_info = MODEL_REGISTRY_2D[model]
    fit_func = model_info["func"]
    param_names = model_info["param_names"]
    num_params = model_info["n_params"]

    # Handle errors
    if z_errors is None:
        z_errors = np.sqrt(np.maximum(z, 1))  # Poisson errors

    # Avoid zero errors
    z_errors = np.maximum(z_errors, 1e-10)

    # Handle fixed parameters
    fixed_params = fixed_params or {}
    fixed_indices = {param_names.index(k): v for k, v in fixed_params.items()}
    free_indices = [i for i in range(num_params) if i not in fixed_indices]

    # Initial parameters
    if initial_params is None:
        # Auto-generate initial guesses
        if model == "gaussian_2d":
            initial_params = [
                np.max(z),  # amp
                np.mean(x),  # mu_x
                np.mean(y),  # mu_y
                np.std(x),  # sigma_x
                np.std(y),  # sigma_y
                0.0,  # rho
            ]
        else:
            initial_params = [1.0] * num_params

    # Create wrapper for fixed parameters
    def fit_func_wrapper(xy: tuple[np.ndarray, np.ndarray], *free_params: float) -> np.ndarray:
        full_params = [0.0] * num_params
        for i, free_idx in enumerate(free_indices):
            full_params[free_idx] = free_params[i]
        for idx, val in fixed_indices.items():
            full_params[idx] = val
        return fit_func(xy, *full_params)

    # Extract free initial parameters
    p0_free = [initial_params[i] for i in free_indices]

    # Handle bounds
    fit_bounds = (-np.inf, np.inf)
    if bounds is not None:
        lower_free = [bounds[0][i] for i in free_indices]
        upper_free = [bounds[1][i] for i in free_indices]
        fit_bounds = (lower_free, upper_free)

    # Perform fit
    try:
        popt_free, pcov_free = curve_fit(
            fit_func_wrapper,
            (x, y),
            z,
            p0=p0_free,
            sigma=z_errors,
            absolute_sigma=True,
            bounds=fit_bounds,
            maxfev=10000,
        )
    except Exception as e:
        raise RuntimeError(f"2D fit failed: {e}")

    # Reconstruct full parameters
    popt_full = [0.0] * num_params
    pcov_full = np.zeros((num_params, num_params))

    for i, free_idx in enumerate(free_indices):
        popt_full[free_idx] = popt_free[i]
        for j, free_jdx in enumerate(free_indices):
            pcov_full[free_idx, free_jdx] = pcov_free[i, j]

    for idx, val in fixed_indices.items():
        popt_full[idx] = val

    # Calculate statistics
    z_fit = fit_func((x, y), *popt_full)
    chi2 = np.sum(((z - z_fit) / z_errors) ** 2)
    ndof = len(z) - len(free_indices)

    return {
        "parameters": popt_full,
        "parameter_names": param_names,
        "errors": np.sqrt(np.diag(pcov_full)).tolist(),
        "chi2": float(chi2),
        "ndof": int(ndof),
        "fitted_values": z_fit.tolist(),
        "model": model,
        "fixed_parameters": list(fixed_indices.keys()),
    }
