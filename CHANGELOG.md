# Changelog

All notable changes to the Bullet Designer workbench will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Dynamic calculated tooltips for nose and tip inputs in both Task Panel and Ballistic Calculator
- Documentation updates for nose and tip validation limits and severity behavior
- Added BDLogo.svg logo file
- Documentation for the geometry-based G1 BC model and environment-dependent corrections

### Changed
- Clarified README feature descriptions for integrated hollow point and hollow point + tip workflows
- Expanded user manual with current nose geometry, wall-thickness, and material-category constraints
- Replaced static G1 BC form-factor constants with a geometry-derived model that includes Mach-regime, atmosphere, boat tail, and meplat corrections
- Restructured addon to **Addon Academy Modern** layout: `freecad/BulletDesigner/` with `init_gui.py`, `Documentation/USER_MANUAL.md`, `Resources/Icons`, `Resources/Media`, and `pyproject.toml`; `package.xml` workbench subdirectory points at `freecad/BulletDesigner`; Python imports use `freecad.BulletDesigner.*`

### Removed
- Deleted SMLogo.svg logo file
- Removed legacy root `Init.py` and former `bullet_designer/` package folder

## [1.0.0] - 2026-02-16

### Added
- Initial release of Bullet Designer workbench
- Parametric bullet creation with customizable dimensions
- Multiple bullet types: land-riding, flat-base, boat-tail designs
- Configurable driving bands (number, length, spacing)
- Three ogive types: tangent, secant, elliptical with customizable caliber ratios
- Ballistic Calculator with Miller stability formula
- G1 ballistic coefficient estimation
- Sectional density calculation
- Recommended twist rate calculation (Greenhill formula)
- Trajectory & Transonic Calculator with RK4 integration
- G7 ballistic coefficient conversion from G1
- Air density and speed of sound calculations
- G7 drag table with linear interpolation
- Spin drift calculation using Litz formula
- Transonic zone detection (Mach 1.1 entry, 0.9 exit)
- Material database with built-in materials (copper, lead, brass, gilding metal, steel, tungsten)
- Custom material density support
- Export to STL format for 3D printing
- Export to STEP format for CAD software
- Task panel with tabbed interface for parameter editing
- Live preview mode for real-time geometry updates
- Preferences page for customizable defaults
- Comprehensive user manual ([Documentation/USER_MANUAL.md](Documentation/USER_MANUAL.md))
- Example bullet designs (.FCStd files)
- PDF technical drawings for example bullets

### Changed
- N/A (initial release)

### Deprecated
- N/A (initial release)

### Removed
- N/A (initial release)

### Fixed
- N/A (initial release)

### Security
- N/A (initial release)
