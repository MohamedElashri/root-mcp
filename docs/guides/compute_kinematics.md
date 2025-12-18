# Kinematic Computation Tool

## Overview

The `compute_kinematics` tool computes derived kinematic quantities from particle four-momenta and angular coordinates. This is essential for physics analyses including Dalitz plots, angular correlations, mass distributions, and more.

## Supported Calculations

### 1. Invariant Mass
Computes the invariant mass: $m = \sqrt{E^2 - p_x^2 - p_y^2 - p_z^2}$

```json
{
  "name": "m_Kpi",
  "type": "invariant_mass",
  "particles": ["K", "pi_1"],
  "components": ["PX", "PY", "PZ", "PE"]
}
```

### 2. Invariant Mass Squared
Computes $m^2 = E^2 - p_x^2 - p_y^2 - p_z^2$ (useful for Dalitz plots)

```json
{
  "name": "m12_squared",
  "type": "invariant_mass_squared",
  "particles": ["p1", "p2"],
  "components": ["PX", "PY", "PZ", "PE"]
}
```

### 3. Transverse Mass
Computes $m_T = \sqrt{E^2 - p_x^2 - p_y^2}$ (useful for W/Z analyses)

```json
{
  "name": "mt_W",
  "type": "transverse_mass",
  "particles": ["lep", "nu"],
  "components": ["PX", "PY", "PZ", "E"]
}
```

### 4. Delta R
Computes $\Delta R = \sqrt{\Delta\eta^2 + \Delta\phi^2}$ between two particles

```json
{
  "name": "delta_r_jets",
  "type": "delta_r",
  "particles": ["jet1", "jet2"],
  "eta_suffix": "ETA",
  "phi_suffix": "PHI"
}
```

### 5. Delta Phi
Computes $\Delta\phi$ between two particles, wrapped to $[-\pi, \pi]$

```json
{
  "name": "delta_phi_12",
  "type": "delta_phi",
  "particles": ["mu1", "mu2"],
  "phi_suffix": "PHI"
}
```

## Tool Schema

```json
{
  "name": "compute_kinematics",
  "parameters": {
    "path": "string (required) - File path",
    "tree": "string (required) - Tree name",
    "computations": "array (required) - List of computations",
    "selection": "string (optional) - Cut expression",
    "limit": "integer (optional) - Max entries to process"
  }
}
```

### Computation Object Schema

```json
{
  "name": "string (required) - Output variable name",
  "type": "string (required) - One of: invariant_mass, invariant_mass_squared, transverse_mass, delta_r, delta_phi",
  "particles": "array of strings (required) - Particle prefixes",
  "components": "array of strings (optional) - Component suffixes, default: ['PX', 'PY', 'PZ', 'PE']",
  "eta_suffix": "string (optional) - Eta suffix for delta_r, default: 'ETA'",
  "phi_suffix": "string (optional) - Phi suffix for delta_r/delta_phi, default: 'PHI'"
}
```

## Usage Examples

### Example 1: Dalitz Plot for D⁰ → K⁻π⁺π⁺

```python
{
  "path": "D0_decay.root",
  "tree": "DecayTree",
  "computations": [
    {
      "name": "m_Kpi_squared",
      "type": "invariant_mass_squared",
      "particles": ["K", "pi_plus_1"]
    },
    {
      "name": "m_pipi_squared",
      "type": "invariant_mass_squared",
      "particles": ["pi_plus_1", "pi_plus_2"]
    }
  ],
  "selection": "K_PT > 500",
  "limit": 100000
}
```

**Workflow:**
1. Use `compute_kinematics` to calculate m²₁₂ and m²₂₃
2. Export results or use directly for analysis
3. Create 2D histogram/Dalitz plot with plotting tools

### Example 2: Dimuon Mass and Angular Separation

