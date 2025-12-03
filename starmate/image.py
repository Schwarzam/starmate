from astropy.io import fits
from astropy.wcs import WCS

import numpy as np

from PIL import Image, ImageDraw, ImageTk
from skimage.draw import line, circle_perimeter, ellipse_perimeter

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from starmate.variables import colors
from starmate.measurements import LineMeasurement, CircleMeasurement, EllipseMeasurement

from logpool import control

class FitsImage:

    def __init__(self, image_data, header, manager, name = None):
        self.manager = manager
        self.name = name
        
        self.image_data = image_data
        self.header = header

        self.wcs_info = WCS(header, naxis=2)

        # Control variables for zooming and panning
        self.zoom_level = 1.0
        self.pan_start_x = 0
        self.pan_start_y = 0

        self.offset_x = 0
        self.offset_y = 0

        self.cached_img_data = None

        # Legacy line drawing (keeping for backwards compatibility)
        self.line_start = None
        self.line_end = None
        self.line_id = None

        # New measurement system variables
        self.measurement_mode = None  # Can be 'line', 'circle', 'ellipse', or None
        self.temp_measurement_points = []  # Temporary points during measurement creation

        self.plot_frame = None
        self.plot_canvas = None

    def update_image_cache(self, pmin=0, pmax=100):
        """Update the cached image based on pmin and pmax values."""

        try:
            pmin = float(pmin)
            pmax = float(pmax)
        except ValueError:
            print("Invalid pmin or pmax value")
            return

        if pmin >= pmax:
            pmax = pmin + 1

        # Cache processed data once
        vmin, vmax = np.percentile(self.image_data, [pmin, pmax])
        img_data = np.clip(self.image_data, vmin, vmax)
        img_data = ((img_data - vmin) / (vmax - vmin) * 255).astype(np.uint8)
        self.cached_img_data = img_data  # Store in cache
        print("Image cache updated")

    def update_display_image(self, image_canvas):
        """Efficiently update the display by only rendering the visible portion of the image."""
        if self.cached_img_data is None:
            return  # If no cache is available, skip

        # Calculate visible area based on offsets and zoom level
        x_start = max(int(self.offset_x / self.zoom_level), 0)
        y_start = max(int(self.offset_y / self.zoom_level), 0)
        visible_width = int(image_canvas.winfo_width() / self.zoom_level)
        visible_height = int(image_canvas.winfo_height() / self.zoom_level)

        # Ensure the cropped area doesn't exceed image bounds
        width = min(visible_width, self.cached_img_data.shape[1] - x_start)
        height = min(visible_height, self.cached_img_data.shape[0] - y_start)

        # Crop and resize only the visible portion of the image
        cropped_data = self.cached_img_data[
            y_start : y_start + height, x_start : x_start + width
        ]
        display_img = Image.fromarray(cropped_data).convert("RGB").resize(
            (int(width * self.zoom_level), int(height * self.zoom_level)), Image.NEAREST
        )

        # Create drawing context
        draw = ImageDraw.Draw(display_img)

        if self.manager.viewer.coords_frozen:
            # Draw the crosshair at the center of the canvas
            x_image = self.manager.viewer.labels["x"][1].cget("text")
            y_image = self.manager.viewer.labels["y"][1].cget("text")

            # Only draw if coordinates are valid (not 'N/A')
            if x_image != 'N/A' and y_image != 'N/A':
                try:
                    frozen_x, frozen_y = self.xy_to_canvas(x_image, y_image)
                    draw.circle(
                        (frozen_x, frozen_y), 10, outline=colors.accent, width=3
                    )
                except (ValueError, TypeError):
                    pass  # Skip drawing if conversion fails

        # Draw the legacy line if start and end points are set
        if self.line_start and self.line_end:
            # Calculate line coordinates relative to the current view
            start_x = (self.line_start[0] - x_start) * self.zoom_level
            start_y = (self.line_start[1] - y_start) * self.zoom_level
            end_x = (self.line_end[0] - x_start) * self.zoom_level
            end_y = (self.line_end[1] - y_start) * self.zoom_level

            # Draw the line in red
            draw.line((start_x, start_y, end_x, end_y), fill="red", width=2)

        # Draw all measurements from the new measurement system
        if hasattr(self.manager, 'measurement_manager'):
            self.draw_measurements(draw, x_start, y_start)

        # Display the image with all overlays
        tk_img = ImageTk.PhotoImage(
            display_img
        )  # Keep reference to avoid garbage collection
        return tk_img
    
    def xy_to_canvas(self, x_image, y_image):
        """Convert image coordinates to canvas coordinates."""
        x_image = float(x_image)
        y_image = float(y_image)
        x_canvas = (x_image * self.zoom_level) - self.offset_x
        y_canvas = (y_image * self.zoom_level) - self.offset_y
        return x_canvas, y_canvas
    
    def get_canvas_mouse_pos(self):
        """Get the mouse position on the canvas."""
        x_canvas = self.manager.viewer.image_canvas.winfo_pointerx() - self.manager.viewer.image_canvas.winfo_rootx()
        y_canvas = self.manager.viewer.image_canvas.winfo_pointery() - self.manager.viewer.image_canvas.winfo_rooty()
        
        return x_canvas, y_canvas
    
    def get_canvas_center_pos(self):
        # Get the center of the canvas
        canvas_width = self.manager.viewer.image_canvas.winfo_width()
        canvas_height = self.manager.viewer.image_canvas.winfo_height()
        center_x = canvas_width / 2
        center_y = canvas_height / 2
        
        return center_x, center_y

    def canvas_pos_to_xy(self, x_canvas, y_canvas):
        """Convert canvas coordinates to image coordinates."""
        x_image = (x_canvas + self.offset_x) / self.zoom_level
        y_image = (y_canvas + self.offset_y) / self.zoom_level
        
        return x_image, y_image
    
    def get_image_xy_mouse(self):
        """Get the image coordinates of the mouse position on the canvas."""
        x_canvas, y_canvas = self.get_canvas_mouse_pos()
        x_image, y_image = self.canvas_pos_to_xy(x_canvas, y_canvas)
        
        return x_image, y_image
    
    def get_radec_from_xy(self, x_image, y_image):
        """Get the RA and Dec coordinates from image coordinates."""
        if hasattr(self.manager.im_ref(), "wcs_info") and self.manager.im_ref().wcs_info:
            if self.manager.im_ref().header["NAXIS"] == 3:
                try:
                    ra_dec = self.manager.im_ref().wcs_info.wcs_pix2world([[x_image, y_image, 0]], 1)[0]
                except:
                    ra_dec = self.manager.im_ref().wcs_info.wcs_pix2world([[x_image, y_image]], 1)[0]
            else:
                ra_dec = self.manager.im_ref().wcs_info.wcs_pix2world([[x_image, y_image]], 1)[0]
                
        return ra_dec[0], ra_dec[1]
    
    def get_xy_from_radec(self, ra, dec):
        """Get the image coordinates from RA and Dec coordinates."""
        try:
            if hasattr(self.manager.im_ref(), "wcs_info") and self.manager.im_ref().wcs_info:
                x_image, y_image = self.manager.im_ref().wcs_info.wcs_world2pix([[ra, dec]], 1)[0]
        except Exception as e:
            control.warn(f"Error converting coordinates: {e}")
            
        return x_image, y_image
    
    def get_mouse_coords(self):
        """Get the RA and Dec coordinates of the mouse position on the image."""
        # Calculate RA and Dec if WCS information is available
        x_image, y_image = self.get_image_xy_mouse()
        ra, dec = self.get_radec_from_xy(x_image, y_image)
        return ra, dec
    
    def get_image_canvas_center_coords(self):
        """Get the RA and Dec coordinates at the center of the canvas."""
        center_x, center_y = self.get_canvas_center_pos()
        x_image, y_image = self.canvas_pos_to_xy(center_x, center_y)
        ra, dec = self.get_radec_from_xy(x_image, y_image)
        
        return ra, dec
    
    def check_xy_image_bounds(self, x_image, y_image):
        """Check if the given image coordinates are within the image bounds."""
        if x_image < 0 or x_image >= self.image_data.shape[1]:
            return False
        if y_image < 0 or y_image >= self.image_data.shape[0]:
            return False
        
        if np.isnan(x_image) or np.isnan(y_image) or np.isinf(x_image) or np.isinf(y_image):
            return False
        
        return True
    
    def center_on_xy(self, x_image, y_image, zoom_level=2.0):
        if not self.check_xy_image_bounds(x_image, y_image):
            control.warn(f"coordinates out of bounds. {self.name}")
            return
        
        # Set the zoom level
        self.zoom_level = zoom_level
        
        # Get the canvas dimensions
        canvas_width = self.manager.viewer.image_canvas.winfo_width()
        canvas_height = self.manager.viewer.image_canvas.winfo_height()
        
        # Calculate the offsets to center the target coordinates on the canvas
        self.offset_x = x_image * self.zoom_level - (canvas_width / 2)
        self.offset_y = y_image * self.zoom_level - (canvas_height / 2)
        
        # Ensure offsets don’t go out of bounds
        self.offset_x = max(self.offset_x, 0)
        self.offset_y = max(self.offset_y, 0)
        
        # Update the display with the new centered position
        self.manager.viewer.update_display_image()
        control.info(f"Centered on X: {x_image}, Y: {y_image} with zoom: {round(zoom_level, 1)}")
    
    def check_radec_bounds(self, ra, dec):
        """Check if the given RA and Dec coordinates are within the image bounds."""
        x_image, y_image = self.get_xy_from_radec(ra, dec)
        
        if x_image < 0 or x_image >= self.image_data.shape[1]:
            return False
        if y_image < 0 or y_image >= self.image_data.shape[0]:
            return False
        return True
    
    def center_on_coordinate(self, ra, dec, zoom_level=2.0):
        """Center a given RA and Dec coordinate on the canvas with a specified zoom level."""
        x_image, y_image = self.get_xy_from_radec(ra, dec)
        
        if not self.check_xy_image_bounds(x_image, y_image):
            control.warn(f"coordinates out of bounds. {self.name}")
            return
        
        # Set the zoom level
        self.zoom_level = zoom_level
        
        # Get the canvas dimensions
        canvas_width = self.manager.viewer.image_canvas.winfo_width()
        canvas_height = self.manager.viewer.image_canvas.winfo_height()
        
        # Calculate the offsets to center the target coordinates on the canvas
        self.offset_x = x_image * self.zoom_level - (canvas_width / 2)
        self.offset_y = y_image * self.zoom_level - (canvas_height / 2)
        
        # Ensure offsets don’t go out of bounds
        self.offset_x = max(self.offset_x, 0)
        self.offset_y = max(self.offset_y, 0)
        
        # Update the display with the new centered position
        self.manager.viewer.update_display_image()
        control.info(f"Centered on RA: {ra}, Dec: {dec} with zoom: {round(zoom_level, 1)}")
        
    def zoom(self, event):
        """Zoom in or out relative to the mouse position."""
        zoom_factor = 1.1 if event.delta > 0 else 0.9
        new_zoom_level = self.zoom_level * zoom_factor

        # Calculate the mouse position relative to the original image coordinates
        x_mouse = (event.x / self.zoom_level) + (self.offset_x / self.zoom_level)
        y_mouse = (event.y / self.zoom_level) + (self.offset_y / self.zoom_level)

        # Update the zoom levelff
        self.zoom_level = new_zoom_level

        # Adjust offsets to keep zoom centered on the mouse
        self.offset_x = (x_mouse * self.zoom_level) - event.x
        self.offset_y = (y_mouse * self.zoom_level) - event.y
        
        if self.offset_x < 0:
            self.offset_x = 0
        if self.offset_y < 0:
            self.offset_y = 0

    def start_pan(self, event):
        """Start panning by recording the initial click position."""
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def pan_image(self, event):
        """Drag the image in the intuitive direction based on mouse movement."""
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        self.offset_x -= dx
        self.offset_y -= dy

        if self.offset_x < 0:
            self.offset_x = 0
        if self.offset_y < 0:
            self.offset_y = 0

        self.pan_start_x = event.x
        self.pan_start_y = event.y
        # self.update_display_image()

    def handle_canvas_click(
        self, event, image_canvas, drawing_func
    ) -> bool:
        """Handle clicks on the canvas for drawing a line between two points."""
        # Convert canvas click coordinates to image coordinates
        x_image, y_image = self.get_image_xy_mouse()
        
        if self.line_start is None:
            # Set the start point and bind the motion event for live drawing
            self.line_start = (x_image, y_image)
            image_canvas.bind("<Motion>", drawing_func)
        else:
            # Set the end point, unbind motion, and finalize drawing
            self.line_end = (x_image, y_image)
            image_canvas.unbind("<Motion>")
            
            self.manager.toggle_drawing_mode()
            self.draw_line(self.line_start, self.line_end)

            return True
            # self.update_display_image()  # Update display to finalize the line

    def update_line_position(self, event) -> bool:
        """Update the end point of the line as the mouse moves for real-time drawing."""
        if self.line_start:
            x_image, y_image = self.get_image_xy_mouse()
            
            # Update the line end temporarily and redraw
            self.line_end = (x_image, y_image)
            return True

    def draw_line(self, start, end):
        """Draw a line on the canvas between start and end points, and plot pixel values along the line."""
        if self.line_id is not None:
            self.image_canvas.delete(self.line_id)  # Remove previous line if any

        # Convert canvas coordinates to image coordinates
        x0_image = int(start[0])
        y0_image = int(start[1])
        x1_image = int(end[0])
        y1_image = int(end[1])

        # Get exact integer-based coordinates along the line (Bresenham's algorithm)
        y_values, x_values = line(y0_image, x0_image, y1_image, x1_image)

        # Ensure the coordinates are within bounds
        x_values = np.clip(x_values, 0, self.image_data.shape[1] - 1)
        y_values = np.clip(y_values, 0, self.image_data.shape[0] - 1)

        # Extract pixel values along the line
        pixel_values = self.image_data[y_values, x_values]

        # Plot the pixel values
        self.plot_pixel_values(pixel_values)

    def clear_line(self, image_canvas):
        """Clear the drawn line if it exists."""
        if self.line_id is not None:
            image_canvas.delete(self.line_id)
            self.line_id = None

    # ==================== NEW MEASUREMENT SYSTEM ====================

    def start_measurement(self, measurement_type):
        """Start a new measurement of the specified type."""
        self.measurement_mode = measurement_type
        self.temp_measurement_points = []
        control.info(f"Started {measurement_type} measurement. Click to add points.")

    def cancel_measurement(self):
        """Cancel the current measurement."""
        self.measurement_mode = None
        self.temp_measurement_points = []
        control.info("Measurement cancelled")

    def handle_measurement_click(self, event, image_canvas):
        """Handle clicks during measurement mode."""
        if self.measurement_mode is None:
            return False

        # Convert canvas coordinates to image coordinates
        x_image, y_image = self.get_image_xy_mouse()

        if self.measurement_mode == 'line':
            return self._handle_line_measurement(x_image, y_image, image_canvas)
        elif self.measurement_mode == 'circle':
            return self._handle_circle_measurement(x_image, y_image, image_canvas)
        elif self.measurement_mode == 'ellipse':
            return self._handle_ellipse_measurement(x_image, y_image, image_canvas)

        return False

    def _handle_line_measurement(self, x_image, y_image, image_canvas):
        """Handle line measurement clicks."""
        if len(self.temp_measurement_points) == 0:
            # First click - set start point
            self.temp_measurement_points.append((x_image, y_image))
            image_canvas.bind("<Motion>", lambda e: self._update_temp_line())
            control.info("Line start set. Click to set end point.")
            return False
        else:
            # Second click - finalize line
            self.temp_measurement_points.append((x_image, y_image))
            image_canvas.unbind("<Motion>")
            self._finalize_line_measurement()
            return True

    def _handle_circle_measurement(self, x_image, y_image, image_canvas):
        """Handle circle measurement clicks."""
        if len(self.temp_measurement_points) == 0:
            # First click - set center
            self.temp_measurement_points.append((x_image, y_image))
            image_canvas.bind("<Motion>", lambda e: self._update_temp_circle())
            control.info("Circle center set. Click to set radius.")
            return False
        else:
            # Second click - finalize circle
            self.temp_measurement_points.append((x_image, y_image))
            image_canvas.unbind("<Motion>")
            self._finalize_circle_measurement()
            return True

    def _handle_ellipse_measurement(self, x_image, y_image, image_canvas):
        """Handle ellipse measurement clicks (3 clicks: center, semi-major end, semi-minor end)."""
        if len(self.temp_measurement_points) == 0:
            # First click - set center
            self.temp_measurement_points.append((x_image, y_image))
            image_canvas.bind("<Motion>", lambda e: self._update_temp_ellipse())
            control.info("Ellipse center set. Click to set semi-major axis.")
            return False
        elif len(self.temp_measurement_points) == 1:
            # Second click - set semi-major axis
            self.temp_measurement_points.append((x_image, y_image))
            control.info("Semi-major axis set. Click to set semi-minor axis.")
            return False
        else:
            # Third click - finalize ellipse
            self.temp_measurement_points.append((x_image, y_image))
            image_canvas.unbind("<Motion>")
            self._finalize_ellipse_measurement()
            return True

    def _update_temp_line(self):
        """Update temporary line during mouse movement."""
        if len(self.temp_measurement_points) >= 1:
            x_image, y_image = self.get_image_xy_mouse()
            self.temp_measurement_points = [self.temp_measurement_points[0], (x_image, y_image)]
            return True
        return False

    def _update_temp_circle(self):
        """Update temporary circle during mouse movement."""
        if len(self.temp_measurement_points) >= 1:
            x_image, y_image = self.get_image_xy_mouse()
            self.temp_measurement_points = [self.temp_measurement_points[0], (x_image, y_image)]
            return True
        return False

    def _update_temp_ellipse(self):
        """Update temporary ellipse during mouse movement."""
        if len(self.temp_measurement_points) >= 1:
            x_image, y_image = self.get_image_xy_mouse()
            if len(self.temp_measurement_points) == 1:
                self.temp_measurement_points = [self.temp_measurement_points[0], (x_image, y_image)]
            else:
                self.temp_measurement_points = [self.temp_measurement_points[0],
                                               self.temp_measurement_points[1],
                                               (x_image, y_image)]
            return True
        return False

    def _finalize_line_measurement(self):
        """Create and save a line measurement."""
        start, end = self.temp_measurement_points[0], self.temp_measurement_points[1]

        # Extract pixel values along the line
        x0, y0 = int(start[0]), int(start[1])
        x1, y1 = int(end[0]), int(end[1])
        y_values, x_values = line(y0, x0, y1, x1)
        x_values = np.clip(x_values, 0, self.image_data.shape[1] - 1)
        y_values = np.clip(y_values, 0, self.image_data.shape[0] - 1)
        pixel_values = self.image_data[y_values, x_values]

        # Create measurement
        measurement = LineMeasurement(
            start=start,
            end=end,
            pixel_values=pixel_values,
            image_name=self.name,
            color="red"
        )

        # Add to manager
        self.manager.measurement_manager.add_measurement(measurement)
        control.info(f"Line measurement added: {measurement.get_length():.2f} px")

        # Plot the pixel values
        self.plot_pixel_values(pixel_values)

        # Clear temp points and exit measurement mode
        self.temp_measurement_points = []
        self.measurement_mode = None

    def _finalize_circle_measurement(self):
        """Create and save a circle measurement."""
        center = self.temp_measurement_points[0]
        edge = self.temp_measurement_points[1]

        # Calculate radius
        dx = edge[0] - center[0]
        dy = edge[1] - center[1]
        radius = np.sqrt(dx**2 + dy**2)

        # Extract pixel values along the circle perimeter
        try:
            rr, cc = circle_perimeter(int(center[1]), int(center[0]), int(radius))
            # Clip to image bounds
            valid = (rr >= 0) & (rr < self.image_data.shape[0]) & (cc >= 0) & (cc < self.image_data.shape[1])
            rr, cc = rr[valid], cc[valid]
            pixel_values = self.image_data[rr, cc]
        except:
            pixel_values = np.array([])

        # Calculate interior statistics
        interior_count = 0
        interior_sum = 0.0
        interior_mean = 0.0

        try:
            # Create a grid of points within the bounding box
            x_min = max(0, int(center[0] - radius - 1))
            x_max = min(self.image_data.shape[1], int(center[0] + radius + 2))
            y_min = max(0, int(center[1] - radius - 1))
            y_max = min(self.image_data.shape[0], int(center[1] + radius + 2))

            # Check each pixel if it's inside the circle
            for y in range(y_min, y_max):
                for x in range(x_min, x_max):
                    dist = np.sqrt((x - center[0])**2 + (y - center[1])**2)
                    if dist <= radius:
                        interior_count += 1
                        interior_sum += float(self.image_data[y, x])

            if interior_count > 0:
                interior_mean = interior_sum / interior_count
        except Exception as e:
            control.warn(f"Error calculating interior statistics: {e}")

        # Create measurement
        measurement = CircleMeasurement(
            center=center,
            radius=radius,
            pixel_values=pixel_values,
            interior_count=interior_count,
            interior_sum=interior_sum,
            interior_mean=interior_mean,
            image_name=self.name,
            color="green"
        )

        # Add to manager
        self.manager.measurement_manager.add_measurement(measurement)
        control.info(f"Circle measurement added: radius={radius:.2f} px, area={measurement.get_area():.2f} px², count={interior_count}")

        # Plot the pixel values
        if len(pixel_values) > 0:
            self.plot_pixel_values(pixel_values)

        # Clear temp points and exit measurement mode
        self.temp_measurement_points = []
        self.measurement_mode = None

    def _finalize_ellipse_measurement(self):
        """Create and save an ellipse measurement."""
        center = self.temp_measurement_points[0]
        major_point = self.temp_measurement_points[1]
        minor_point = self.temp_measurement_points[2]

        # Calculate semi-major axis and rotation
        dx_major = major_point[0] - center[0]
        dy_major = major_point[1] - center[1]
        semi_major = np.sqrt(dx_major**2 + dy_major**2)
        rotation = np.arctan2(dy_major, dx_major)

        # Calculate semi-minor axis (perpendicular distance from minor_point to major axis)
        dx_minor = minor_point[0] - center[0]
        dy_minor = minor_point[1] - center[1]
        # Project onto perpendicular axis
        perp_x = -dy_major
        perp_y = dx_major
        perp_len = np.sqrt(perp_x**2 + perp_y**2)
        if perp_len > 0:
            perp_x /= perp_len
            perp_y /= perp_len
        semi_minor = abs(dx_minor * perp_x + dy_minor * perp_y)

        # Extract pixel values along the ellipse perimeter
        try:
            rr, cc = ellipse_perimeter(int(center[1]), int(center[0]),
                                      int(semi_major), int(semi_minor),
                                      orientation=rotation)
            # Clip to image bounds
            valid = (rr >= 0) & (rr < self.image_data.shape[0]) & (cc >= 0) & (cc < self.image_data.shape[1])
            rr, cc = rr[valid], cc[valid]
            pixel_values = self.image_data[rr, cc]
        except:
            pixel_values = np.array([])

        # Calculate interior statistics
        interior_count = 0
        interior_sum = 0.0
        interior_mean = 0.0

        try:
            # Create a grid of points within the bounding box
            max_axis = max(semi_major, semi_minor)
            x_min = max(0, int(center[0] - max_axis - 1))
            x_max = min(self.image_data.shape[1], int(center[0] + max_axis + 2))
            y_min = max(0, int(center[1] - max_axis - 1))
            y_max = min(self.image_data.shape[0], int(center[1] + max_axis + 2))

            # Precompute rotation matrix
            cos_rot = np.cos(-rotation)
            sin_rot = np.sin(-rotation)

            # Check each pixel if it's inside the ellipse
            for y in range(y_min, y_max):
                for x in range(x_min, x_max):
                    # Transform point to ellipse coordinate system
                    dx = x - center[0]
                    dy = y - center[1]
                    # Rotate back to align with axes
                    x_rot = dx * cos_rot - dy * sin_rot
                    y_rot = dx * sin_rot + dy * cos_rot

                    # Check if inside ellipse: (x/a)^2 + (y/b)^2 <= 1
                    if semi_major > 0 and semi_minor > 0:
                        ellipse_eq = (x_rot / semi_major)**2 + (y_rot / semi_minor)**2
                        if ellipse_eq <= 1.0:
                            interior_count += 1
                            interior_sum += float(self.image_data[y, x])

            if interior_count > 0:
                interior_mean = interior_sum / interior_count
        except Exception as e:
            control.warn(f"Error calculating interior statistics: {e}")

        # Create measurement
        measurement = EllipseMeasurement(
            center=center,
            semi_major=semi_major,
            semi_minor=semi_minor,
            rotation=rotation,
            pixel_values=pixel_values,
            interior_count=interior_count,
            interior_sum=interior_sum,
            interior_mean=interior_mean,
            image_name=self.name,
            color="blue"
        )

        # Add to manager
        self.manager.measurement_manager.add_measurement(measurement)
        control.info(f"Ellipse measurement added: axes=({semi_major:.2f}, {semi_minor:.2f}) px, area={measurement.get_area():.2f} px², count={interior_count}")

        # Plot the pixel values
        if len(pixel_values) > 0:
            self.plot_pixel_values(pixel_values)

        # Clear temp points and exit measurement mode
        self.temp_measurement_points = []
        self.measurement_mode = None

    def draw_measurements(self, image_draw, x_start, y_start):
        """Draw all visible measurements for this image on the PIL Image."""
        measurements = self.manager.measurement_manager.get_visible_measurements(self.name)

        for measurement in measurements:
            # Get drawing instructions
            drawing_instructions = measurement.draw(
                self.image_data,
                self.zoom_level,
                self.offset_x,
                self.offset_y,
                self.xy_to_canvas
            )

            # Execute drawing instructions
            for shape_type, params in drawing_instructions:
                # Adjust coordinates relative to current view
                if shape_type == "line":
                    coords = params["coords"]
                    adjusted_coords = [
                        (coords[0] - x_start * self.zoom_level),
                        (coords[1] - y_start * self.zoom_level),
                        (coords[2] - x_start * self.zoom_level),
                        (coords[3] - y_start * self.zoom_level)
                    ]
                    image_draw.line(adjusted_coords, fill=params["fill"], width=params["width"])
                elif shape_type == "oval":
                    coords = params["coords"]
                    adjusted_coords = [
                        (coords[0] - x_start * self.zoom_level),
                        (coords[1] - y_start * self.zoom_level),
                        (coords[2] - x_start * self.zoom_level),
                        (coords[3] - y_start * self.zoom_level)
                    ]
                    image_draw.ellipse(adjusted_coords, fill=params.get("fill"),
                                     outline=params.get("outline"), width=params.get("width", 1))
                elif shape_type == "polygon":
                    coords = params["coords"]
                    # Adjust all polygon points
                    adjusted_coords = []
                    for i in range(0, len(coords), 2):
                        adjusted_coords.append(coords[i] - x_start * self.zoom_level)
                        adjusted_coords.append(coords[i+1] - y_start * self.zoom_level)
                    image_draw.polygon(adjusted_coords, fill=params.get("fill", ""),
                                     outline=params.get("outline"), width=params.get("width", 1))

        # Draw temporary measurement in progress
        if self.measurement_mode and len(self.temp_measurement_points) > 0:
            self._draw_temp_measurement(image_draw, x_start, y_start)

    def _draw_temp_measurement(self, image_draw, x_start, y_start):
        """Draw temporary measurement being created."""
        if self.measurement_mode == 'line' and len(self.temp_measurement_points) >= 1:
            points = self.temp_measurement_points
            if len(points) == 2:
                x1, y1 = self.xy_to_canvas(points[0][0], points[0][1])
                x2, y2 = self.xy_to_canvas(points[1][0], points[1][1])
                x1 -= x_start * self.zoom_level
                y1 -= y_start * self.zoom_level
                x2 -= x_start * self.zoom_level
                y2 -= y_start * self.zoom_level
                image_draw.line([x1, y1, x2, y2], fill="yellow", width=2)
                # Draw circles at endpoints
                image_draw.ellipse([x1-3, y1-3, x1+3, y1+3], fill="yellow", outline="yellow")
                image_draw.ellipse([x2-3, y2-3, x2+3, y2+3], fill="yellow", outline="yellow")

        elif self.measurement_mode == 'circle' and len(self.temp_measurement_points) >= 1:
            points = self.temp_measurement_points
            center = points[0]

            # Draw center point
            cx, cy = self.xy_to_canvas(center[0], center[1])
            cx -= x_start * self.zoom_level
            cy -= y_start * self.zoom_level
            image_draw.ellipse([cx-4, cy-4, cx+4, cy+4], fill="yellow", outline="yellow")

            if len(points) == 2:
                edge = points[1]
                dx = edge[0] - center[0]
                dy = edge[1] - center[1]
                radius = np.sqrt(dx**2 + dy**2)

                ex, ey = self.xy_to_canvas(center[0] + radius, center[1])
                canvas_radius = abs(ex - cx)

                # Draw the circle
                image_draw.ellipse([cx - canvas_radius, cy - canvas_radius,
                                   cx + canvas_radius, cy + canvas_radius],
                                  outline="yellow", width=2)

                # Draw radius line
                edge_x, edge_y = self.xy_to_canvas(edge[0], edge[1])
                edge_x -= x_start * self.zoom_level
                edge_y -= y_start * self.zoom_level
                image_draw.line([cx, cy, edge_x, edge_y], fill="yellow", width=1, dash=(5, 3))
                # Draw edge point
                image_draw.ellipse([edge_x-3, edge_y-3, edge_x+3, edge_y+3], fill="yellow", outline="yellow")

        elif self.measurement_mode == 'ellipse' and len(self.temp_measurement_points) >= 1:
            points = self.temp_measurement_points
            center = points[0]

            # Draw center point
            cx, cy = self.xy_to_canvas(center[0], center[1])
            cx -= x_start * self.zoom_level
            cy -= y_start * self.zoom_level
            image_draw.ellipse([cx-4, cy-4, cx+4, cy+4], fill="yellow", outline="yellow")

            if len(points) >= 2:
                major_point = points[1]

                # Draw center to major axis line
                mx, my = self.xy_to_canvas(major_point[0], major_point[1])
                mx -= x_start * self.zoom_level
                my -= y_start * self.zoom_level
                image_draw.line([cx, cy, mx, my], fill="yellow", width=2)
                image_draw.ellipse([mx-3, my-3, mx+3, my+3], fill="yellow", outline="yellow")

                if len(points) == 3:
                    minor_point = points[2]

                    # Calculate ellipse parameters for preview
                    dx_major = major_point[0] - center[0]
                    dy_major = major_point[1] - center[1]
                    semi_major = np.sqrt(dx_major**2 + dy_major**2)
                    rotation = np.arctan2(dy_major, dx_major)

                    dx_minor = minor_point[0] - center[0]
                    dy_minor = minor_point[1] - center[1]
                    perp_x = -dy_major
                    perp_y = dx_major
                    perp_len = np.sqrt(perp_x**2 + perp_y**2)
                    if perp_len > 0:
                        perp_x /= perp_len
                        perp_y /= perp_len
                    semi_minor = abs(dx_minor * perp_x + dy_minor * perp_y)

                    # Draw the ellipse preview
                    try:
                        # Generate ellipse points
                        theta = np.linspace(0, 2*np.pi, 100)
                        x_local = semi_major * np.cos(theta)
                        y_local = semi_minor * np.sin(theta)

                        cos_rot = np.cos(rotation)
                        sin_rot = np.sin(rotation)
                        x_rotated = x_local * cos_rot - y_local * sin_rot
                        y_rotated = x_local * sin_rot + y_local * cos_rot

                        x_img = x_rotated + center[0]
                        y_img = y_rotated + center[1]

                        # Convert to canvas coordinates and adjust for view
                        canvas_points = []
                        for xi, yi in zip(x_img, y_img):
                            xc, yc = self.xy_to_canvas(xi, yi)
                            xc -= x_start * self.zoom_level
                            yc -= y_start * self.zoom_level
                            canvas_points.append((xc, yc))

                        # Draw ellipse as polygon
                        if len(canvas_points) > 2:
                            for i in range(len(canvas_points)):
                                next_i = (i + 1) % len(canvas_points)
                                image_draw.line([canvas_points[i], canvas_points[next_i]],
                                              fill="yellow", width=2)
                    except:
                        pass

                    # Draw minor axis point
                    mnx, mny = self.xy_to_canvas(minor_point[0], minor_point[1])
                    mnx -= x_start * self.zoom_level
                    mny -= y_start * self.zoom_level
                    image_draw.line([cx, cy, mnx, mny], fill="yellow", width=1, dash=(5, 3))
                    image_draw.ellipse([mnx-3, mny-3, mnx+3, mny+3], fill="yellow", outline="yellow")

    def plot_pixel_values(self, pixel_values):
        """Plot the pixel values along the line and display it within the Tkinter interface with a custom background."""

        # Clear previous plot if it exists
        for widget in self.manager.plot_frame.winfo_children():
            widget.destroy()

        # Set the background color of plot_frame to match the Tkinter window background if necessary
        self.manager.plot_frame.configure(
            fg_color="#333233"
        )  # Adjust to your main window color if needed

        # Create a new figure with specified background color
        fig = Figure(figsize=(5, 3), dpi=100, facecolor="#333233")
        ax = fig.add_subplot(
            111, facecolor="#333233"
        )  # Set axes background to the same color

        line_color = "#FFDD44"  # Yellowish line color
        marker_color = "#FF8800"  # Orange marker color
        # Plot the pixel values
        ax.plot(
            pixel_values,
            color=line_color,
            markerfacecolor=marker_color,
            markeredgewidth=0,
            marker="o",
            markersize=2,
            linestyle="-",
            linewidth=1,
        )
        ax.set_title(
            "Pixel Values Along the Line", color="white"
        )  # Set title color to contrast
        ax.set_xlabel("Position Along the Line", color="white")
        ax.set_ylabel("Pixel Intensity", color="white")
        ax.grid(True, color="gray")  # Grid color for visibility on dark background

        # Customize tick colors to match background contrast
        ax.tick_params(colors="white")

        # Apply tight layout to prevent cutting off edges
        fig.tight_layout()

        # Embed the plot in the specified frame
        self.plot_canvas = FigureCanvasTkAgg(fig, master=self.manager.plot_frame)
        self.plot_canvas.draw()
        self.plot_canvas.get_tk_widget().pack(fill="both", expand=True)

    def get_thumbnail(self, image_canvas, size=(25, 25), final_size=(50, 50)):
        """Generate a thumbnail of the cached image for display with precise subpixel alignment of the center square."""
        if self.cached_img_data is None:
            print("Cached image data is not available.")
            return None

        x_image, y_image = self.get_image_xy_mouse()
        
        # Define the cropping area around the mouse location with subpixel precision
        x_start = x_image - size[0] / 2
        y_start = y_image - size[1] / 2
        x_end = x_image + size[0] / 2
        y_end = y_image + size[1] / 2

        # Ensure the crop boundaries are within the image bounds
        x_start = max(x_start, 0)
        y_start = max(y_start, 0)
        x_end = min(x_end, self.cached_img_data.shape[1])
        y_end = min(y_end, self.cached_img_data.shape[0])

        # Extract the thumbnail data, handling subpixel precision using resampling
        cropped_data = self.cached_img_data[
            int(y_start) : int(y_end), int(x_start) : int(x_end)
        ]
        thumbnail_image = Image.fromarray(cropped_data).convert("RGB").resize(
            final_size, Image.NEAREST
        )

        # Calculate the offset within the pixel for accurate subpixel placement
        subpixel_offset_x = (x_image - int(x_image)) * final_size[0] / size[0]
        subpixel_offset_y = (y_image - int(y_image)) * final_size[1] / size[1]

        # Draw a square at the exact subpixel position within the thumbnail
        draw = ImageDraw.Draw(thumbnail_image)
        center_x = (final_size[0] / 2) + subpixel_offset_x - 3
        center_y = (final_size[1] / 2) + subpixel_offset_y - 3
        square_size = 10  # Size of the square in pixels
        draw.rectangle(
            [
                (center_x - square_size / 2, center_y - square_size / 2),
                (center_x + square_size / 2, center_y + square_size / 2),
            ],
            outline=colors.accent,
        )

        return thumbnail_image

    @staticmethod
    def load_f_data(data, header, manager = None, name = None):
        fits_image = FitsImage(data, header, manager, name)
        fits_image.update_image_cache()

        return fits_image
    
    @staticmethod
    def load(file_path, hdu_index=0, manager = None, name = None):
        hdulist = fits.open(file_path)
        hdu = hdulist[hdu_index]

        fits_image = FitsImage(hdu.data, hdu.header, manager, name)
        fits_image.update_image_cache()

        return fits_image
