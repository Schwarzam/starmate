from astropy.io import fits
from astropy.wcs import WCS

import numpy as np

from PIL import Image, ImageDraw, ImageTk
from skimage.draw import line

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

class FitsImage:
    
    def __init__(self, image_data, header):
        self.image_data = image_data
        self.header = header
        
        self.wcs_info = WCS(header)
        
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
    
    def update_image_cache(self, pmin = 0, pmax = 100):
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
        cropped_data = self.cached_img_data[y_start:y_start + height, x_start:x_start + width]
        display_img = Image.fromarray(cropped_data).resize(
            (int(width * self.zoom_level), int(height * self.zoom_level)),
            Image.NEAREST
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
        tk_img = ImageTk.PhotoImage(display_img)  # Keep reference to avoid garbage collection
        return tk_img
    
    def zoom(self, event):
        """Zoom in or out relative to the mouse position."""
        zoom_factor = 1.1 if event.delta > 0 else 0.9
        new_zoom_level = self.zoom_level * zoom_factor

        # Calculate the mouse position relative to the original image coordinates
        x_mouse = (event.x / self.zoom_level) + (self.offset_x / self.zoom_level)
        y_mouse = (event.y / self.zoom_level) + (self.offset_y / self.zoom_level)

        # Update the zoom level
        self.zoom_level = new_zoom_level

        # Adjust offsets to keep zoom centered on the mouse
        self.offset_x = (x_mouse * self.zoom_level) - event.x
        self.offset_y = (y_mouse * self.zoom_level) - event.y

        # Refresh the display to apply the new zoom and offsets
        # self.update_display_image()
        
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
        self, 
        event, 
        image_canvas, 
        drawing_func,
        toggle_drawing_mode
    ) -> bool:
        """Handle clicks on the canvas for drawing a line between two points."""
        # Convert canvas click coordinates to image coordinates
        x_image = (event.x + self.offset_x) / self.zoom_level
        y_image = (event.y + self.offset_y) / self.zoom_level

        if self.line_start is None:
            # Set the start point and bind the motion event for live drawing
            self.line_start = (x_image, y_image)
            image_canvas.bind("<Motion>", drawing_func)
        else:
            # Set the end point, unbind motion, and finalize drawing
            self.line_end = (x_image - 1, y_image - 1)
            image_canvas.unbind("<Motion>")
            toggle_drawing_mode()
            self.draw_line(self.line_start, self.line_end)
            
            return True
            # self.update_display_image()  # Update display to finalize the line
    
    def update_line_position(self, event) -> bool:
        """Update the end point of the line as the mouse moves for real-time drawing."""
        if self.line_start:
            # Convert current mouse position to image coordinates
            x_image = (event.x + self.offset_x) / self.zoom_level
            y_image = (event.y + self.offset_y) / self.zoom_level

            # Update the line end temporarily and redraw
            self.line_end = (x_image - 1, y_image - 1)
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
        for widget in self.plot_frame.winfo_children():
            widget.destroy()
        
        # Set the background color of plot_frame to match the Tkinter window background if necessary
        self.plot_frame.config(bg="#333233")  # Adjust to your main window color if needed

        # Create a new figure with specified background color
        fig = Figure(figsize=(4, 2), dpi=100, facecolor="#333233")
        ax = fig.add_subplot(111, facecolor="#333233")  # Set axes background to the same color
        
        line_color = "#FFDD44"  # Yellowish line color
        marker_color = "#FF8800"  # Orange marker color
        # Plot the pixel values
        ax.plot(
            pixel_values, 
            color=line_color, 
            markerfacecolor=marker_color,
            markeredgewidth=0,
            marker='o', 
            markersize=2, 
            linestyle='-',
            linewidth=1
        )
        ax.set_title("Pixel Values Along the Line", color="white")  # Set title color to contrast
        ax.set_xlabel("Position Along the Line", color="white")
        ax.set_ylabel("Pixel Intensity", color="white")
        ax.grid(True, color="gray")  # Grid color for visibility on dark background

        # Customize tick colors to match background contrast
        ax.tick_params(colors="white")

        # Apply tight layout to prevent cutting off edges
        fig.tight_layout()

        # Embed the plot in the specified frame
        self.plot_canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.plot_canvas.draw()
        self.plot_canvas.get_tk_widget().pack(fill="both", expand=True)
        
    def get_thumbnail(self, image_canvas, size=(25, 25), final_size=(50, 50)):
        """Generate a thumbnail of the cached image for display with precise subpixel alignment of the center square."""
        if self.cached_img_data is None:
            print("Cached image data is not available.")
            return None

        # Get precise mouse position relative to the canvas
        x_canvas = image_canvas.winfo_pointerx() - image_canvas.winfo_rootx()
        y_canvas = image_canvas.winfo_pointery() - image_canvas.winfo_rooty()

        # Calculate the precise position on the cached image
        x_image = (x_canvas + self.offset_x) / self.zoom_level
        y_image = (y_canvas + self.offset_y) / self.zoom_level

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
            int(y_start):int(y_end),
            int(x_start):int(x_end)
        ]
        thumbnail_image = Image.fromarray(cropped_data).resize(final_size, Image.NEAREST)

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
                (center_x + square_size / 2, center_y + square_size / 2)
            ],
            outline="red"
        )

        return thumbnail_image
        
    
    @staticmethod
    def load(file_path, hdu_index=0):
        hdulist = fits.open(file_path)
        hdu = hdulist[hdu_index]
        
        fits_image = FitsImage(hdu.data, hdu.header)
        fits_image.update_image_cache()
        
        return fits_image
    
    
        