```python
{
  "path": "dimuon_data.root",
  "tree": "Events",
  "computations": [
    {
      "name": "m_mumu",
      "type": "invariant_mass",
      "particles": ["mu_plus", "mu_minus"],
      "components": ["PX", "PY", "PZ", "E"]
    },
    {
      "name": "delta_r_mumu",
      "type": "delta_r",
      "particles": ["mu_plus", "mu_minus"]
    }
  ],
  "selection": "mu_plus_PT > 20 && mu_minus_PT > 20"
}
```

### Example 3: W Boson Transverse Mass

```python
{
  "path": "W_events.root",
  "tree": "Events",
  "computations": [
    {
      "name": "mt_W",
      "type": "transverse_mass",
      "particles": ["lepton", "MET"]
    }
  ],
  "selection": "lepton_PT > 25 && MET_PT > 25"
}
```

### Example 4: Multiple Combinations

```python
{
  "path": "multibody.root",
  "tree": "DecayTree",
  "computations": [
    {"name": "m12", "type": "invariant_mass", "particles": ["p1", "p2"]},
    {"name": "m13", "type": "invariant_mass", "particles": ["p1", "p3"]},
    {"name": "m23", "type": "invariant_mass", "particles": ["p2", "p3"]},
    {"name": "m123", "type": "invariant_mass", "particles": ["p1", "p2", "p3"]},
    {"name": "delta_r_12", "type": "delta_r", "particles": ["p1", "p2"]},
    {"name": "delta_r_13", "type": "delta_r", "particles": ["p1", "p3"]}
  ]
}
```

## Branch Naming Convention

The tool expects branches to follow this naming pattern:
- Four-momentum: `{particle}_{component}` (e.g., `K_PX`, `K_PY`, `K_PZ`, `K_PE`)
- Angles: `{particle}_{angle}` (e.g., `mu_ETA`, `mu_PHI`)

You can customize suffixes using the `components`, `eta_suffix`, and `phi_suffix` parameters.

## Output Format

```json
{
  "data": {
    "m_Kpi_squared": [1.234, 2.345, ...],
    "m_pipi_squared": [0.987, 1.876, ...],
    ...
  },
  "metadata": {
    "operation": "compute_kinematics",
    "tree": "DecayTree",
    "entries_processed": 50000,
    "computations": [
      {"name": "m_Kpi_squared", "type": "invariant_mass_squared"},
      ...
    ],
    "selection": "K_PT > 500"
  },
  "suggestions": [
    "Computed 2 kinematic quantities: m_Kpi_squared, m_pipi_squared",
    "Processed 50,000 entries",
    "Use compute_histogram() to visualize mass distributions or compute_histogram_2d() for Dalitz plots"
  ]
}
```

## Physics Applications

### Dalitz Plots
1. Compute invariant mass squared for particle pairs
2. Create 2D histogram with `compute_histogram_2d`
3. Analyze phase space distributions, resonances, and interference patterns

### Resonance Studies
1. Compute invariant masses of particle combinations
2. Create histograms to identify peaks (resonances)
3. Fit with appropriate models

### Angular Correlations
1. Compute ΔR, Δφ, Δη between particles
2. Study jet substructure, isolation, or particle separations
3. Apply angular cuts for analysis selections

### Missing Energy Analyses
1. Compute transverse masses for W/Z reconstruction
2. Handle events with neutrinos or other invisible particles

## Performance Notes

- The tool reads only the necessary branches
- Computations are vectorized using NumPy/Awkward arrays
- Use `selection` to reduce data before computation
- Use `limit` to process subsets for testing

## Error Handling

Common errors:
- **Branch not found**: Check branch names with `list_branches` tool
- **Invalid particle count**: delta_r and delta_phi require exactly 2 particles
- **Invalid components**: Need 4 components (px, py, pz, E) for mass calculations

## See Also

- [compute_histogram](tools.md#compute_histogram) - Create 1D mass distributions
- [compute_histogram_2d](tools.md#compute_histogram_2d) - Create Dalitz plots
- [export_branches](tools.md#export_branches) - Export computed values
- [defines parameter](guides/configuration.md#defines) - Alternative for simple expressions
