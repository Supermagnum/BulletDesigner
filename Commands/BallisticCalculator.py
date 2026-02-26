"""
Ballistic Calculator command for Bullet Designer workbench.

This command opens a dialog for calculating ballistic properties
including stability, BC, and twist rate recommendations.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide2 import QtWidgets
import os
import sys

# Add Utils to path
wb_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(wb_path, "Utils"))

from Utils.Calculations import (
    calculate_stability_factor_miller,
    calculate_ballistic_coefficient_g1,
    calculate_sectional_density,
    calculate_recommended_twist_rate,
    calculate_nose_configuration,
    check_tip_velocity_limit,
    validate_hp_diameter,
    calculate_hp_depth_limits,
    validate_tip_design,
    min_wall_thickness,
)
from Utils.MaterialDatabase import get_material_database

# Units: 0 = Metric (m/s, Celsius, hPa), 1 = Imperial (fps, Fahrenheit, inHg)
PREF_GROUP = "User parameter:BaseApp/Preferences/Mod/BulletDesigner"
FPS_TO_MPS = 0.3048
INHG_TO_HPA = 33.8639


def _get_ballistic_units():
    """Get ballistic calculator units from FreeCAD preferences (0=Metric, 1=Imperial)."""
    param = App.ParamGet(PREF_GROUP)
    return param.GetInt("Units", 0)


def _set_ballistic_units(metric):
    """Save ballistic calculator units to FreeCAD preferences."""
    param = App.ParamGet(PREF_GROUP)
    param.SetInt("Units", 0 if metric else 1)


class BallisticCalculatorDialog(QtWidgets.QDialog):
    """
    Dialog for ballistic calculations.
    """

    def __init__(self, bullet_obj=None, parent=None):
        """
        Initialize the calculator dialog.

        Args:
            bullet_obj: Optional bullet object to use
            parent: Parent widget
        """
        super().__init__(parent)
        self.bullet_obj = bullet_obj
        self.setWindowTitle("Ballistic Calculator")
        self.setMinimumWidth(500)
        self._metric = _get_ballistic_units() == 0

        self._create_ui()
        self._load_bullet_data()

    def _create_ui(self):
        """Create the user interface."""
        layout = QtWidgets.QVBoxLayout(self)

        # Input section
        input_group = QtWidgets.QGroupBox("Input Parameters")
        input_layout = QtWidgets.QFormLayout()

        # Units toggle (follows FreeCAD/BulletDesigner preference)
        self.units_combo = QtWidgets.QComboBox()
        self.units_combo.addItems(["Metric (m/s, °C, hPa)", "Imperial (fps, °F, inHg)"])
        self.units_combo.setCurrentIndex(0 if self._metric else 1)
        self.units_combo.currentIndexChanged.connect(self._on_units_changed)
        input_layout.addRow("Units:", self.units_combo)

        # Bullet selection
        self.bullet_combo = QtWidgets.QComboBox()
        self._populate_bullet_combo()
        input_layout.addRow("Bullet:", self.bullet_combo)

        # Manual entry fields
        self.diameter_spin = QtWidgets.QDoubleSpinBox()
        self.diameter_spin.setRange(0.1, 50.0)
        self.diameter_spin.setSuffix(" mm")
        self.diameter_spin.setDecimals(2)
        input_layout.addRow("Diameter:", self.diameter_spin)

        self.length_spin = QtWidgets.QDoubleSpinBox()
        self.length_spin.setRange(1.0, 200.0)
        self.length_spin.setSuffix(" mm")
        self.length_spin.setDecimals(2)
        input_layout.addRow("Length:", self.length_spin)

        self.weight_spin = QtWidgets.QDoubleSpinBox()
        self.weight_spin.setRange(1.0, 2000.0)
        self.weight_spin.setSuffix(" grains")
        self.weight_spin.setDecimals(1)
        input_layout.addRow("Weight:", self.weight_spin)

        self.ogive_type_combo = QtWidgets.QComboBox()
        self.ogive_type_combo.addItems(["Tangent", "Secant", "Elliptical"])
        input_layout.addRow("Ogive Type:", self.ogive_type_combo)

        self.nose_type_combo = QtWidgets.QComboBox()
        self.nose_type_combo.addItems(["Solid", "Hollow Point", "Hollow Point + Tip"])
        input_layout.addRow("Nose Type:", self.nose_type_combo)

        self.hp_diameter_spin = QtWidgets.QDoubleSpinBox()
        self.hp_diameter_spin.setRange(0.0, 50.0)
        self.hp_diameter_spin.setSuffix(" mm")
        self.hp_diameter_spin.setDecimals(3)
        input_layout.addRow("HP Diameter:", self.hp_diameter_spin)

        self.hp_depth_spin = QtWidgets.QDoubleSpinBox()
        self.hp_depth_spin.setRange(0.0, 100.0)
        self.hp_depth_spin.setSuffix(" mm")
        self.hp_depth_spin.setDecimals(3)
        input_layout.addRow("HP Depth:", self.hp_depth_spin)

        self.cavity_shape_combo = QtWidgets.QComboBox()
        self.cavity_shape_combo.addItems(["cylindrical", "conical"])
        input_layout.addRow("Cavity Shape:", self.cavity_shape_combo)

        material_db = get_material_database()
        self.tip_material_combo = QtWidgets.QComboBox()
        self.tip_material_combo.addItems(material_db.get_tip_material_names())
        tip_default_idx = self.tip_material_combo.findText("PEEK")
        if tip_default_idx >= 0:
            self.tip_material_combo.setCurrentIndex(tip_default_idx)
        input_layout.addRow("Tip Material:", self.tip_material_combo)

        self.tip_density_spin = QtWidgets.QDoubleSpinBox()
        self.tip_density_spin.setRange(0.1, 20.0)
        self.tip_density_spin.setSuffix(" g/cm³")
        self.tip_density_spin.setDecimals(3)
        self.tip_density_spin.setValue(1.32)
        input_layout.addRow("Tip Density:", self.tip_density_spin)

        self.tip_length_spin = QtWidgets.QDoubleSpinBox()
        self.tip_length_spin.setRange(0.0, 50.0)
        self.tip_length_spin.setSuffix(" mm")
        self.tip_length_spin.setDecimals(3)
        input_layout.addRow("Tip Length:", self.tip_length_spin)

        self.tip_base_diameter_spin = QtWidgets.QDoubleSpinBox()
        self.tip_base_diameter_spin.setRange(0.0, 50.0)
        self.tip_base_diameter_spin.setSuffix(" mm")
        self.tip_base_diameter_spin.setDecimals(3)
        input_layout.addRow("Tip Base Diameter:", self.tip_base_diameter_spin)

        self.tip_tip_diameter_spin = QtWidgets.QDoubleSpinBox()
        self.tip_tip_diameter_spin.setRange(0.0, 50.0)
        self.tip_tip_diameter_spin.setSuffix(" mm")
        self.tip_tip_diameter_spin.setDecimals(3)
        input_layout.addRow("Tip Tip Diameter:", self.tip_tip_diameter_spin)

        # Material selection (for stability threshold determination)
        material_db = get_material_database()
        material_names = material_db.get_material_names()
        self.material_combo = QtWidgets.QComboBox()
        self.material_combo.addItems(material_names)
        # Default to Pure Copper for monolithic bullets
        copper_idx = self.material_combo.findText("Pure Copper")
        if copper_idx >= 0:
            self.material_combo.setCurrentIndex(copper_idx)
        input_layout.addRow("Material:", self.material_combo)

        # Barrel parameters
        self.twist_spin = QtWidgets.QDoubleSpinBox()
        self.twist_spin.setRange(1.0, 50.0)
        self.twist_spin.setSuffix(" inches")
        self.twist_spin.setValue(10.0)
        input_layout.addRow("Barrel Twist:", self.twist_spin)

        self.velocity_spin = QtWidgets.QDoubleSpinBox()
        self._apply_velocity_units(set_default=True)
        input_layout.addRow("Velocity:", self.velocity_spin)

        # Atmospheric conditions
        self.temp_spin = QtWidgets.QDoubleSpinBox()
        self._apply_temp_units(set_default=True)
        input_layout.addRow("Temperature:", self.temp_spin)

        self.pressure_spin = QtWidgets.QDoubleSpinBox()
        self._apply_pressure_units(set_default=True)
        input_layout.addRow("Pressure:", self.pressure_spin)

        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Results section
        results_group = QtWidgets.QGroupBox("Results")
        results_layout = QtWidgets.QFormLayout()

        self.stability_label = QtWidgets.QLabel("N/A")
        results_layout.addRow("Stability Factor:", self.stability_label)

        self.stability_status_label = QtWidgets.QLabel("")
        results_layout.addRow("Status:", self.stability_status_label)

        self.bc_label = QtWidgets.QLabel("0.0")
        results_layout.addRow("BC (G1):", self.bc_label)

        self.sd_label = QtWidgets.QLabel("0.0")
        results_layout.addRow("Sectional Density:", self.sd_label)

        self.recommended_twist_label = QtWidgets.QLabel("N/A")
        results_layout.addRow("Recommended Twist:", self.recommended_twist_label)

        self.mass_removed_label = QtWidgets.QLabel("0.0")
        results_layout.addRow("Mass Removed (gr):", self.mass_removed_label)

        self.mass_added_label = QtWidgets.QLabel("0.0")
        results_layout.addRow("Mass Added (gr):", self.mass_added_label)

        self.corrected_mass_label = QtWidgets.QLabel("0.0")
        results_layout.addRow("Corrected Mass (gr):", self.corrected_mass_label)

        self.form_factor_label = QtWidgets.QLabel("N/A")
        results_layout.addRow("Form Factor Used:", self.form_factor_label)

        self.meplat_used_label = QtWidgets.QLabel("N/A")
        results_layout.addRow("Effective Meplat (mm):", self.meplat_used_label)

        self.corrected_l_label = QtWidgets.QLabel("N/A")
        results_layout.addRow("Corrected l (cal):", self.corrected_l_label)

        self.tip_velocity_label = QtWidgets.QLabel("N/A")
        results_layout.addRow("Tip Velocity Rating:", self.tip_velocity_label)

        self.velocity_warning_label = QtWidgets.QLabel("")
        self.velocity_warning_label.setWordWrap(True)
        results_layout.addRow("Velocity Warning:", self.velocity_warning_label)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()

        self.calculate_button = QtWidgets.QPushButton("Calculate")
        self.calculate_button.clicked.connect(self.calculate)
        button_layout.addWidget(self.calculate_button)

        button_layout.addStretch()

        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

        # Connect bullet selection change
        self.bullet_combo.currentIndexChanged.connect(self._on_bullet_selected)
        self.nose_type_combo.currentTextChanged.connect(self._on_nose_type_changed)
        self.tip_material_combo.currentTextChanged.connect(
            self._on_tip_material_changed
        )
        self._on_nose_type_changed(self.nose_type_combo.currentText())
        self._on_tip_material_changed(self.tip_material_combo.currentText())
        self._update_nose_tooltips()

        for spin in (
            self.diameter_spin,
            self.length_spin,
            self.hp_diameter_spin,
            self.hp_depth_spin,
            self.tip_length_spin,
            self.tip_base_diameter_spin,
            self.tip_tip_diameter_spin,
            self.velocity_spin,
        ):
            spin.valueChanged.connect(self._update_nose_tooltips)

    def _apply_velocity_units(self, set_default=False):
        """Set velocity spinbox range and suffix; optionally set default value."""
        if self._metric:
            self.velocity_spin.setRange(100.0, 1500.0)
            self.velocity_spin.setSuffix(" m/s")
            if set_default:
                self.velocity_spin.setValue(853.0)
        else:
            self.velocity_spin.setRange(300.0, 5000.0)
            self.velocity_spin.setSuffix(" fps")
            if set_default:
                self.velocity_spin.setValue(2800.0)
        self.velocity_spin.setDecimals(1)

    def _apply_temp_units(self, set_default=False):
        """Set temperature spinbox range and suffix; optionally set default value."""
        if self._metric:
            self.temp_spin.setRange(-40.0, 50.0)
            self.temp_spin.setSuffix(" °C")
            if set_default:
                self.temp_spin.setValue(15.0)
        else:
            self.temp_spin.setRange(-40.0, 120.0)
            self.temp_spin.setSuffix(" °F")
            if set_default:
                self.temp_spin.setValue(59.0)
        self.temp_spin.setDecimals(1)

    def _apply_pressure_units(self, set_default=False):
        """Set pressure spinbox range and suffix; optionally set default value."""
        if self._metric:
            self.pressure_spin.setRange(800.0, 1200.0)
            self.pressure_spin.setSuffix(" hPa")
            if set_default:
                self.pressure_spin.setValue(1013.25)
        else:
            self.pressure_spin.setRange(23.0, 35.0)
            self.pressure_spin.setSuffix(" inHg")
            if set_default:
                self.pressure_spin.setValue(29.92)
        self.pressure_spin.setDecimals(2)

    def _on_units_changed(self, index):
        """Convert current values and switch velocity/temp/pressure to new units."""
        new_metric = index == 0
        if new_metric == self._metric:
            return

        # Read current values in old units
        vel = self.velocity_spin.value()
        temp = self.temp_spin.value()
        press = self.pressure_spin.value()

        self._metric = new_metric
        _set_ballistic_units(self._metric)

        # Convert values
        if new_metric:
            vel = vel * FPS_TO_MPS
            temp = (temp - 32.0) * 5.0 / 9.0
            press = press * INHG_TO_HPA
        else:
            vel = vel / FPS_TO_MPS
            temp = temp * 9.0 / 5.0 + 32.0
            press = press / INHG_TO_HPA

        # Update range/suffix then set converted values
        self._apply_velocity_units(set_default=False)
        self._apply_temp_units(set_default=False)
        self._apply_pressure_units(set_default=False)
        self.velocity_spin.setValue(vel)
        self.temp_spin.setValue(temp)
        self.pressure_spin.setValue(press)

    def _populate_bullet_combo(self):
        """Populate bullet combo box with document objects."""
        self.bullet_combo.addItem("Manual Entry", None)

        if App.ActiveDocument:
            for obj in App.ActiveDocument.Objects:
                if hasattr(obj, "Proxy") and hasattr(obj.Proxy, "Type"):
                    if obj.Proxy.Type == "BulletFeature":
                        self.bullet_combo.addItem(obj.Label, obj)

    def _on_bullet_selected(self, index):
        """Called when bullet selection changes."""
        bullet_obj = self.bullet_combo.itemData(index)
        if bullet_obj:
            self._load_bullet_data(bullet_obj)

    def _on_nose_type_changed(self, nose_type_text):
        hp_enabled = nose_type_text in ("Hollow Point", "Hollow Point + Tip")
        tip_enabled = nose_type_text == "Hollow Point + Tip"
        for w in (self.hp_diameter_spin, self.hp_depth_spin, self.cavity_shape_combo):
            w.setEnabled(hp_enabled)
        for w in (
            self.tip_material_combo,
            self.tip_density_spin,
            self.tip_length_spin,
            self.tip_base_diameter_spin,
            self.tip_tip_diameter_spin,
        ):
            w.setEnabled(tip_enabled)
        self._update_nose_tooltips()

    def _on_tip_material_changed(self, material_name):
        material_db = get_material_database()
        self.tip_density_spin.setValue(material_db.get_tip_density(material_name, 1.32))
        self._update_nose_tooltips()

    def _update_nose_tooltips(self):
        """Update dynamic tooltips with calculated limits for current inputs."""
        diameter = self.diameter_spin.value()
        length = self.length_spin.value()
        hp_d = self.hp_diameter_spin.value()
        hp_depth = self.hp_depth_spin.value()
        velocity = self._get_velocity_mps()

        ogive_ratio = 7.0
        meplat_mm = 2.5
        material_density = get_material_database().get_density(
            self.material_combo.currentText()
        )
        bullet_obj = self.bullet_obj or (
            self.bullet_combo.itemData(self.bullet_combo.currentIndex())
            if self.bullet_combo.currentIndex() >= 0
            else None
        )
        if bullet_obj and hasattr(bullet_obj, "OgiveCaliberRatio"):
            ogive_ratio = float(bullet_obj.OgiveCaliberRatio)
        if bullet_obj and hasattr(bullet_obj, "MeplatDiameter"):
            try:
                meplat_prop = bullet_obj.MeplatDiameter
                if hasattr(meplat_prop, "getValueAs"):
                    meplat_mm = float(meplat_prop.getValueAs("mm").Value)
                elif hasattr(meplat_prop, "Value"):
                    meplat_mm = float(meplat_prop.Value)
                else:
                    meplat_mm = float(meplat_prop)
            except Exception:
                meplat_mm = 2.5
        if bullet_obj and hasattr(bullet_obj, "Density"):
            material_density = float(bullet_obj.Density)

        hp_depth_min, hp_depth_max = calculate_hp_depth_limits(diameter, ogive_ratio)
        body_length = max(
            0.0,
            length
            - (
                float(bullet_obj.BoatTailLength)
                if bullet_obj and hasattr(bullet_obj, "BoatTailLength")
                else 0.0
            ),
        )
        if body_length > 0:
            hp_depth_max = min(hp_depth_max, max(0.0, body_length - 0.001))

        min_wall = min_wall_thickness(material_density, velocity)
        hp_diam_max_meplat = max(0.0, meplat_mm - (2.0 * min_wall))
        hp_diam_max_effective = max(0.0, diameter - 0.001)
        hp_diam_max = min(hp_diam_max_meplat, hp_diam_max_effective)

        self.hp_diameter_spin.setToolTip(
            f"Maximum allowed: {hp_diam_max:.2f} mm "
            f"(meplat/wall and diameter limits at {velocity:.0f} m/s)."
        )
        self.hp_depth_spin.setToolTip(
            f"Recommended: {hp_depth_min:.2f}-{hp_depth_max:.2f} mm. "
            f"Maximum allowed: {hp_depth_max:.2f} mm."
        )

        tip_base_max = max(0.0, hp_d)
        tip_tip_max = max(0.0, tip_base_max - 0.001)
        self.tip_base_diameter_spin.setToolTip(
            f"Maximum allowed: {tip_base_max:.2f} mm (must be <= HP diameter)."
        )
        self.tip_tip_diameter_spin.setToolTip(
            f"Maximum allowed: {tip_tip_max:.2f} mm (must be < tip base diameter)."
        )

        ogive_length_mm = (ogive_ratio * diameter) / 2.0 if diameter > 0 else 0.0
        tip_length_max = max(
            0.0, (ogive_length_mm + 0.1) - ((hp_depth * 0.35) + 0.20)
        )
        self.tip_length_spin.setToolTip(
            f"Estimated maximum: {tip_length_max:.2f} mm "
            f"(assembly fit within ogive length +/- 0.1 mm)."
        )

    def _load_bullet_data(self, bullet_obj=None):
        """Load data from bullet object."""
        obj = bullet_obj or self.bullet_obj

        if obj and hasattr(obj, "Diameter"):
            self.diameter_spin.setValue(obj.Diameter)
            self.length_spin.setValue(obj.Length)
            self.weight_spin.setValue(
                obj.ActualWeight if obj.ActualWeight > 0 else obj.Weight
            )

            index = self.ogive_type_combo.findText(obj.OgiveType)
            if index >= 0:
                self.ogive_type_combo.setCurrentIndex(index)

            # Set material from bullet object
            if hasattr(obj, "Material"):
                material_index = self.material_combo.findText(obj.Material)
                if material_index >= 0:
                    self.material_combo.setCurrentIndex(material_index)
            if hasattr(obj, "NoseType"):
                mapping = {
                    "solid": "Solid",
                    "hp": "Hollow Point",
                    "hp_tip": "Hollow Point + Tip",
                }
                idx = self.nose_type_combo.findText(
                    mapping.get(str(obj.NoseType), "Solid")
                )
                if idx >= 0:
                    self.nose_type_combo.setCurrentIndex(idx)
            if hasattr(obj, "HPDiameter"):
                self.hp_diameter_spin.setValue(float(obj.HPDiameter))
            if hasattr(obj, "HPDepth"):
                self.hp_depth_spin.setValue(float(obj.HPDepth))
            if hasattr(obj, "CavityShape"):
                idx = self.cavity_shape_combo.findText(str(obj.CavityShape).lower())
                if idx >= 0:
                    self.cavity_shape_combo.setCurrentIndex(idx)
            if hasattr(obj, "TipLength"):
                self.tip_length_spin.setValue(float(obj.TipLength))
            if hasattr(obj, "TipBaseDiameter"):
                self.tip_base_diameter_spin.setValue(float(obj.TipBaseDiameter))
            if hasattr(obj, "TipTipDiameter"):
                self.tip_tip_diameter_spin.setValue(float(obj.TipTipDiameter))
            if hasattr(obj, "TipMaterial"):
                idx = self.tip_material_combo.findText(str(obj.TipMaterial))
                if idx >= 0:
                    self.tip_material_combo.setCurrentIndex(idx)
            if hasattr(obj, "TipDensity"):
                self.tip_density_spin.setValue(float(obj.TipDensity))

            # Select this bullet in combo
            for i in range(self.bullet_combo.count()):
                if self.bullet_combo.itemData(i) == obj:
                    self.bullet_combo.setCurrentIndex(i)
                    break

        # Calculate initial results
        self._update_nose_tooltips()
        self.calculate()

    def _get_velocity_mps(self):
        """Return velocity in m/s for calculations."""
        v = self.velocity_spin.value()
        return v if self._metric else (v * FPS_TO_MPS)

    def _get_temperature_c(self):
        """Return temperature in Celsius for calculations."""
        t = self.temp_spin.value()
        return t if self._metric else ((t - 32.0) * 5.0 / 9.0)

    def _get_pressure_hpa(self):
        """Return pressure in hPa for calculations."""
        p = self.pressure_spin.value()
        return p if self._metric else (p * INHG_TO_HPA)

    def calculate(self):
        """Perform ballistic calculations."""
        try:
            diameter = self.diameter_spin.value()
            length = self.length_spin.value()
            weight = self.weight_spin.value()
            ogive_type = self.ogive_type_combo.currentText()
            nose_type_text = self.nose_type_combo.currentText()
            nose_type = {
                "Solid": "solid",
                "Hollow Point": "hp",
                "Hollow Point + Tip": "hp_tip",
            }.get(nose_type_text, "solid")
            twist_rate = self.twist_spin.value()
            velocity = self._get_velocity_mps()
            temperature = self._get_temperature_c()
            pressure = self._get_pressure_hpa()
            hp_diameter = self.hp_diameter_spin.value()
            hp_depth = self.hp_depth_spin.value()
            cavity_shape = self.cavity_shape_combo.currentText()
            tip_length = self.tip_length_spin.value()
            tip_base_diameter = self.tip_base_diameter_spin.value()
            tip_tip_diameter = self.tip_tip_diameter_spin.value()
            tip_material = self.tip_material_combo.currentText()
            tip_density = self.tip_density_spin.value()
            ogive_caliber_ratio = 7.0
            boat_tail_angle_for_bc = 0.0
            boat_tail_length_for_bc = 0.0

            # Get effective diameter and material density
            effective_diameter = None
            material_density = None
            bullet_obj = self.bullet_obj or (
                self.bullet_combo.itemData(self.bullet_combo.currentIndex())
                if self.bullet_combo.currentIndex() >= 0
                else None
            )

            if bullet_obj:
                # Effective diameter currently follows nominal diameter.
                if hasattr(bullet_obj, "LandRiding") and bullet_obj.LandRiding:
                    effective_diameter = diameter
                else:
                    effective_diameter = diameter

                # Get material density from bullet object
                if hasattr(bullet_obj, "Density"):
                    material_density = float(bullet_obj.Density)
                if hasattr(bullet_obj, "OgiveCaliberRatio"):
                    ogive_caliber_ratio = float(bullet_obj.OgiveCaliberRatio)
                if hasattr(bullet_obj, "BoatTailAngle"):
                    boat_tail_angle_for_bc = float(bullet_obj.BoatTailAngle)
                if hasattr(bullet_obj, "BoatTailLength"):
                    boat_tail_length_for_bc = float(bullet_obj.BoatTailLength)
            else:
                # No bullet object selected - use material from combo box
                material_db = get_material_database()
                selected_material = self.material_combo.currentText()
                material_density = material_db.get_density(selected_material)

            meplat_mm = 2.5
            if bullet_obj and hasattr(bullet_obj, "MeplatDiameter"):
                try:
                    meplat_prop = bullet_obj.MeplatDiameter
                    if hasattr(meplat_prop, "getValueAs"):
                        meplat_mm = float(meplat_prop.getValueAs("mm").Value)
                    elif hasattr(meplat_prop, "Value"):
                        meplat_mm = float(meplat_prop.Value)
                    else:
                        meplat_mm = float(meplat_prop)
                except Exception:
                    meplat_mm = 2.5

            # Nose validation
            body_length = max(
                0.0,
                length
                - (
                    float(bullet_obj.BoatTailLength)
                    if bullet_obj and hasattr(bullet_obj, "BoatTailLength")
                    else 0.0
                ),
            )
            if nose_type in ("hp", "hp_tip"):
                if hp_diameter >= diameter:
                    raise ValueError(
                        "HP diameter must be less than effective diameter."
                    )
                if hp_depth >= body_length and body_length > 0:
                    raise ValueError("HP depth must be less than body length.")
                hp_depth_min, hp_depth_max = calculate_hp_depth_limits(
                    diameter_mm=diameter,
                    ogive_caliber_ratio=ogive_caliber_ratio,
                )
                if hp_depth_max > 0 and hp_depth > hp_depth_max:
                    raise ValueError(
                        f"ERROR: HP depth {hp_depth:.2f} mm exceeds practical ogive "
                        f"limit {hp_depth_max:.2f} mm. Recommended range is "
                        f"{hp_depth_min:.2f}-{hp_depth_max:.2f} mm."
                    )
                hp_msg = validate_hp_diameter(
                    meplat_mm=meplat_mm,
                    hp_diameter_mm=hp_diameter,
                    material_density_gcm3=(
                        material_density if material_density else 8.86
                    ),
                    velocity_ms=velocity,
                )
                if hp_msg:
                    raise ValueError(hp_msg)
            if nose_type == "hp_tip":
                if tip_base_diameter > hp_diameter:
                    raise ValueError("Tip base diameter must be <= HP diameter.")
                if (
                    tip_tip_diameter >= tip_base_diameter
                    and tip_base_diameter > 0
                ):
                    raise ValueError("Tip tip diameter must be < tip base diameter.")
                if velocity > 1300.0:
                    raise ValueError("Velocity must be <= 1300 m/s.")
                tip_data = get_material_database().get_tip_material(tip_material)
                if tip_data and tip_data.get("category") in ("Geometry Only", "Prototype"):
                    raise ValueError(
                        f"{tip_data.get('category')} tip materials are blocked for "
                        "live-fire calculations."
                    )
                ogive_length_mm = (ogive_caliber_ratio * diameter) / 2.0
                tip_validation = validate_tip_design(
                    meplat_mm=meplat_mm,
                    hp_depth_mm=hp_depth,
                    ogive_length_mm=ogive_length_mm,
                    tip_length_mm=tip_length,
                    tip_base_diameter_mm=tip_base_diameter,
                    tip_tip_diameter_mm=tip_tip_diameter,
                    tip_material_name=tip_material,
                )
                if tip_validation["errors"]:
                    raise ValueError(tip_validation["errors"][0])
            else:
                tip_validation = {"warnings": []}

            nose_result = calculate_nose_configuration(
                nose_type=nose_type,
                original_mass_grains=weight,
                length_mm=length,
                d_effective_mm=(
                    effective_diameter if effective_diameter else diameter
                ),
                bullet_density_gcm3=(
                    material_density if material_density else 8.86
                ),
                hp_diameter_mm=hp_diameter,
                hp_depth_mm=hp_depth,
                cavity_shape=cavity_shape,
                tip_length_mm=tip_length,
                tip_base_diameter_mm=tip_base_diameter,
                tip_tip_diameter_mm=tip_tip_diameter,
                tip_density_gcm3=tip_density,
                body_length_mm=body_length,
            )

            # Calculate stability
            App.Console.PrintMessage("Ballistic Calculator inputs:\n")
            App.Console.PrintMessage(f"  Diameter: {diameter:.2f} mm\n")
            if effective_diameter and abs(effective_diameter - diameter) > 0.01:
                App.Console.PrintMessage(
                    f"  Effective Diameter: {effective_diameter:.2f} mm (bearing bands)\n"
                )
            App.Console.PrintMessage(f"  Length: {length:.2f} mm\n")
            App.Console.PrintMessage(f"  Weight: {weight:.2f} grains\n")
            if material_density:
                App.Console.PrintMessage(
                    f"  Material Density: {material_density:.2f} g/cm³\n"
                )
            App.Console.PrintMessage(f"  Twist: {twist_rate:.2f} inches\n")
            App.Console.PrintMessage(
                f"  Velocity: {velocity:.2f} m/s\n"
            )
            App.Console.PrintMessage(f"  Temperature: {temperature:.2f} °C\n")
            App.Console.PrintMessage(f"  Pressure: {pressure:.2f} hPa\n")

            stability, threshold = calculate_stability_factor_miller(
                diameter,
                length,
                weight,
                twist_rate,
                velocity,
                temperature,
                pressure,
                effective_diameter_mm=effective_diameter,
                material_density_g_per_cm3=material_density,
                l_effective_calibers=nose_result["l_effective_calibers"],
                corrected_mass_grains=nose_result["corrected_mass_grains"],
            )

            App.Console.PrintMessage(f"  Calculated stability: {stability:.4f}\n")
            threshold_type = "Monolithic copper/brass" if threshold >= 1.8 else "Lead-core"
            App.Console.PrintMessage(
                f"  Stability threshold: {threshold:.2f} ({threshold_type})\n"
            )
            self.stability_label.setText(f"{stability:.2f}")

            # Stability status using correct threshold
            if stability >= threshold:
                status = "Stable (Good)"
                color = "green"
            elif (
                stability >= threshold * 0.67
            ):  # ~1.0 for lead-core, ~1.2 for monolithic
                status = "Marginally Stable"
                color = "orange"
            else:
                status = "Unstable"
                color = "red"

            status_check = stability >= threshold
            App.Console.PrintMessage(
                f"  Status: {status} "
                f"(threshold check: {stability:.4f} >= {threshold:.2f} = {status_check})\n"
            )

            self.stability_status_label.setText(status)
            self.stability_status_label.setStyleSheet(f"color: {color}")

            # Calculate BC
            bc = calculate_ballistic_coefficient_g1(
                diameter,
                nose_result["corrected_mass_grains"],
                length,
                ogive_type,
                nose_type=nose_type,
                hp_diameter_mm=hp_diameter,
                effective_diameter_mm=effective_diameter,
                velocity_mps=velocity,
                temperature_c=temperature,
                pressure_hpa=pressure,
                ogive_caliber_ratio=ogive_caliber_ratio,
                boat_tail_angle_deg=boat_tail_angle_for_bc,
                boat_tail_length_mm=boat_tail_length_for_bc,
                meplat_diameter_mm=meplat_mm,
            )
            self.bc_label.setText(f"{bc:.3f}")

            # Calculate SD
            sd = calculate_sectional_density(diameter, weight)
            self.sd_label.setText(f"{sd:.3f}")

            # Calculate recommended twist (with Miller temp/pressure correction)
            twist_rate, twist_str = calculate_recommended_twist_rate(
                diameter,
                length,
                weight,
                velocity,
                effective_diameter_mm=effective_diameter,
                material_density_g_per_cm3=material_density,
                temperature_c=temperature,
                pressure_hpa=pressure,
            )
            self.recommended_twist_label.setText(twist_str)

            # Extended nose/tip results
            self.mass_removed_label.setText(f"{nose_result['mass_removed_grains']:.2f}")
            self.mass_added_label.setText(f"{nose_result['mass_added_grains']:.2f}")
            self.corrected_mass_label.setText(
                f"{nose_result['corrected_mass_grains']:.2f}"
            )
            ff_base = {"Tangent": 0.85, "Secant": 0.80, "Elliptical": 0.75}.get(
                ogive_type, 0.85
            )
            ff_used = ff_base
            if nose_type == "hp" and effective_diameter and effective_diameter > 0:
                ff_used = ff_base * (
                    1.0 + 0.15 * ((hp_diameter / effective_diameter) ** 2)
                )
            self.form_factor_label.setText(
                f"{ff_used:.3f} (HP penalty: {'yes' if nose_type == 'hp' else 'no'})"
            )
            meplat_used = (
                nose_result["effective_meplat_mm"]
                if nose_result["effective_meplat_mm"] > 0
                else 0.0
            )
            self.meplat_used_label.setText(f"{meplat_used:.3f}")
            self.corrected_l_label.setText(f"{nose_result['l_effective_calibers']:.3f}")

            if nose_type == "hp_tip":
                tip_data = get_material_database().get_tip_material(tip_material)
                max_vel = float(tip_data.get("max_velocity_ms", 0)) if tip_data else 0.0
                self.tip_velocity_label.setText(
                    f"{tip_material}: {max_vel:.0f} m/s vs {velocity:.0f} m/s"
                )
                severity, warning_msg = check_tip_velocity_limit(tip_material, velocity)
                if tip_validation["warnings"]:
                    self.velocity_warning_label.setStyleSheet("color: #b26a00;")
                    self.velocity_warning_label.setText(tip_validation["warnings"][0])
                elif severity == "ERROR":
                    self.velocity_warning_label.setStyleSheet("color: #b00020;")
                    self.velocity_warning_label.setText(warning_msg)
                elif severity == "WARNING":
                    self.velocity_warning_label.setStyleSheet("color: #b26a00;")
                    self.velocity_warning_label.setText(warning_msg)
                else:
                    self.velocity_warning_label.setStyleSheet("color: #1b7f3a;")
                    self.velocity_warning_label.setText("OK")
            else:
                self.tip_velocity_label.setText("N/A")
                self.velocity_warning_label.setText("")

        except Exception as e:
            App.Console.PrintError(f"Error calculating ballistics: {e}\n")


class BallisticCalculatorCommand:
    """
    Command to open ballistic calculator.
    """

    def __init__(self):
        """Initialize the command."""
        wb_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.resources = {
            "Pixmap": os.path.join(wb_path, "Resources", "icons", "Calculator.svg"),
            "MenuText": "Ballistic Calculator",
            "ToolTip": "Calculate ballistic properties and stability",
            "Accel": "C",
        }

    def GetResources(self):
        """Return command resources."""
        return self.resources

    def IsActive(self):
        """Check if command is active."""
        return True

    def Activated(self):
        """Execute the command."""
        # Try to get selected bullet
        bullet_obj = None
        if App.ActiveDocument and Gui.Selection.getSelection():
            sel = Gui.Selection.getSelection()[0]
            if hasattr(sel, "Proxy") and hasattr(sel.Proxy, "Type"):
                if sel.Proxy.Type == "BulletFeature":
                    bullet_obj = sel

        # Open dialog
        dialog = BallisticCalculatorDialog(bullet_obj)
        dialog.exec_()


# Register command (only if Gui is available)
try:
    Gui.addCommand("BulletDesigner_BallisticCalculator", BallisticCalculatorCommand())
except Exception as e:
    App.Console.PrintError(f"Failed to register BallisticCalculator command: {e}\n")
