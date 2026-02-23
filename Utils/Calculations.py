"""
Ballistic calculations and formulas for bullet design.

This module provides functions for calculating ballistic properties
including stability, ballistic coefficient, sectional density, and twist rates.
"""

import math
from typing import Optional, Tuple, Dict

from Utils.MaterialDatabase import get_material_database


def calculate_sectional_density(diameter_mm: float, weight_grains: float) -> float:
    """
    Calculate sectional density (SD) of a bullet.

    Sectional density = Weight (lbs) / Diameter^2 (inches)

    Args:
        diameter_mm: Bullet diameter in millimeters
        weight_grains: Bullet weight in grains

    Returns:
        Sectional density (dimensionless)
    """
    if diameter_mm <= 0 or weight_grains <= 0:
        return 0.0

    # Convert to inches and pounds
    diameter_inches = diameter_mm / 25.4
    weight_lbs = weight_grains / 7000.0

    sd = weight_lbs / (diameter_inches**2)
    return sd


def calculate_ballistic_coefficient_g1(
    diameter_mm: float,
    weight_grains: float,
    length_mm: float,
    ogive_type: str = "Tangent",
    nose_type: str = "solid",
    hp_diameter_mm: float = 0.0,
    effective_diameter_mm: Optional[float] = None,
    velocity_mps: Optional[float] = None,
    temperature_c: float = 15.0,
    pressure_hpa: float = 1013.25,
    ogive_caliber_ratio: Optional[float] = None,
    boat_tail_angle_deg: float = 0.0,
    boat_tail_length_mm: float = 0.0,
    meplat_diameter_mm: float = 0.0,
) -> float:
    """
    Estimate G1 ballistic coefficient using empirical formulas.

    This is a simplified estimation. Real BC depends on many factors
    including velocity, shape, and atmospheric conditions.

    Args:
        diameter_mm: Bullet diameter in millimeters
        weight_grains: Bullet weight in grains
        length_mm: Bullet length in millimeters
        ogive_type: Type of ogive ("Tangent", "Secant", "Elliptical")

    Returns:
        Estimated G1 ballistic coefficient
    """
    if diameter_mm <= 0 or weight_grains <= 0 or length_mm <= 0:
        return 0.0

    def _clamp(value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))

    # Convert to inches
    d_effective_mm = effective_diameter_mm if effective_diameter_mm else diameter_mm
    d_effective_mm = max(d_effective_mm, 0.001)

    # Calculate sectional density
    sd = calculate_sectional_density(diameter_mm, weight_grains)

    # Geometry-derived form factor referenced to a Mayewski-like standard projectile.
    # i < 1.0 generally improves BC, i > 1.0 worsens BC.
    form_factor = 1.0

    if ogive_caliber_ratio and ogive_caliber_ratio > 0:
        ogive_length_mm = (ogive_caliber_ratio * d_effective_mm) / 2.0
        ogive_radius_mm = calculate_ogive_radius(
            ogive_caliber_ratio, d_effective_mm, ogive_type
        )
    else:
        # Fallback estimate if detailed ogive ratio is not provided.
        ogive_length_mm = max(0.0, length_mm * 0.45)
        ogive_radius_mm = ogive_length_mm

    nose_length_ratio = ogive_length_mm / d_effective_mm
    ogive_radius_calibers = (
        ogive_radius_mm / d_effective_mm if ogive_radius_mm > 0 else nose_length_ratio
    )

    # Compare to G1/Mayewski standard-like reference nose fineness.
    mayewski_ref_nose_fineness = 3.28
    mayewski_delta = (
        (nose_length_ratio - mayewski_ref_nose_fineness) / mayewski_ref_nose_fineness
    )
    form_factor = form_factor * (
        1.0 - 0.04 * _clamp(mayewski_delta, -1.0, 1.0)
    )

    # Additional geometry sensitivity from nose ratio and ogive radius.
    nose_term = 1.0 - 0.045 * _clamp((nose_length_ratio - 3.0) / 4.0, -1.0, 1.0)
    radius_term = 1.0 - 0.03 * _clamp((ogive_radius_calibers - 6.0) / 8.0, -1.0, 1.0)
    form_factor = form_factor * nose_term * radius_term

    # Keep mild ogive-type influence while letting geometry dominate.
    ogive_type_factor = {"Tangent": 1.00, "Secant": 0.985, "Elliptical": 0.975}
    form_factor = form_factor * ogive_type_factor.get(ogive_type, 1.00)

    # Boat-tail correction typically reduces form factor by ~3-8%.
    if boat_tail_angle_deg > 0.0 and boat_tail_length_mm > 0.0 and length_mm > 0.0:
        angle_term = _clamp((boat_tail_angle_deg - 5.0) / 7.0, 0.0, 1.0)
        length_ratio = boat_tail_length_mm / length_mm
        length_term = _clamp(length_ratio / 0.20, 0.0, 1.0)
        bt_reduction = 0.03 + 0.05 * ((0.6 * angle_term) + (0.4 * length_term))
        form_factor = form_factor * (1.0 - bt_reduction)

    # Meplat penalty: larger meplat increases drag.
    if meplat_diameter_mm > 0.0:
        meplat_ratio = meplat_diameter_mm / d_effective_mm
        form_factor = form_factor * (1.0 + 0.22 * (meplat_ratio**1.4))

    # Hollow point form factor penalty (hp only)
    if nose_type == "hp" and hp_diameter_mm > 0 and d_effective_mm > 0:
        hp_ratio = hp_diameter_mm / d_effective_mm
        form_factor = form_factor * (1.0 + 0.15 * (hp_ratio**2))

    # Mach-regime correction since G1 BC varies with velocity.
    mach = None
    if velocity_mps is not None and velocity_mps > 0.0:
        temp_k = temperature_c + 273.15
        speed_of_sound = 331.3 * math.sqrt(max(temp_k, 1.0) / 273.15)
        if speed_of_sound > 0.0:
            mach = velocity_mps / speed_of_sound

    if mach is not None:
        if mach < 1.2:
            mach_factor = 1.02 + 0.03 * _clamp((1.2 - mach) / 1.2, 0.0, 1.0)
        elif mach <= 2.0:
            blend = (mach - 1.2) / 0.8
            mach_factor = 1.10 - 0.06 * _clamp(blend, 0.0, 1.0)
        else:
            mach_factor = 1.03
        form_factor = form_factor * mach_factor

    form_factor = max(0.40, min(form_factor, 1.80))

    # BC = SD / i
    bc = sd / form_factor

    # Atmospheric density scaling relative to ICAO standard conditions.
    # Higher actual density => lower effective BC in flight, and vice versa.
    temp_k = temperature_c + 273.15
    rho_actual = (pressure_hpa * 100.0) / (287.05 * max(temp_k, 1.0))
    rho_std = (1013.25 * 100.0) / (287.05 * (15.0 + 273.15))
    density_ratio = rho_actual / rho_std if rho_std > 0 else 1.0
    bc = bc * (1.0 / _clamp(density_ratio, 0.6, 1.4))

    return round(bc, 3)


