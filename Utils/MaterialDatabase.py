"""
Material database for bullet design.

This module loads and manages material properties for bullet design.
"""

import json
import os
import FreeCAD as App
from typing import Dict, List, Optional


class MaterialDatabase:
    """
    Database of bullet materials with properties.
    """

    def __init__(self):
        """Initialize the material database."""
        self.materials = {}
        self.tip_materials = {}
        self._load_materials()
        self._create_default_tip_materials()

    def _load_materials(self):
        """Load materials from JSON file."""
        try:
            wb_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            materials_file = os.path.join(wb_path, "Data", "materials.json")

            if os.path.exists(materials_file):
                with open(materials_file, "r") as f:
                    data = json.load(f)
                    for material in data.get("materials", []):
                        name = material.get("name")
                        if name:
                            self.materials[name] = {
                                "name": name,
                                "density": material.get("density", 8.86),
                                "color": material.get("color", [0.8, 0.5, 0.2]),
                                "description": material.get("description", ""),
                            }
            else:
                App.Console.PrintWarning(
                    f"Materials file not found: {materials_file}\n"
                )
                # Use default materials
                self._create_default_materials()
        except Exception as e:
            App.Console.PrintError(f"Error loading materials: {e}\n")
            self._create_default_materials()

    def _create_default_materials(self):
        """Create default materials if file cannot be loaded."""
        default_materials = [
            {
                "name": "Gilding Metal (95/5)",
                "density": 8.86,
                "color": [0.80, 0.50, 0.20],
                "description": "95% copper, 5% zinc",
            },
            {
                "name": "Pure Copper",
                "density": 8.96,
                "color": [0.72, 0.45, 0.20],
                "description": "Pure copper",
            },
            {
                "name": "Lead Core",
                "density": 11.34,
                "color": [0.40, 0.40, 0.40],
                "description": "Pure lead",
            },
        ]

        for material in default_materials:
            self.materials[material["name"]] = material

    def get_material(self, name: str) -> Optional[Dict]:
        """
        Get material properties by name.

        Args:
            name: Material name

        Returns:
            Material dictionary or None if not found
        """
        return self.materials.get(name)

    def get_material_names(self) -> List[str]:
        """
        Get list of all material names.

        Returns:
            List of material names
        """
        return sorted(self.materials.keys())

    def get_density(self, material_name: str) -> float:
        """
        Get density for a material.

        Args:
            material_name: Name of the material

        Returns:
            Density in g/cm³, or default 8.86 if not found
        """
        material = self.materials.get(material_name)
        if material:
            return material["density"]
        return 8.86  # Default to gilding metal density

    def get_color(self, material_name: str) -> List[float]:
        """
        Get color for a material.

        Args:
            material_name: Name of the material

        Returns:
            RGB color tuple [R, G, B] in range 0-1
        """
        material = self.materials.get(material_name)
        if material:
            return material["color"]
        return [0.8, 0.5, 0.2]  # Default copper color

    def add_custom_material(
        self, name: str, density: float, color: List[float], description: str = ""
    ):
        """
        Add a custom material to the database.

        Args:
            name: Material name
            density: Density in g/cm³
            color: RGB color [R, G, B] in range 0-1
            description: Optional description
        """
        self.materials[name] = {
            "name": name,
            "density": density,
            "color": color,
            "description": description,
        }

    def _create_default_tip_materials(self):
        """Create built-in ballistic tip material database."""
        entries = [
            {
                "name": "PEEK",
                "density_gcm3": 1.32,
                "max_temp_C": 250,
                "max_velocity_ms": 1300,
                "category": "Functional",
                "printer_req": None,
                "note": "Best all-round. Recommended default for V > 1000 m/s.",
            },
            {
                "name": "Torlon (PAI)",
                "density_gcm3": 1.40,
                "max_temp_C": 280,
                "max_velocity_ms": 1300,
                "category": "Functional",
                "printer_req": None,
                "note": "Best thermal resistance. Slightly brittle.",
            },
            {
                "name": "Ultem (PEI)",
                "density_gcm3": 1.27,
                "max_temp_C": 217,
                "max_velocity_ms": 1100,
                "category": "Functional",
                "printer_req": None,
                "note": "Cost-effective. Warn if V > 1100 m/s.",
            },
            {
                "name": "Delrin (POM)",
                "density_gcm3": 1.41,
                "max_temp_C": 120,
                "max_velocity_ms": 600,
                "category": "Functional",
                "printer_req": None,
                "note": "Low velocity only. Warn if V > 600 m/s.",
            },
            {
                "name": "Aluminium 6061",
                "density_gcm3": 2.70,
                "max_temp_C": 999,
                "max_velocity_ms": 1300,
                "category": "Functional",
                "printer_req": None,
                "note": "Metal tip. No thermal limit. Higher CG shift than polymers.",
            },
            {
                "name": "PEEK (3D Printed)",
                "density_gcm3": 1.32,
                "max_temp_C": 240,
                "max_velocity_ms": 1300,
                "category": "Functional",
                "printer_req": "Hotend >= 380C, heated chamber >= 120C",
                "note": "100% infill required. Slightly lower strength than machined PEEK.",
            },
            {
                "name": "Ultem 9085 (3D Printed)",
                "density_gcm3": 1.34,
                "max_temp_C": 210,
                "max_velocity_ms": 1100,
                "category": "Functional",
                "printer_req": "Hotend >= 360C, heated chamber required",
                "note": "Warn if V > 1100 m/s.",
            },
            {
                "name": "PA12-CF (3D Printed)",
                "density_gcm3": 1.05,
                "max_temp_C": 180,
                "max_velocity_ms": 900,
                "category": "Functional",
                "printer_req": "Hotend >= 280C, hardened nozzle required",
                "note": "Lightest printable option. Warn if V > 900 m/s.",
            },
            {
                "name": "PETG (3D Printed)",
                "density_gcm3": 1.27,
                "max_temp_C": 80,
                "max_velocity_ms": 300,
                "category": "Prototype",
                "printer_req": "Standard FDM, hotend 230-250C",
                "note": "Dimensional prototyping only. NO live fire above 300 m/s.",
            },
            {
                "name": "PLA",
                "density_gcm3": 1.24,
                "max_temp_C": 60,
                "max_velocity_ms": 0,
                "category": "Geometry Only",
                "printer_req": "Any FDM printer",
                "note": "NO live fire under any circumstances. Geometry verification only.",
            },
            {
                "name": "Resin SLA (Standard)",
                "density_gcm3": 1.15,
                "max_temp_C": 60,
                "max_velocity_ms": 0,
                "category": "Geometry Only",
                "printer_req": "SLA/MSLA printer",
                "note": "NO live fire. Excellent dimensional accuracy for cavity fit checking.",
            },
            {
                "name": "Resin SLA (High Temp)",
                "density_gcm3": 1.18,
                "max_temp_C": 120,
                "max_velocity_ms": 400,
                "category": "Prototype",
                "printer_req": "SLA/MSLA printer",
                "note": "Very low velocity functional testing only. Warn if V > 400 m/s.",
            },
        ]
        for entry in entries:
            self.tip_materials[entry["name"]] = entry

    def get_tip_material_names(self) -> List[str]:
        """Return ballistic tip material names."""
        return sorted(self.tip_materials.keys())

    def get_tip_material(self, name: str) -> Optional[Dict]:
        """Return tip material metadata by name."""
        return self.tip_materials.get(name)

    def get_tip_density(self, name: str, default: float = 1.32) -> float:
        """Return tip material density in g/cm3."""
        material = self.get_tip_material(name)
        if material:
            return float(material.get("density_gcm3", default))
        return default


# Global instance
_material_db = None


def get_material_database() -> MaterialDatabase:
    """
    Get the global material database instance.

    Returns:
        MaterialDatabase instance
    """
    global _material_db
    if _material_db is None:
        _material_db = MaterialDatabase()
    return _material_db
