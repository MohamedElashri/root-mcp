"""Kinematics calculations for particle physics analysis."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import awkward as ak
import numpy as np

if TYPE_CHECKING:
    from root_mcp.config import Config
    from root_mcp.core.io.file_manager import FileManager

logger = logging.getLogger(__name__)


class KinematicsOperations:
    """
    Particle physics kinematics calculations.

    Provides:
    - Invariant mass calculations
    - Transverse momentum (pT)
    - Pseudorapidity (eta)
    - Azimuthal angle (phi)
    - Delta R separation
    - Lorentz transformations
    - Dalitz variables
    """

    def __init__(self, config: Config, file_manager: FileManager):
        """
        Initialize kinematics operations.

        Args:
            config: Server configuration
            file_manager: File manager instance
        """
        self.config = config
        self.file_manager = file_manager

    def compute_invariant_mass(
        self,
        path: str,
        tree_name: str,
        pt_branches: list[str],
        eta_branches: list[str],
        phi_branches: list[str],
        mass_branches: list[str] | None = None,
        selection: str | None = None,
    ) -> dict[str, Any]:
        """
        Compute invariant mass from 4-vectors.

        Args:
            path: File path
            tree_name: Tree name
            pt_branches: List of pT branches
            eta_branches: List of eta branches
            phi_branches: List of phi branches
            mass_branches: List of mass branches (optional, assumes massless if None)
            selection: Optional cut expression

        Returns:
            Dictionary with invariant mass array
        """
        tree = self.file_manager.get_tree(path, tree_name)

        # Read data
        branches_to_read = pt_branches + eta_branches + phi_branches
        if mass_branches:
            branches_to_read.extend(mass_branches)

        arrays = tree.arrays(
            filter_name=branches_to_read,
            cut=selection,
            library="ak",
        )

        # Extract components
        n_particles = len(pt_branches)

        # Build 4-vectors
        px_total = 0
        py_total = 0
        pz_total = 0
        e_total = 0

        for i in range(n_particles):
            pt = arrays[pt_branches[i]]
            eta = arrays[eta_branches[i]]
            phi = arrays[phi_branches[i]]

            # Get mass (default to 0 if not provided)
            if mass_branches and i < len(mass_branches):
                mass = arrays[mass_branches[i]]
            else:
                mass = ak.zeros_like(pt)

            # Convert to Cartesian
            px = pt * np.cos(phi)
            py = pt * np.sin(phi)
            pz = pt * np.sinh(eta)

            # Energy
            p_squared = px**2 + py**2 + pz**2
            e = np.sqrt(p_squared + mass**2)

            # Sum
            px_total += px
            py_total += py
            pz_total += pz
            e_total += e

        # Compute invariant mass
        m_squared = e_total**2 - (px_total**2 + py_total**2 + pz_total**2)

        # Handle numerical precision issues
        m_squared = ak.where(m_squared < 0, 0, m_squared)
        invariant_mass = np.sqrt(m_squared)

        return {
            "invariant_mass": ak.to_list(invariant_mass),
            "metadata": {
                "operation": "compute_invariant_mass",
                "n_particles": n_particles,
                "selection": selection,
            },
        }

    def compute_transverse_mass(
        self,
        path: str,
        tree_name: str,
        pt1: str,
        phi1: str,
        pt2: str,
        phi2: str,
        selection: str | None = None,
    ) -> dict[str, Any]:
        """
        Compute transverse mass (useful for W->lν analyses).

        Args:
            path: File path
            tree_name: Tree name
            pt1: First particle pT branch
            phi1: First particle phi branch
            pt2: Second particle pT branch (e.g., MET)
            phi2: Second particle phi branch
            selection: Optional cut expression

        Returns:
            Dictionary with transverse mass array
        """
        tree = self.file_manager.get_tree(path, tree_name)

        arrays = tree.arrays(
            filter_name=[pt1, phi1, pt2, phi2],
            cut=selection,
            library="ak",
        )

        pt_1 = arrays[pt1]
        phi_1 = arrays[phi1]
        pt_2 = arrays[pt2]
        phi_2 = arrays[phi2]

        # Compute delta phi
        dphi = phi_1 - phi_2
        # Wrap to [-pi, pi]
        dphi = np.arctan2(np.sin(dphi), np.cos(dphi))

        # Transverse mass formula
        mt_squared = 2 * pt_1 * pt_2 * (1 - np.cos(dphi))
        mt = np.sqrt(mt_squared)

        return {
            "transverse_mass": ak.to_list(mt),
            "metadata": {
                "operation": "compute_transverse_mass",
                "selection": selection,
            },
        }

    def compute_delta_r(
        self,
        path: str,
        tree_name: str,
        eta1: str,
        phi1: str,
        eta2: str,
        phi2: str,
        selection: str | None = None,
    ) -> dict[str, Any]:
        """
        Compute Delta R separation between two objects.

        Args:
            path: File path
            tree_name: Tree name
            eta1: First object eta branch
            phi1: First object phi branch
            eta2: Second object eta branch
            phi2: Second object phi branch
            selection: Optional cut expression

        Returns:
            Dictionary with Delta R array
        """
        tree = self.file_manager.get_tree(path, tree_name)

        arrays = tree.arrays(
            filter_name=[eta1, phi1, eta2, phi2],
            cut=selection,
            library="ak",
        )

        eta_1 = arrays[eta1]
        phi_1 = arrays[phi1]
        eta_2 = arrays[eta2]
        phi_2 = arrays[phi2]

        # Compute delta eta and delta phi
        deta = eta_1 - eta_2
        dphi = phi_1 - phi_2

        # Wrap dphi to [-pi, pi]
        dphi = np.arctan2(np.sin(dphi), np.cos(dphi))

        # Delta R
        delta_r = np.sqrt(deta**2 + dphi**2)

        return {
            "delta_r": ak.to_list(delta_r),
            "metadata": {
                "operation": "compute_delta_r",
                "selection": selection,
            },
        }

    def compute_dalitz_variables(
        self,
        path: str,
        tree_name: str,
        pt_branches: list[str],
        eta_branches: list[str],
        phi_branches: list[str],
        mass_branches: list[str],
        selection: str | None = None,
    ) -> dict[str, Any]:
        """
        Compute Dalitz plot variables for 3-body decay.

        Args:
            path: File path
            tree_name: Tree name
            pt_branches: List of 3 pT branches
            eta_branches: List of 3 eta branches
            phi_branches: List of 3 phi branches
            mass_branches: List of 3 mass branches
            selection: Optional cut expression

        Returns:
            Dictionary with m12_squared and m23_squared arrays
        """
        if len(pt_branches) != 3:
            raise ValueError("Dalitz variables require exactly 3 particles")

        tree = self.file_manager.get_tree(path, tree_name)

        # Read data
        branches_to_read = pt_branches + eta_branches + phi_branches + mass_branches
        arrays = tree.arrays(
            filter_name=branches_to_read,
            cut=selection,
            library="ak",
        )

        # Build 4-vectors for each particle
        four_vectors = []
        for i in range(3):
            pt = arrays[pt_branches[i]]
            eta = arrays[eta_branches[i]]
            phi = arrays[phi_branches[i]]
            mass = arrays[mass_branches[i]]

            px = pt * np.cos(phi)
            py = pt * np.sin(phi)
            pz = pt * np.sinh(eta)
            p_squared = px**2 + py**2 + pz**2
            e = np.sqrt(p_squared + mass**2)

            four_vectors.append({"px": px, "py": py, "pz": pz, "e": e})

        # Compute invariant masses
        def invariant_mass_squared(v1, v2):
            e_sum = v1["e"] + v2["e"]
            px_sum = v1["px"] + v2["px"]
            py_sum = v1["py"] + v2["py"]
            pz_sum = v1["pz"] + v2["pz"]
            return e_sum**2 - (px_sum**2 + py_sum**2 + pz_sum**2)

        m12_sq = invariant_mass_squared(four_vectors[0], four_vectors[1])
        m23_sq = invariant_mass_squared(four_vectors[1], four_vectors[2])
        m13_sq = invariant_mass_squared(four_vectors[0], four_vectors[2])

        return {
            "m12_squared": ak.to_list(m12_sq),
            "m23_squared": ak.to_list(m23_sq),
            "m13_squared": ak.to_list(m13_sq),
            "metadata": {
                "operation": "compute_dalitz_variables",
                "selection": selection,
            },
        }

    def compute_boost_to_cm(
        self,
        path: str,
        tree_name: str,
        pt_branches: list[str],
        eta_branches: list[str],
        phi_branches: list[str],
        mass_branches: list[str],
        selection: str | None = None,
    ) -> dict[str, Any]:
        """
        Boost particles to center-of-mass frame.

        Args:
            path: File path
            tree_name: Tree name
            pt_branches: List of pT branches
            eta_branches: List of eta branches
            phi_branches: List of phi branches
            mass_branches: List of mass branches
            selection: Optional cut expression

        Returns:
            Dictionary with boosted 4-vectors
        """
        tree = self.file_manager.get_tree(path, tree_name)

        branches_to_read = pt_branches + eta_branches + phi_branches + mass_branches
        arrays = tree.arrays(
            filter_name=branches_to_read,
            cut=selection,
            library="ak",
        )

        n_particles = len(pt_branches)

        # Compute total 4-momentum
        px_total = 0
        py_total = 0
        pz_total = 0
        e_total = 0

        particles = []
        for i in range(n_particles):
            pt = arrays[pt_branches[i]]
            eta = arrays[eta_branches[i]]
            phi = arrays[phi_branches[i]]
            mass = arrays[mass_branches[i]]

            px = pt * np.cos(phi)
            py = pt * np.sin(phi)
            pz = pt * np.sinh(eta)
            p_squared = px**2 + py**2 + pz**2
            e = np.sqrt(p_squared + mass**2)

            particles.append({"px": px, "py": py, "pz": pz, "e": e})

            px_total += px
            py_total += py
            pz_total += pz
            e_total += e

        # Compute boost parameters
        p_total_squared = px_total**2 + py_total**2 + pz_total**2
        p_total = np.sqrt(p_total_squared)

        # Avoid division by zero
        beta = ak.where(e_total > 0, p_total / e_total, 0)
        gamma = ak.where(beta < 1, 1 / np.sqrt(1 - beta**2), 1)

        # Unit vector in boost direction
        beta_x = ak.where(p_total > 0, px_total / p_total, 0)
        beta_y = ak.where(p_total > 0, py_total / p_total, 0)
        beta_z = ak.where(p_total > 0, pz_total / p_total, 0)

        # Boost each particle
        boosted_particles = []
        for particle in particles:
            # Parallel component
            p_parallel = particle["px"] * beta_x + particle["py"] * beta_y + particle["pz"] * beta_z

            # Boosted energy
            e_boosted = gamma * (particle["e"] - beta * p_parallel)

            # Boosted momentum
            factor = (gamma - 1) * p_parallel - gamma * beta * particle["e"]
            px_boosted = particle["px"] + factor * beta_x
            py_boosted = particle["py"] + factor * beta_y
            pz_boosted = particle["pz"] + factor * beta_z

            boosted_particles.append(
                {
                    "px": ak.to_list(px_boosted),
                    "py": ak.to_list(py_boosted),
                    "pz": ak.to_list(pz_boosted),
                    "e": ak.to_list(e_boosted),
                }
            )

        return {
            "boosted_particles": boosted_particles,
            "metadata": {
                "operation": "compute_boost_to_cm",
                "n_particles": n_particles,
                "selection": selection,
            },
        }