def calculate_recommended_twist_rate(
    diameter_mm: float,
    length_mm: float,
    weight_grains: float,
    velocity_mps: float = 853.0,
    effective_diameter_mm: Optional[float] = None,
    material_density_g_per_cm3: Optional[float] = None,
) -> Tuple[float, str]:
    """
    Calculate recommended barrel twist rate using Greenhill formula or Miller-based formula.

    For monolithic copper/brass bullets, uses Miller-based required twist calculation:
    T_required = d_effective × √[(30 × m) / (1.8 × d_effective³ × l × (1 + l²))] × (2800/V)^(1/6)

    For lead-core bullets, uses Greenhill formula:
    T = 150 * D^2 / L (or with velocity correction for V > 2800 fps)

    CRITICAL: Uses d_effective (band diameter), NOT nominal diameter.
    For land-riding bullets: d_effective = band diameter (typically 6.5-6.6 mm, NOT 6.7 mm)

    Args:
        diameter_mm: Bullet diameter in millimeters (nominal/groove diameter)
        length_mm: Bullet length in millimeters
        weight_grains: Bullet weight in grains
        velocity_mps: Muzzle velocity in meters per second (default 853 m/s = ~2800 fps)
        effective_diameter_mm: Effective diameter at bearing bands for land-riding bullets.
            For land-riding bullets: typically 6.5-6.6 mm (NOT 6.7 mm nominal).
            If None, uses diameter_mm.
        material_density_g_per_cm3: Material density in g/cm³ used to determine bullet type.

    Returns:
        Tuple of (twist_rate_inches, formatted_string)
        Example: (8.0, "1:8\"")
    """
    if diameter_mm <= 0 or length_mm <= 0:
        return (0.0, "N/A")

    # Determine if monolithic copper/brass bullet
    is_monolithic_copper_brass = False
    if material_density_g_per_cm3 is not None:
        if 7.0 <= material_density_g_per_cm3 <= 9.5:
            is_monolithic_copper_brass = True

    # Use effective diameter (bearing band diameter) if provided
    # CRITICAL: For land-riding bullets, d_effective is band diameter.
    # Typical value is 6.5-6.6 mm, not nominal 6.7 mm.
    d_effective_mm = (
        effective_diameter_mm if effective_diameter_mm is not None else diameter_mm
    )

    # Convert to inches (formula uses imperial units)
    d_effective_inches = d_effective_mm / 25.4
    length_inches = length_mm / 25.4

    # Convert velocity to fps
    velocity_fps = velocity_mps * 3.28084

    if is_monolithic_copper_brass:
        # Miller-based required twist for monolithic copper/brass bullets
        # T_required = d_effective × sqrt((30 × m)/(1.8 × d_effective³ × l × (1 + l²)))
        #              × (2800/V)^(1/6)
        length_calibers = length_inches / d_effective_inches

        # Calculate numerator: 30 × m
        numerator = 30.0 * weight_grains

        # Calculate denominator: 1.8 × d_effective³ × l × (1 + l²)
        denominator = 1.8 * (d_effective_inches**3) * length_calibers
        denominator = denominator * (1.0 + length_calibers**2)

        # Calculate square root term
        sqrt_term = math.sqrt(numerator / denominator) if denominator > 0 else 0.0

        # Calculate velocity correction: (2800/V)^(1/6)
        if velocity_fps > 0:
            velocity_correction = math.pow(2800.0 / velocity_fps, 1.0 / 6.0)
        else:
            velocity_correction = 1.0

        # Final twist rate: T_required = d_effective × sqrt_term × velocity_correction
        twist_rate = d_effective_inches * sqrt_term * velocity_correction
    else:
        # Greenhill formula for lead-core bullets
        if velocity_fps <= 2800:
            twist_rate = 150.0 * (d_effective_inches**2) / length_inches
        else:
            velocity_factor = math.sqrt(velocity_fps / 2800.0)
            twist_rate = (
                150.0 * (d_effective_inches**2) / length_inches * velocity_factor
            )

    # Round to nearest reasonable value (typically 7, 8, 9, 10, 12, 14)
    twist_rate = round(twist_rate)

    # Format as "1:X\""
    formatted = f'1:{int(twist_rate)}"'

    return (twist_rate, formatted)


