"""
Measurement system for astronomical image analysis.
Supports line, circle, and ellipse measurements with data storage and visualization.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
import uuid


@dataclass
class Measurement:
    """Base class for all measurement types."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    measurement_type: str = ""
    image_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    notes: str = ""
    color: str = "red"
    visible: bool = True

    def get_display_info(self) -> Dict[str, Any]:
        """Return dictionary of measurement info for display in table."""
        return {
            "ID": self.id[:8],
            "Type": self.measurement_type,
            "Image": self.image_name,
            "Time": self.timestamp.strftime("%H:%M:%S"),
        }

    def get_coords(self) -> List[Tuple[float, float]]:
        """Return list of key coordinates for this measurement."""
        return []

    def draw(self, image_array: np.ndarray, zoom: float, offset_x: float, offset_y: float,
             xy_to_canvas_func) -> List[Tuple[str, Any]]:
        """
        Return list of drawing instructions for canvas.
        Each instruction is a tuple of (shape_type, params_dict)
        """
        return []


@dataclass
class LineMeasurement(Measurement):
    """Line measurement between two points."""
    start: Tuple[float, float] = (0, 0)
    end: Tuple[float, float] = (0, 0)
    pixel_values: np.ndarray = field(default_factory=lambda: np.array([]))

    def __post_init__(self):
        self.measurement_type = "Line"

    def get_length(self) -> float:
        """Calculate Euclidean distance between start and end points."""
        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        return np.sqrt(dx**2 + dy**2)

    def get_display_info(self) -> Dict[str, Any]:
        info = super().get_display_info()
        info.update({
            "Start": f"({self.start[0]:.1f}, {self.start[1]:.1f})",
            "End": f"({self.end[0]:.1f}, {self.end[1]:.1f})",
            "Length": f"{self.get_length():.2f} px",
        })
        return info

    def get_coords(self) -> List[Tuple[float, float]]:
        return [self.start, self.end]

    def draw(self, image_array: np.ndarray, zoom: float, offset_x: float, offset_y: float,
             xy_to_canvas_func) -> List[Tuple[str, Any]]:
        """Draw line on canvas."""
        x1_canvas, y1_canvas = xy_to_canvas_func(self.start[0], self.start[1])
        x2_canvas, y2_canvas = xy_to_canvas_func(self.end[0], self.end[1])

        return [
            ("line", {
                "coords": (x1_canvas, y1_canvas, x2_canvas, y2_canvas),
                "fill": self.color,
                "width": 2
            }),
            ("oval", {
                "coords": (x1_canvas-3, y1_canvas-3, x1_canvas+3, y1_canvas+3),
                "fill": self.color,
                "outline": self.color
            }),
            ("oval", {
                "coords": (x2_canvas-3, y2_canvas-3, x2_canvas+3, y2_canvas+3),
                "fill": self.color,
                "outline": self.color
            })
        ]


@dataclass
class CircleMeasurement(Measurement):
    """Circle measurement with center and radius."""
    center: Tuple[float, float] = (0, 0)
    radius: float = 0.0
    pixel_values: np.ndarray = field(default_factory=lambda: np.array([]))
    interior_count: int = 0  # Number of pixels inside circle
    interior_sum: float = 0.0  # Sum of pixel values inside circle
    interior_mean: float = 0.0  # Mean of pixel values inside circle

    def __post_init__(self):
        self.measurement_type = "Circle"

    def get_circumference(self) -> float:
        """Calculate circumference."""
        return 2 * np.pi * self.radius

    def get_area(self) -> float:
        """Calculate area."""
        return np.pi * self.radius**2

    def get_display_info(self) -> Dict[str, Any]:
        info = super().get_display_info()
        info.update({
            "Center": f"({self.center[0]:.1f}, {self.center[1]:.1f})",
            "Radius": f"{self.radius:.2f} px",
            "Circumference": f"{self.get_circumference():.2f} px",
            "Area": f"{self.get_area():.2f} px²",
            "Count": str(self.interior_count),
            "Sum": f"{self.interior_sum:.2f}",
            "Mean": f"{self.interior_mean:.2f}",
        })
        return info

    def get_coords(self) -> List[Tuple[float, float]]:
        return [self.center]

    def draw(self, image_array: np.ndarray, zoom: float, offset_x: float, offset_y: float,
             xy_to_canvas_func) -> List[Tuple[str, Any]]:
        """Draw circle on canvas."""
        cx_canvas, cy_canvas = xy_to_canvas_func(self.center[0], self.center[1])

        # Calculate radius in canvas coordinates
        # Use a point on the circle to determine canvas radius
        edge_x = self.center[0] + self.radius
        edge_y = self.center[1]
        ex_canvas, ey_canvas = xy_to_canvas_func(edge_x, edge_y)
        canvas_radius = abs(ex_canvas - cx_canvas)

        return [
            ("oval", {
                "coords": (cx_canvas - canvas_radius, cy_canvas - canvas_radius,
                          cx_canvas + canvas_radius, cy_canvas + canvas_radius),
                "outline": self.color,
                "width": 2
            }),
            ("oval", {
                "coords": (cx_canvas-3, cy_canvas-3, cx_canvas+3, cy_canvas+3),
                "fill": self.color,
                "outline": self.color
            })
        ]


