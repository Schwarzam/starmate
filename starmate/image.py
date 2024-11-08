from astropy.io import fits
from astropy.wcs import WCS

import numpy as np

from PIL import Image, ImageDraw, ImageTk
from skimage.draw import line

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from starmate.variables import colors

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

        self.line_start = None
        self.line_end = None

        self.line_id = None

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
        
        if self.manager.viewer.coords_frozen:
            # Draw the crosshair at the center of the canvas
            draw = ImageDraw.Draw(display_img)
            
            x_image = self.manager.viewer.labels["x"][1].cget("text")
            y_image = self.manager.viewer.labels["y"][1].cget("text")
            
            frozen_x, frozen_y = self.xy_to_canvas(x_image, y_image)
            
            draw.circle(
                (frozen_x, frozen_y), 10, outline=colors.accent, width=3
            )

        # Draw the line if start and end points are set
        if self.line_start and self.line_end:
            draw = ImageDraw.Draw(display_img)

            # Calculate line coordinates relative to the current view
            start_x = (self.line_start[0] - x_start) * self.zoom_level
            start_y = (self.line_start[1] - y_start) * self.zoom_level
            end_x = (self.line_end[0] - x_start) * self.zoom_level
            end_y = (self.line_end[1] - y_start) * self.zoom_level

            # Draw the line in red
            draw.line((start_x, start_y, end_x, end_y), fill="red", width=2)

        # Display the image with the line
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