def calculate_stability_factor_miller(
    diameter_mm: float,
    length_mm: float,
    weight_grains: float,
    twist_rate_inches: float,
    velocity_mps: float = 853.0,
    temperature_c: float = 15.0,
    pressure_hpa: float = 1013.25,
    effective_diameter_mm: Optional[float] = None,
    material_density_g_per_cm3: Optional[float] = None,
    l_effective_calibers: Optional[float] = None,
    corrected_mass_grains: Optional[float] = None,
) -> Tuple[float, float]:
    """
    Calculate stability factor using Miller's formula.

    CORRECTED FORMULA (3 steps):

    Step 1: Basic calculation
    l = L / d_effective
    t = T / d_effective
    Sg = (30 × m) / (t² × d_effective³ × l × (1 + l²))

    Step 2: Velocity correction
    Sg_corrected = Sg × (V_fps / 2800)^(1/3)

    Step 3: Stability threshold
    Monolithic copper/brass: Sg_corrected ≥ 1.8
    Lead-core bullets: Sg_corrected ≥ 1.5

    WHERE:
    - m = bullet mass (grains)
    - V_fps = muzzle velocity (ft/sec)
    - T = twist rate (inches per turn)
    - d_effective = effective bullet diameter in inches (bearing band diameter for land-riding)
    - l = bullet length in calibers = L/d_effective
    - L = bullet length (inches)

    CRITICAL: Use d_effective (band diameter), NOT nominal diameter.
    For land-riding bullets: d_effective = band diameter (typically 6.5-6.6 mm, NOT 6.7 mm)

    Args:
        diameter_mm: Bullet diameter in millimeters (nominal/groove diameter)
        length_mm: Bullet length in millimeters
        weight_grains: Bullet weight in grains
        twist_rate_inches: Barrel twist rate (e.g., 8 for 1:8")
        velocity_mps: Muzzle velocity in meters per second (default ~853 m/s = ~2800 fps)
        temperature_c: Temperature in Celsius (default 15°C = ~59°F)
        pressure_hpa: Atmospheric pressure in hectopascals (default 1013.25 hPa = 29.92 inHg)
        effective_diameter_mm: Effective diameter at bearing bands for land-riding bullets.
            For land-riding bullets: typically 6.5-6.6 mm (NOT 6.7 mm nominal).
            If None, uses diameter_mm.
        material_density_g_per_cm3: Material density in g/cm³ used to determine bullet class.

    Returns:
        Tuple of (stability_factor, stability_threshold)
        - stability_factor: Calculated stability factor (dimensionless)
        - stability_threshold: Required threshold.
          1.8 for monolithic copper/brass, 1.5 for lead-core.
    """
    if (
        diameter_mm <= 0
        or length_mm <= 0
        or weight_grains <= 0
        or twist_rate_inches <= 0
    ):
        return (0.0, 1.5)

    # Determine if monolithic copper/brass bullet
    # Monolithic copper/brass typically has density 7.85-8.96 g/cm³
    # Lead-core bullets typically have density > 10 g/cm³
    is_monolithic_copper_brass = False
    if material_density_g_per_cm3 is not None:
        # Monolithic copper/brass: density typically 7.85-9.0 g/cm³
        # Lead-core: density typically > 10 g/cm³
        if 7.0 <= material_density_g_per_cm3 <= 9.5:
            is_monolithic_copper_brass = True

    # Determine stability threshold
    stability_threshold = 1.8 if is_monolithic_copper_brass else 1.5

    # Use effective diameter (bearing band diameter) if provided.
    # CRITICAL: For land-riding bullets, d_effective is band diameter.
    # Typical value is 6.5-6.6 mm, not nominal 6.7 mm.
    # For groove-riding bullets, effective diameter equals nominal diameter
    d_effective_mm = (
        effective_diameter_mm if effective_diameter_mm is not None else diameter_mm
    )

    # Convert to inches (formula uses imperial units)
    d_effective_inches = d_effective_mm / 25.4
    length_inches = length_mm / 25.4

    # Mass in grains
    mass_grains = (
        corrected_mass_grains if corrected_mass_grains is not None else weight_grains
    )

    # Convert velocity to fps
    velocity_fps = velocity_mps * 3.28084

    # Step 1: Basic calculation
    # Length in calibers: l = L / d_effective
    if l_effective_calibers is not None and l_effective_calibers > 0:
        length_calibers = l_effective_calibers
    else:
        length_calibers = length_inches / d_effective_inches

    # Twist rate in calibers per turn: t = T / d_effective
    twist_calibers = twist_rate_inches / d_effective_inches

    # Basic Miller formula: Sg = (30 × m) / (t² × d_effective³ × l × (1 + l²))
    stability = (30.0 * mass_grains) / (
        (twist_calibers**2)
        * (d_effective_inches**3)
        * length_calibers
        * (1.0 + length_calibers**2)
    )

    # Step 2: Velocity correction
    # Sg_corrected = Sg × (V_fps / 2800)^(1/3)
    if velocity_fps > 0:
        velocity_correction = math.pow(velocity_fps / 2800.0, 1.0 / 3.0)
    else:
        velocity_correction = 1.0
    stability = stability * velocity_correction

    # Convert metric inputs to imperial for atmospheric corrections
    # Temperature: Celsius to Fahrenheit
    temperature_f = (temperature_c * 9.0 / 5.0) + 32.0
    # Pressure: hPa to inHg (1 hPa = 0.0295299830714 inHg)
    pressure_inhg = pressure_hpa * 0.0295299830714

    # Temperature correction (formula uses Rankine: F + 459.67)
    # Standard reference: 59°F = 518.67°R
    temp_correction = math.sqrt((temperature_f + 459.67) / 518.67)

    # Pressure correction (standard is 29.92 inHg)
    pressure_correction = math.sqrt(pressure_inhg / 29.92)

    # Apply atmospheric corrections
    stability = stability * temp_correction * pressure_correction

    # Round to 2 decimal places for display
    return (round(stability, 2), stability_threshold)