@dataclass
class EllipseMeasurement(Measurement):
    """Ellipse measurement with center, axes, and rotation."""
    center: Tuple[float, float] = (0, 0)
    semi_major: float = 0.0
    semi_minor: float = 0.0
    rotation: float = 0.0  # Rotation angle in radians
    pixel_values: np.ndarray = field(default_factory=lambda: np.array([]))
    interior_count: int = 0  # Number of pixels inside ellipse
    interior_sum: float = 0.0  # Sum of pixel values inside ellipse
    interior_mean: float = 0.0  # Mean of pixel values inside ellipse

    def __post_init__(self):
        self.measurement_type = "Ellipse"

    def get_area(self) -> float:
        """Calculate area."""
        return np.pi * self.semi_major * self.semi_minor

    def get_eccentricity(self) -> float:
        """Calculate eccentricity."""
        if self.semi_major == 0:
            return 0
        return np.sqrt(1 - (self.semi_minor**2 / self.semi_major**2))

    def get_display_info(self) -> Dict[str, Any]:
        info = super().get_display_info()
        info.update({
            "Center": f"({self.center[0]:.1f}, {self.center[1]:.1f})",
            "Semi-major": f"{self.semi_major:.2f} px",
            "Semi-minor": f"{self.semi_minor:.2f} px",
            "Rotation": f"{np.degrees(self.rotation):.1f}°",
            "Area": f"{self.get_area():.2f} px²",
            "Eccentricity": f"{self.get_eccentricity():.3f}",
            "Count": str(self.interior_count),
            "Sum": f"{self.interior_sum:.2f}",
            "Mean": f"{self.interior_mean:.2f}",
        })
        return info

    def get_coords(self) -> List[Tuple[float, float]]:
        return [self.center]

    def draw(self, image_array: np.ndarray, zoom: float, offset_x: float, offset_y: float,
             xy_to_canvas_func) -> List[Tuple[str, Any]]:
        """Draw ellipse on canvas as a polygon approximation."""
        # Generate points along the ellipse
        theta = np.linspace(0, 2*np.pi, 100)

        # Ellipse in local coordinates
        x_local = self.semi_major * np.cos(theta)
        y_local = self.semi_minor * np.sin(theta)

        # Rotate
        cos_rot = np.cos(self.rotation)
        sin_rot = np.sin(self.rotation)
        x_rotated = x_local * cos_rot - y_local * sin_rot
        y_rotated = x_local * sin_rot + y_local * cos_rot

        # Translate to center
        x_img = x_rotated + self.center[0]
        y_img = y_rotated + self.center[1]

        # Convert to canvas coordinates
        canvas_points = []
        for xi, yi in zip(x_img, y_img):
            xc, yc = xy_to_canvas_func(xi, yi)
            canvas_points.extend([xc, yc])

        cx_canvas, cy_canvas = xy_to_canvas_func(self.center[0], self.center[1])

        return [
            ("polygon", {
                "coords": canvas_points,
                "outline": self.color,
                "fill": "",
                "width": 2
            }),
            ("oval", {
                "coords": (cx_canvas-3, cy_canvas-3, cx_canvas+3, cy_canvas+3),
                "fill": self.color,
                "outline": self.color
            })
        ]


class MeasurementManager:
    """Manages collection of measurements for an image viewing session."""

    def __init__(self):
        self.measurements: List[Measurement] = []
        self.selected_measurement: Optional[Measurement] = None

    def add_measurement(self, measurement: Measurement) -> str:
        """Add a measurement and return its ID."""
        self.measurements.append(measurement)
        return measurement.id

    def remove_measurement(self, measurement_id: str) -> bool:
        """Remove a measurement by ID. Returns True if found and removed."""
        for i, m in enumerate(self.measurements):
            if m.id == measurement_id:
                if self.selected_measurement and self.selected_measurement.id == measurement_id:
                    self.selected_measurement = None
                del self.measurements[i]
                return True
        return False

    def get_measurement(self, measurement_id: str) -> Optional[Measurement]:
        """Get a measurement by ID."""
        for m in self.measurements:
            if m.id == measurement_id:
                return m
        return None

    def get_measurements_for_image(self, image_name: str) -> List[Measurement]:
        """Get all measurements for a specific image."""
        return [m for m in self.measurements if m.image_name == image_name]

    def get_visible_measurements(self, image_name: Optional[str] = None) -> List[Measurement]:
        """Get all visible measurements, optionally filtered by image."""
        if image_name:
            return [m for m in self.measurements if m.visible and m.image_name == image_name]
        return [m for m in self.measurements if m.visible]

    def clear_all(self):
        """Remove all measurements."""
        self.measurements.clear()
        self.selected_measurement = None

    def select_measurement(self, measurement_id: str):
        """Select a measurement by ID."""
        self.selected_measurement = self.get_measurement(measurement_id)

    def toggle_visibility(self, measurement_id: str):
        """Toggle visibility of a measurement."""
        measurement = self.get_measurement(measurement_id)
        if measurement:
            measurement.visible = not measurement.visible

    def export_to_dict(self) -> List[Dict[str, Any]]:
        """Export all measurements to a list of dictionaries."""
        return [m.get_display_info() for m in self.measurements]

    def calculate_residual(self, measurement1_id: str, measurement2_id: str) -> Optional[np.ndarray]:
        """
        Calculate residual between two measurements.
        For now, only supports comparing measurements of the same type with pixel values.
        Returns difference array or None if incompatible.
        """
        m1 = self.get_measurement(measurement1_id)
        m2 = self.get_measurement(measurement2_id)

        if not m1 or not m2:
            return None

        if m1.measurement_type != m2.measurement_type:
            return None

        # For measurements with pixel values
        if hasattr(m1, 'pixel_values') and hasattr(m2, 'pixel_values'):
            pv1 = m1.pixel_values
            pv2 = m2.pixel_values

            if len(pv1) == 0 or len(pv2) == 0:
                return None

            # Handle different lengths by using minimum length
            min_len = min(len(pv1), len(pv2))
            return pv1[:min_len] - pv2[:min_len]

        return None
