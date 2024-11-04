import tkinter as tk
from tkinter import filedialog
from astropy.io import fits
from PIL import Image, ImageTk
import numpy as np
import os
from image import FitsImage
from PIL import ImageDraw

import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from skimage.draw import line

MAX_DISPLAY_SIZE = 2000  # Limit to a maximum display size to reduce lag

class FITSViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("FITS Viewer")
        self.sidebar_visible = False  # Track if the sidebar is visible

        # Create the main container frame
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        # Sidebar (initially hidden)
        self.sidebar_frame = tk.Frame(self.main_frame, width=200, relief="sunken", borderwidth=2)
        self.sidebar_frame.pack(side="right", fill="y")
        self.sidebar_frame.pack_forget()  # Start with the sidebar hidden

        # Initialize attributes for drawing mode
        self.drawing_mode = False

        self.line_start = None
        self.line_end = None  # Add an end point for the line
        
        self.line_id = None
            
        # Content frame inside main_frame for the rest of the UI elements
        self.content_frame = tk.Frame(self.main_frame)
        self.content_frame.pack(side="left", fill="both", expand=True)

        # Setup the main UI components in content_frame
        self.setup_ui()

        self.active_image = None
        self.images = {}
        self.cached_img_data = None  # Cached processed image data
        self.last_zoom_level = 1.0  # Track the last zoom level to avoid redundant resizing
        self.current_display = None  # Cache for the displayed image portion
        self.update_coordinates()

    def setup_ui(self):
        # Sidebar Content
        tk.Label(self.sidebar_frame, text="Sidebar Content").pack()
        # Add additional sidebar controls here (e.g., sliders, buttons, etc.)

        draw_line_button = tk.Button(self.sidebar_frame, text="Draw Line", command=self.toggle_drawing_mode)
        draw_line_button.pack(pady=5)
        
        # Main file frame and canvas inside content_frame
        file_frame = tk.Frame(self.content_frame)
        file_frame.pack(fill="x", padx=5, pady=5)
        self.file_path_entry = tk.Entry(file_frame, width=40)
        self.file_path_entry.pack(side="left", fill="x", expand=True)
        browse_button = tk.Button(file_frame, text="Browse FITS File", command=self.open_file_dialog)
        browse_button.pack(side="right")
        
        self.hdu_numinput = tk.Entry(file_frame, width=5)
        self.hdu_numinput.pack(side="right")
        self.hdu_numinput.insert(0, "1")
        
        hdu_numlabel = tk.Label(file_frame, text="HDU Number:")
        hdu_numlabel.pack(side="right")
        
        

        # Input fields for pmin and pmax with an "Apply" button
        input_frame = tk.Frame(self.content_frame)
        input_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Label(input_frame, text="pmin:").pack(side="left")
        self.pmin_entry = tk.Entry(input_frame, width=5)
        self.pmin_entry.insert(0, "0")
        self.pmin_entry.pack(side="left")
        
        tk.Label(input_frame, text="pmax:").pack(side="left")
        self.pmax_entry = tk.Entry(input_frame, width=5)
        self.pmax_entry.insert(0, "100")
        self.pmax_entry.pack(side="left")
        
        apply_button = tk.Button(input_frame, text="Apply", command=self.update_image_cache)
        apply_button.pack(side="left")
        
        # Sidebar Toggle Button
        toggle_sidebar_button = tk.Button(input_frame, text="Tools", command=self.toggle_sidebar)
        toggle_sidebar_button.pack(side="right")

        # Canvas to display the FITS image
        self.image_canvas = tk.Canvas(self.content_frame, width=500, height=500)
        self.image_canvas.pack(fill="both", expand=True, padx=5, pady=5)
        self.image_canvas.bind("<MouseWheel>", self.zoom)
        self.image_canvas.bind("<Button-1>", self.start_pan)
        self.image_canvas.bind("<B1-Motion>", self.pan_image)
        
        coord_frame = tk.Frame(self.content_frame)
        coord_frame.pack(pady=10)
        self.x_label = tk.Label(coord_frame, text="X:", width=10, relief="sunken", font=("Arial", 10))
        self.x_label.grid(row=0, column=0, padx=5)
        self.y_label = tk.Label(coord_frame, text="Y:", width=10, relief="sunken", font=("Arial", 10))
        self.y_label.grid(row=0, column=1, padx=5)
        self.ra_label = tk.Label(coord_frame, text="RA:", width=20, relief="sunken", font=("Arial", 10))
        self.ra_label.grid(row=0, column=2, padx=5)
        self.dec_label = tk.Label(coord_frame, text="Dec:", width=20, relief="sunken", font=("Arial", 10))
        self.dec_label.grid(row=0, column=3, padx=5)
        self.pixel_value_label = tk.Label(coord_frame, text="Value:", width=15, relief="sunken", font=("Arial", 10))
        self.pixel_value_label.grid(row=0, column=4, padx=5)

    def toggle_drawing_mode(self):
        """Enable or disable line drawing mode."""
        self.drawing_mode = not self.drawing_mode
        if self.drawing_mode:
            self.line_start = None  # Reset starting point
            self.line_end = None  # Reset end point
            self.image_canvas.unbind("<Button-1>")
            self.image_canvas.bind("<Button-1>", self.handle_canvas_click)  # Bind for drawing
            print("Drawing mode enabled.")
        else:
            self.clear_line()  # Clear any drawn line when exiting drawing mode
            self.image_canvas.unbind("<Button-1>")
            self.image_canvas.bind("<Button-1>", self.start_pan)  # Re-bind for panning
            
            print("Drawing mode disabled.")
    
    def toggle_sidebar(self):
        """Toggle the visibility of the sidebar."""
        if self.sidebar_visible:
            self.sidebar_frame.pack_forget()  # Hide the sidebar
        else:
            self.sidebar_frame.pack(side="right", fill="y")  # Show the sidebar
        self.sidebar_visible = not self.sidebar_visible  # Update the visibility status

    def open_file_dialog(self):
        file_path = filedialog.askopenfilename(filetypes=[("FITS file", ["*.fz", "*fits"] ), ("All files", "*.*")])
        if file_path:
            self.file_path_entry.delete(0, tk.END)
            self.file_path_entry.insert(0, file_path)
            self.load_fits(file_path)

    def im_ref(self):
        if self.active_image is None:
            return None
        return self.images[self.active_image]
    
    def load_fits(self, file_path):
        try:
            hdu = int(self.hdu_numinput.get())
            image_name = os.path.basename(file_path)
            with fits.open(file_path) as hdul:
                im = FitsImage(hdul[hdu].data, hdul[hdu].header)
            self.images[image_name] = im
            self.active_image = image_name
            
            self.im_ref().zoom_level = 1.0
            self.im_ref().offset_x = self.offset_y = 0
            self.update_image_cache()  # Process image once and cache it
        except Exception as e:
            print(f"Error loading file: {e}")

    def update_image_cache(self):
        """Update the cached image based on pmin and pmax values."""
        if self.active_image is not None:
            try:
                pmin = float(self.pmin_entry.get())
                pmax = float(self.pmax_entry.get())
            except ValueError:
                print("Invalid pmin or pmax value")
                return
            
            if pmin >= pmax:
                pmax = pmin + 1
            
            # Cache processed data once
            vmin, vmax = np.percentile(self.im_ref().image_data, [pmin, pmax])
            img_data = np.clip(self.im_ref().image_data, vmin, vmax)
            img_data = ((img_data - vmin) / (vmax - vmin) * 255).astype(np.uint8)
            self.cached_img_data = img_data  # Store in cache
            self.update_display_image()  # Display the cached image

    def update_display_image(self):
        """Efficiently update the display by only rendering the visible portion of the image."""
        if self.cached_img_data is None:
            return  # If no cache is available, skip

        # Calculate visible area based on offsets and zoom level
        x_start = max(int(self.im_ref().offset_x / self.im_ref().zoom_level), 0)
        y_start = max(int(self.im_ref().offset_y / self.im_ref().zoom_level), 0)
        visible_width = int(self.image_canvas.winfo_width() / self.im_ref().zoom_level)
        visible_height = int(self.image_canvas.winfo_height() / self.im_ref().zoom_level)

        # Ensure the cropped area doesn't exceed image bounds
        width = min(visible_width, self.cached_img_data.shape[1] - x_start)
        height = min(visible_height, self.cached_img_data.shape[0] - y_start)

        # Crop and resize only the visible portion of the image
        cropped_data = self.cached_img_data[y_start:y_start+height, x_start:x_start+width]
        display_img = Image.fromarray(cropped_data).resize(
            (int(width * self.im_ref().zoom_level), int(height * self.im_ref().zoom_level)),
            Image.NEAREST
        )

        # Draw the line if start and end points are set
        if self.line_start and self.line_end:
            draw = ImageDraw.Draw(display_img)
            
            # Calculate line coordinates relative to the current view
            start_x = (self.line_start[0] - x_start) * self.im_ref().zoom_level
            start_y = (self.line_start[1] - y_start) * self.im_ref().zoom_level
            end_x = (self.line_end[0] - x_start) * self.im_ref().zoom_level
            end_y = (self.line_end[1] - y_start) * self.im_ref().zoom_level

            # Draw the line in red
            draw.line((start_x, start_y, end_x, end_y), fill="red", width=2)

        # Display the image with the line
        self.tk_img = ImageTk.PhotoImage(display_img)
        self.image_canvas.delete("all")
        self.image_canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        
    def zoom(self, event):
        """Zoom in or out relative to the mouse position."""
        zoom_factor = 1.1 if event.delta > 0 else 0.9
        new_zoom_level = self.im_ref().zoom_level * zoom_factor

        # Calculate the mouse position relative to the original image coordinates
        x_mouse = (event.x / self.im_ref().zoom_level) + (self.im_ref().offset_x / self.im_ref().zoom_level)
        y_mouse = (event.y / self.im_ref().zoom_level) + (self.im_ref().offset_y / self.im_ref().zoom_level)

        # Update the zoom level
        self.im_ref().zoom_level = new_zoom_level

        # Adjust offsets to keep zoom centered on the mouse
        self.im_ref().offset_x = (x_mouse * self.im_ref().zoom_level) - event.x
        self.im_ref().offset_y = (y_mouse * self.im_ref().zoom_level) - event.y

        # Refresh the display to apply the new zoom and offsets
        self.update_display_image()

    def start_pan(self, event):
        """Start panning by recording the initial click position."""
        if not self.active_image:
            return
        self.im_ref().pan_start_x = event.x
        self.im_ref().pan_start_y = event.y

    def pan_image(self, event):
        """Drag the image in the intuitive direction based on mouse movement."""
        if not self.active_image or self.drawing_mode:  # Skip if in drawing mode
            return
        dx = event.x - self.im_ref().pan_start_x
        dy = event.y - self.im_ref().pan_start_y
        self.im_ref().offset_x -= dx
        self.im_ref().offset_y -= dy
        self.im_ref().pan_start_x = event.x
        self.im_ref().pan_start_y = event.y
        self.update_display_image()
        
    def handle_canvas_click(self, event):
        """Handle clicks on the canvas for drawing a line between two points."""
        if not self.drawing_mode:
            return  # Only proceed if drawing mode is active

        # Convert canvas click coordinates to image coordinates
        x_image = (event.x + self.im_ref().offset_x) / self.im_ref().zoom_level
        y_image = (event.y + self.im_ref().offset_y) / self.im_ref().zoom_level

        if self.line_start is None:
            # Set the start point and bind the motion event for live drawing
            self.line_start = (x_image, y_image)
            self.image_canvas.bind("<Motion>", self.update_line_position)
        else:
            # Set the end point, unbind motion, and finalize drawing
            self.line_end = (x_image - 1, y_image - 1)
            self.image_canvas.unbind("<Motion>")
            self.draw_line(self.line_start, self.line_end)
            
            self.update_display_image()  # Update display to finalize the line
    
    def update_line_position(self, event):
        """Update the end point of the line as the mouse moves for real-time drawing."""
        if self.line_start:
            # Convert current mouse position to image coordinates
            x_image = (event.x + self.im_ref().offset_x) / self.im_ref().zoom_level
            y_image = (event.y + self.im_ref().offset_y) / self.im_ref().zoom_level

            # Update the line end temporarily and redraw
            self.line_end = (x_image - 1, y_image - 1)
            self.update_display_image()
        
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
        x_values = np.clip(x_values, 0, self.im_ref().image_data.shape[1] - 1)
        y_values = np.clip(y_values, 0, self.im_ref().image_data.shape[0] - 1)

        print(x_values, y_values)
        
        # Extract pixel values along the line
        pixel_values = self.im_ref().image_data[y_values, x_values]

        # Plot the pixel values
        print(pixel_values)
        self.toggle_drawing_mode()  # Exit drawing mode after drawing
        self.plot_pixel_values(pixel_values)

    def clear_line(self):
        """Clear the drawn line if it exists."""
        if self.line_id is not None:
            self.image_canvas.delete(self.line_id)
            self.line_id = None
    def plot_pixel_values(self, pixel_values):
        """Plot the pixel values along the line."""
        plt.figure(figsize=(8, 4))
        plt.plot(pixel_values, color='blue', marker='o', markersize=4, linestyle='-')
        plt.title("Pixel Values Along the Line")
        plt.xlabel("Position Along the Line")
        plt.ylabel("Pixel Intensity")
        plt.grid()
        plt.show()
    
    def update_coordinates(self):
        if self.active_image is not None:
            # Get mouse position relative to the canvas
            x_canvas = self.image_canvas.winfo_pointerx() - self.image_canvas.winfo_rootx()
            y_canvas = self.image_canvas.winfo_pointery() - self.image_canvas.winfo_rooty()

            # Calculate the actual position on the full image, accounting for zoom and offsets
            x_image = (x_canvas + self.im_ref().offset_x) / self.im_ref().zoom_level
            y_image = (y_canvas + self.im_ref().offset_y) / self.im_ref().zoom_level
            x_int, y_int = round(x_image) - 1, round(y_image) - 1

            # Ensure coordinates are within the image boundaries
            if 0 <= x_int < self.im_ref().image_data.shape[1] and 0 <= y_int < self.im_ref().image_data.shape[0]:
                # Get pixel value from the full-resolution data
                pixel_value = self.im_ref().image_data[y_int, x_int]
                
                # Calculate RA and Dec if WCS information is available
                if hasattr(self.im_ref(), 'wcs_info') and self.im_ref().wcs_info:
                    ra_dec = self.im_ref().wcs_info.wcs_pix2world([[x_image, y_image]], 1)[0]
                    ra, dec = ra_dec[0], ra_dec[1]
                    self.ra_label.config(text=f"RA: {ra:.4f}")
                    self.dec_label.config(text=f"Dec: {dec:.4f}")
                else:
                    # Set RA/Dec to None if no WCS information
                    self.ra_label.config(text="RA: N/A")
                    self.dec_label.config(text="Dec: N/A")
                
                # Update coordinate labels
                self.x_label.config(text=f"X: {x_image:.2f}")
                self.y_label.config(text=f"Y: {y_image:.2f}")
                self.pixel_value_label.config(text=f"Value: {pixel_value:.3f}")
            else:
                # Clear labels if outside image bounds
                self.x_label.config(text="X: -")
                self.y_label.config(text="Y: -")
                self.ra_label.config(text="RA: -")
                self.dec_label.config(text="Dec: -")
                self.pixel_value_label.config(text="Value: -")
                
        # Schedule the next update
        self.root.after(50, self.update_coordinates)
        
root = tk.Tk()
viewer = FITSViewer(root)
root.mainloop()