def calculate_nose_configuration(
    nose_type: str,
    original_mass_grains: float,
    length_mm: float,
    d_effective_mm: float,
    bullet_density_gcm3: float,
    hp_diameter_mm: float = 0.0,
    hp_depth_mm: float = 0.0,
    cavity_shape: str = "cylindrical",
    tip_length_mm: float = 0.0,
    tip_base_diameter_mm: float = 0.0,
    tip_tip_diameter_mm: float = 0.0,
    tip_density_gcm3: float = 1.32,
    body_length_mm: Optional[float] = None,
) -> Dict[str, float]:
    """
    Calculate hollow-point / tip corrections while preserving solid defaults.
    """
    result = {
        "mass_removed_grains": 0.0,
        "mass_added_grains": 0.0,
        "corrected_mass_grains": original_mass_grains,
        "l_effective_calibers": (
            (length_mm / d_effective_mm) if d_effective_mm > 0 else 0.0
        ),
        "effective_meplat_mm": 0.0,
        "hp_penalty_applied": 0.0,
    }

    if nose_type == "solid":
        return result

    if d_effective_mm <= 0 or bullet_density_gcm3 <= 0 or length_mm <= 0:
        return result

    if hp_diameter_mm <= 0 or hp_depth_mm <= 0:
        return result

    cavity_radius = hp_diameter_mm / 2.0
    if cavity_shape == "conical":
        v_cavity = (math.pi / 3.0) * (cavity_radius**2) * hp_depth_mm
    else:
        v_cavity = math.pi * (cavity_radius**2) * hp_depth_mm

    mass_removed = (v_cavity / 1000.0) * bullet_density_gcm3 * 15.4323584
    corrected_mass = original_mass_grains - mass_removed
    result["mass_removed_grains"] = max(0.0, mass_removed)

    if nose_type == "hp":
        # l_effective = (L - 0.4 * HP_depth) / d_effective
        l_eff = (length_mm - 0.4 * hp_depth_mm) / d_effective_mm
        result["l_effective_calibers"] = max(0.01, l_eff)
        result["corrected_mass_grains"] = max(0.0, corrected_mass)
        result["effective_meplat_mm"] = hp_diameter_mm
        result["hp_penalty_applied"] = 1.0
        return result

    if nose_type == "hp_tip":
        if tip_length_mm > 0 and tip_base_diameter_mm > 0 and tip_density_gcm3 > 0:
            tip_radius = tip_base_diameter_mm / 2.0
            v_tip = (math.pi / 3.0) * (tip_radius**2) * tip_length_mm
            mass_added = (v_tip / 1000.0) * tip_density_gcm3 * 15.4323584
        else:
            mass_added = 0.0

        corrected_mass = corrected_mass + mass_added
        # l_effective = (L + tip_length * (tip_density / bullet_density)) / d_effective
        l_eff = (
            length_mm + tip_length_mm * (tip_density_gcm3 / bullet_density_gcm3)
        ) / d_effective_mm
        result["mass_added_grains"] = max(0.0, mass_added)
        result["corrected_mass_grains"] = max(0.0, corrected_mass)
        result["l_effective_calibers"] = max(0.01, l_eff)
        result["effective_meplat_mm"] = max(0.0, tip_tip_diameter_mm)
        result["hp_penalty_applied"] = 0.0
        return result

    return result


def check_tip_velocity_limit(
    material_name: str, velocity_ms: float
) -> Tuple[str, Optional[str]]:
    """
    Validate muzzle velocity against tip material velocity rating.
    Returns (severity, message): severity in {"OK", "WARNING", "ERROR"}.
    """
    if not material_name:
        return ("OK", None)

    material_db = get_material_database()
    tip_data = material_db.get_tip_material(material_name)
    if not tip_data:
        return ("OK", None)

    max_vel = float(tip_data.get("max_velocity_ms", 0.0))
    if max_vel <= 0:
        return (
            "ERROR",
            "This material is for geometry verification only. No live fire.",
        )

    if velocity_ms > max_vel:
        return (
            "WARNING",
            (
                f"WARNING: {material_name} is rated to {max_vel:.0f} m/s. "
                f"At {velocity_ms:.0f} m/s aerodynamic heating will cause tip "
                "deformation and BC shift in flight. Use PEEK or Torlon for this velocity."
            ),
        )

    return ("OK", None)


def min_wall_thickness(material_density_gcm3: float, velocity_ms: float) -> float:
    """
    Return minimum HP wall thickness in mm.

    Wall thickness is measured at the meplat radially between HP bore
    and outer surface.
    """
    if material_density_gcm3 <= 9.5:
        base = 0.5
    elif material_density_gcm3 <= 11.5:
        base = 0.35
    else:
        base = 0.3

    if velocity_ms > 900.0:
        surcharge = (velocity_ms - 900.0) / 4000.0
    else:
        surcharge = 0.0

    return round(base + surcharge, 3)


def validate_hp_diameter(
    meplat_mm: float,
    hp_diameter_mm: float,
    material_density_gcm3: float,
    velocity_ms: float,
) -> Optional[str]:
    """
    Validate HP diameter against wall-thickness-limited max HP diameter.

    Governing relation:
        HP_diameter_max = meplat_diameter - (2 * minimum_wall_thickness)
    """
    if meplat_mm <= 0.0 or hp_diameter_mm <= 0.0:
        return None

    min_wall = min_wall_thickness(material_density_gcm3, velocity_ms)
    max_hp = meplat_mm - (2.0 * min_wall)

    if hp_diameter_mm > max_hp:
        return (
            f"ERROR: HP diameter {hp_diameter_mm:.2f} mm exceeds maximum "
            f"{max_hp:.2f} mm for this material at {velocity_ms:.0f} m/s. "
            f"Minimum wall thickness required: {min_wall:.2f} mm per side."
        )

    return None


def calculate_hp_depth_limits(
    diameter_mm: float,
    ogive_caliber_ratio: float,
) -> Tuple[float, float]:
    """
    Return practical HP depth range (min_recommended, max_allowed) in mm.

    Practical rule:
      HP_depth_max ~= ogive_length * 0.60
      Recommended start ~= ogive_length * 0.50
    where ogive_length = (ogive_caliber_ratio * diameter_mm) / 2
    """
    if diameter_mm <= 0.0 or ogive_caliber_ratio <= 0.0:
        return (0.0, 0.0)

    ogive_length = (ogive_caliber_ratio * diameter_mm) / 2.0
    return (round(ogive_length * 0.50, 3), round(ogive_length * 0.60, 3))


def _tip_manufacturing_method(material_name: str) -> str:
    """Infer manufacturing method for tip point minimum limits."""
    name = (material_name or "").lower()
    if "resin sla" in name or "sla" in name:
        return "sla"
    if "3d printed" in name or "fdm" in name or "pla" in name or "petg" in name:
        return "fdm"
    return "machined"


def _tip_point_minimum_diameter_mm(material_name: str) -> float:
    """Return minimum allowed tip point diameter in mm by method."""
    method = _tip_manufacturing_method(material_name)
    if method == "sla":
        return 0.5
    if method == "fdm":
        return 0.8
    return 0.3


def validate_tip_design(
    meplat_mm: float,
    hp_depth_mm: float,
    ogive_length_mm: float,
    tip_length_mm: float,
    tip_base_diameter_mm: float,
    tip_tip_diameter_mm: float,
    tip_material_name: str,
) -> Dict[str, object]:
    """
    Validate HP+tip geometric rules and return errors/warnings/derived metrics.
    """
    result = {
        "errors": [],
        "warnings": [],
        "tip_half_angle_deg": 0.0,
        "assembled_length_min_mm": 0.0,
        "assembled_length_max_mm": 0.0,
        "air_gap_min_mm": 0.0,
        "tip_point_min_mm": 0.0,
    }

    if tip_length_mm > 0 and tip_base_diameter_mm > tip_tip_diameter_mm:
        half_angle_rad = math.atan(
            (tip_base_diameter_mm - tip_tip_diameter_mm) / (2.0 * tip_length_mm)
        )
        half_angle_deg = math.degrees(half_angle_rad)
        result["tip_half_angle_deg"] = half_angle_deg
        if half_angle_deg < 5.0 or half_angle_deg > 10.0:
            result["warnings"].append(
                f"Tip half-angle {half_angle_deg:.2f} deg is outside recommended 5-10 deg."
            )

    tip_point_min = _tip_point_minimum_diameter_mm(tip_material_name)
    result["tip_point_min_mm"] = tip_point_min
    if tip_tip_diameter_mm > 0 and tip_tip_diameter_mm < tip_point_min:
        result["errors"].append(
            f"Tip tip diameter {tip_tip_diameter_mm:.2f} mm is below minimum "
            f"{tip_point_min:.2f} mm for this manufacturing method."
        )

    # Feasible assembly range using practical defaults:
    # stem = 35-45% of HP depth, shoulder = 0.20-0.40 mm.
    stem_min = hp_depth_mm * 0.35
    stem_max = hp_depth_mm * 0.45
    shoulder_min = 0.20
    shoulder_max = 0.40
    assembled_min = stem_min + shoulder_min + tip_length_mm
    assembled_max = stem_max + shoulder_max + tip_length_mm
    result["assembled_length_min_mm"] = assembled_min
    result["assembled_length_max_mm"] = assembled_max

    target_min = max(0.0, ogive_length_mm - 0.1)
    target_max = ogive_length_mm + 0.1
    intersects_target = (assembled_max >= target_min) and (assembled_min <= target_max)
    if ogive_length_mm > 0 and not intersects_target:
        result["errors"].append(
            "Tip assembled length (stem + shoulder + cone) cannot fit within "
            f"ogive length tolerance ({target_min:.2f}-{target_max:.2f} mm)."
        )

    # Air gap rule: cavity floor must remain at least 0.15 mm below stem tip.
    # Worst-case air gap occurs with longest stem.
    air_gap_min = hp_depth_mm - stem_max
    result["air_gap_min_mm"] = air_gap_min
    if hp_depth_mm > 0 and air_gap_min < 0.15:
        result["errors"].append(
            f"Stem bottoms out risk: minimum air gap {air_gap_min:.2f} mm is below 0.15 mm."
        )

    # Solid nose above cavity floor rule.
    solid_nose_remaining = ogive_length_mm - hp_depth_mm
    min_solid_nose = meplat_mm * 1.5
    if ogive_length_mm > 0 and solid_nose_remaining < min_solid_nose:
        result["errors"].append(
            f"Solid nose remaining {solid_nose_remaining:.2f} mm is below required "
            f"{min_solid_nose:.2f} mm (1.5 x meplat)."
        )

    return result


def calculate_volume_from_weight(
    weight_grains: float, density_g_per_cm3: float
) -> float:
    """
    Calculate bullet volume from weight and material density.

    Args:
        weight_grains: Bullet weight in grains
        density_g_per_cm3: Material density in g/cm³

    Returns:
        Volume in cubic millimeters
    """
    if weight_grains <= 0 or density_g_per_cm3 <= 0:
        return 0.0

    # Convert grains to grams
    weight_grams = weight_grains / 15.4323584

    # Calculate volume in cm³
    volume_cm3 = weight_grams / density_g_per_cm3

    # Convert to mm³
    volume_mm3 = volume_cm3 * 1000.0

    return volume_mm3


def calculate_weight_from_volume(volume_mm3: float, density_g_per_cm3: float) -> float:
    """
    Calculate bullet weight from volume and material density.

    Args:
        volume_mm3: Bullet volume in cubic millimeters
        density_g_per_cm3: Material density in g/cm³

    Returns:
        Weight in grains
    """
    if volume_mm3 <= 0 or density_g_per_cm3 <= 0:
        return 0.0

    # Convert mm³ to cm³
    volume_cm3 = volume_mm3 / 1000.0

    # Calculate weight in grams
    weight_grams = volume_cm3 * density_g_per_cm3

    # Convert to grains
    weight_grains = weight_grams * 15.4323584

    return weight_grains


def calculate_bearing_surface(
    diameter_mm: float,
    length_mm: float,
    num_bands: int,
    band_length_mm: float,
    band_spacing_mm: float,
) -> float:
    """
    Calculate total bearing surface area of bullet.

    Bearing surface = area of all driving bands + body contact area

    Args:
        diameter_mm: Bullet diameter in millimeters
        length_mm: Total bullet length in millimeters
        num_bands: Number of driving bands
        band_length_mm: Length of each band in millimeters
        band_spacing_mm: Spacing between bands in millimeters

    Returns:
        Bearing surface area in square millimeters
    """
    if diameter_mm <= 0 or length_mm <= 0:
        return 0.0

    # Circumference
    circumference = math.pi * diameter_mm

    # Band area
    band_area = num_bands * band_length_mm * circumference

    # Body area (simplified - assumes bands are the main bearing surface)
    # For more accuracy, subtract band areas from total surface
    total_surface = circumference * length_mm

    # If we have bands, use band area; otherwise use total surface
    if num_bands > 0:
        bearing_surface = band_area
    else:
        # No bands - entire surface is bearing surface
        bearing_surface = total_surface

    return bearing_surface


def calculate_ogive_radius(
    caliber_ratio: float, diameter_mm: float, ogive_type: str = "Tangent"
) -> float:
    """
    Calculate ogive radius from caliber ratio.

    Args:
        caliber_ratio: Ogive length in calibers (diameter units)
        diameter_mm: Bullet diameter in millimeters
        ogive_type: Type of ogive ("Tangent", "Secant", "Elliptical")

    Returns:
        Ogive radius in millimeters
    """
    if caliber_ratio <= 0 or diameter_mm <= 0:
        return 0.0

    ogive_length = (caliber_ratio * diameter_mm) / 2.0

    # For tangent ogive: R = (L^2 + D^2/4) / (2*D)
    # Simplified approximation
    if ogive_type == "Tangent":
        radius = (ogive_length**2 + (diameter_mm / 2) ** 2) / diameter_mm
    elif ogive_type == "Secant":
        # Secant ogive typically has larger radius
        radius = (ogive_length**2 + (diameter_mm / 2) ** 2) / diameter_mm * 1.1
    else:  # Elliptical
        # Elliptical approximation
        radius = ogive_length * 1.2

    return radius


def calculate_bullet_dimensions_from_weight(
    target_weight_grains: float,
    groove_diameter_mm: float,
    land_diameter_mm: float,
    material_density_g_per_cm3: float,
    num_bands: int,
    band_length_mm: float,
    band_spacing_mm: float,
    ogive_caliber_ratio: float,
    ogive_type: str,
    boat_tail_angle_deg: float,
    meplat_diameter_mm: float,
    land_riding: bool = True,
    max_iterations: int = 10,
) -> Dict[str, float]:
    """
    Calculate bullet dimensions from target weight and other parameters.

    This function performs reverse calculation: given a target weight,
    it calculates the required bullet length and other dimensions.

    Args:
        target_weight_grains: Target bullet weight in grains
        groove_diameter_mm: Groove diameter in mm
        land_diameter_mm: Land diameter in mm
        material_density_g_per_cm3: Material density in g/cm³
        num_bands: Number of driving bands
        band_length_mm: Length of each band in mm
        band_spacing_mm: Spacing between bands in mm
        ogive_caliber_ratio: Ogive caliber ratio
        ogive_type: Type of ogive ("Tangent", "Secant", "Elliptical")
        boat_tail_angle_deg: Boat tail angle in degrees
        meplat_diameter_mm: Meplat (tip) diameter in mm
        land_riding: True for land riding (body at land diameter), False for groove riding
        max_iterations: Maximum iterations for boat tail adjustment

    Returns:
        Dictionary with calculated dimensions and ballistic properties:
        - total_length_mm: Total bullet length
        - boat_tail_length_mm: Boat tail length (may be adjusted)
        - bearing_surface_length_mm: Length of bearing surface section
        - ogive_length_mm: Ogive length
        - gap_length_needed_mm: Required gap length between bands
        - gap_coverage_mm: Actual gap coverage from spacing
        - calculated_weight_grains: Calculated weight (should match target)
        - ballistic_coefficient_g1: Calculated G1 ballistic coefficient
        - sectional_density: Sectional density
        - length_diameter_ratio: Length to diameter ratio
        - meplat_ratio: Meplat to groove diameter ratio
        - form_factor: Final form factor used in BC calculation
        - is_valid: Whether dimensions are valid
        - validation_message: Message explaining validation result
    """
    # Constants
    GRAINS_TO_GRAMS = 0.06479891
    CM3_TO_MM3 = 1000.0

    # 1. REQUIRED VOLUME
    weight_g = target_weight_grains * GRAINS_TO_GRAMS
    volume_total_mm3 = (weight_g / material_density_g_per_cm3) * CM3_TO_MM3

    # 2. RADII
    r_groove = groove_diameter_mm / 2.0
    r_land = land_diameter_mm / 2.0
    r_meplat = meplat_diameter_mm / 2.0

    # 3. OGIVE LENGTH
    ogive_length_mm = (ogive_caliber_ratio * groove_diameter_mm) / 2.0

    # 4. OGIVE VOLUME (paraboloid approximation)
    # Using simplified paraboloid volume: V = (π × r² × h) / 2
    # Average radius approximation for ogive
    V_ogive_mm3 = (math.pi * r_land * r_land * ogive_length_mm) / 2.0

    # 5. BOAT TAIL (iterative calculation)
    boat_tail_length_mm = groove_diameter_mm * 0.7  # Start estimate
    boat_tail_angle_rad = math.radians(boat_tail_angle_deg)

    for iteration in range(max_iterations):
        # Calculate boat tail base radius
        bt_reduction = boat_tail_length_mm * math.tan(boat_tail_angle_rad)
        r_base = r_land - bt_reduction
        r_base = max(r_base, r_groove * 0.3)  # Minimum 30% of groove radius

        # Boat tail volume (frustum of cone)
        # V = (π × h / 3) × (r1² + r1×r2 + r2²)
        V_boattail_mm3 = (math.pi * boat_tail_length_mm / 3.0) * (
            r_base * r_base + r_base * r_land + r_land * r_land
        )

        # 6. BEARING SURFACE VOLUME NEEDED
        V_bearing_mm3 = volume_total_mm3 - V_ogive_mm3 - V_boattail_mm3

        if V_bearing_mm3 <= 0:
            # Boat tail too long, reduce it
            boat_tail_length_mm *= 0.8
            continue

        # 7. BEARING SURFACE BREAKDOWN
        band_coverage_mm = num_bands * band_length_mm
        gap_coverage_mm = (num_bands - 1) * band_spacing_mm if num_bands > 1 else 0.0

        if land_riding:
            # LAND RIDING: Body is at land diameter, bands are annular expansions
            # Body volume = π × r_land² × length
            # Band volume = num_bands × π × (r_groove² - r_land²) × band_length

            # Volume of bands (annular cylinders from land to groove)
            V_bands_mm3 = (
                num_bands
                * math.pi
                * (r_groove * r_groove - r_land * r_land)
                * band_length_mm
            )

            # Volume needed for gaps (land diameter cylinder)
            V_gaps_needed_mm3 = V_bearing_mm3 - V_bands_mm3

            if V_gaps_needed_mm3 < 0:
                # Bands alone exceed volume - reduce boat tail further
                boat_tail_length_mm *= 0.9
                continue

            # Gap length needed (at land diameter)
            gap_length_needed_mm = V_gaps_needed_mm3 / (math.pi * r_land * r_land)
        else:
            # GROOVE RIDING: Body is at groove diameter
            # Volume of bands (annular cylinders)
            V_bands_mm3 = (
                num_bands
                * math.pi
                * (r_groove * r_groove - r_land * r_land)
                * band_length_mm
            )

            # Volume needed for gaps (groove diameter cylinder)
            V_gaps_needed_mm3 = V_bearing_mm3 - V_bands_mm3

            if V_gaps_needed_mm3 < 0:
                # Bands alone exceed volume - reduce boat tail further
                boat_tail_length_mm *= 0.9
                continue

            # Gap length needed (at groove diameter)
            gap_length_needed_mm = V_gaps_needed_mm3 / (math.pi * r_groove * r_groove)

        # Total bearing surface length
        total_bearing_length_mm = band_coverage_mm + gap_length_needed_mm

        # VALIDATION: gap_length_needed should ≥ gap_coverage
        if gap_length_needed_mm >= gap_coverage_mm:
            # Valid! Calculate total length
            total_length_mm = (
                boat_tail_length_mm + total_bearing_length_mm + ogive_length_mm
            )

            # Verify calculated weight
            # Recalculate volumes for verification
            V_ogive_check = (math.pi * r_land * r_land * ogive_length_mm) / 2.0
            V_boattail_check = (math.pi * boat_tail_length_mm / 3.0) * (
                r_base * r_base + r_base * r_land + r_land * r_land
            )
            V_bands_check = (
                num_bands
                * math.pi
                * (r_groove * r_groove - r_land * r_land)
                * band_length_mm
            )
            if land_riding:
                V_gaps_check = gap_length_needed_mm * math.pi * r_land * r_land
            else:
                V_gaps_check = gap_length_needed_mm * math.pi * r_groove * r_groove
            V_total_check = (
                V_ogive_check + V_boattail_check + V_bands_check + V_gaps_check
            )

            calculated_weight_g = (
                V_total_check / CM3_TO_MM3
            ) * material_density_g_per_cm3
            calculated_weight_grains = calculated_weight_g / GRAINS_TO_GRAMS

            # 9. BALLISTIC COEFFICIENT (G1) CALCULATION
            # a. Convert to inches
            diameter_in = groove_diameter_mm / 25.4
            length_in = total_length_mm / 25.4

            # b. Sectional Density
            weight_lbs = target_weight_grains / 7000.0
            SD = weight_lbs / (diameter_in * diameter_in)

            # c. Form Factor (base based on ogive type)
            form_factors_base = {"Tangent": 0.85, "Secant": 0.80, "Elliptical": 0.75}
            i = form_factors_base.get(ogive_type, 0.85)

            # d. Length correction
            length_ratio = length_in / diameter_in
            if length_ratio > 4.0:
                i = i * 0.95  # Longer = better BC
            elif length_ratio < 3.0:
                i = i * 1.05  # Shorter = worse BC

            # e. Meplat correction
            meplat_ratio = meplat_diameter_mm / groove_diameter_mm
            if meplat_ratio > 0.3:
                i = i * 1.10  # Blunt tip = worse BC
            elif meplat_ratio < 0.1:
                i = i * 0.98  # Sharp tip = better BC

            # f. Boat tail correction
            if boat_tail_angle_deg > 0:
                i = i * 0.95  # Boat tail = better BC

            # g. Final BC
            BC_G1 = SD / i

            is_valid = True
            validation_message = (
                "Valid: gap_length_needed "
                f"({gap_length_needed_mm:.2f}mm) >= "
                f"gap_coverage ({gap_coverage_mm:.2f}mm)"
            )

            return {
                "total_length_mm": total_length_mm,
                "boat_tail_length_mm": boat_tail_length_mm,
                "bearing_surface_length_mm": total_bearing_length_mm,
                "ogive_length_mm": ogive_length_mm,
                "gap_length_needed_mm": gap_length_needed_mm,
                "gap_coverage_mm": gap_coverage_mm,
                "calculated_weight_grains": calculated_weight_grains,
                "target_weight_grains": target_weight_grains,
                "weight_error_percent": abs(
                    calculated_weight_grains - target_weight_grains
                )
                / target_weight_grains
                * 100.0,
                "ballistic_coefficient_g1": BC_G1,
                "sectional_density": SD,
                "length_diameter_ratio": length_ratio,
                "meplat_ratio": meplat_ratio,
                "form_factor": i,
                "is_valid": is_valid,
                "validation_message": validation_message,
            }
        else:
            # Gap doesn't fit - reduce boat tail and try again
            boat_tail_length_mm *= 0.9

    # Failed to find valid solution
    gap_length_needed_final = (
        gap_length_needed_mm if "gap_length_needed_mm" in locals() else 0.0
    )
    gap_coverage_final = gap_coverage_mm if "gap_coverage_mm" in locals() else 0.0

    return {
        "total_length_mm": 0.0,
        "boat_tail_length_mm": boat_tail_length_mm,
        "bearing_surface_length_mm": 0.0,
        "ogive_length_mm": ogive_length_mm,
        "gap_length_needed_mm": gap_length_needed_final,
        "gap_coverage_mm": gap_coverage_final,
        "calculated_weight_grains": 0.0,
        "target_weight_grains": target_weight_grains,
        "weight_error_percent": 100.0,
        "ballistic_coefficient_g1": 0.0,
        "sectional_density": 0.0,
        "length_diameter_ratio": 0.0,
        "meplat_ratio": (
            meplat_diameter_mm / groove_diameter_mm if groove_diameter_mm > 0 else 0.0
        ),
        "form_factor": 0.0,
        "is_valid": False,
        "validation_message": (
            f"Failed to find valid dimensions after {max_iterations} iterations. "
            f"Gap needed ({gap_length_needed_final:.2f}mm) < "
            f"gap coverage ({gap_coverage_final:.2f}mm). "
            "Try reducing band spacing or increasing target weight."
        ),
    }
