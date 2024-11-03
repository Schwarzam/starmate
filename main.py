import tkinter as tk
from tkinter import filedialog
from astropy.io import fits
from PIL import Image, ImageTk
import numpy as np
import os
from image import FitsImage

MAX_DISPLAY_SIZE = 2000  # Limit to a maximum display size to reduce lag

class FITSViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("FITS Viewer")
        self.setup_ui()
        self.active_image = None
        self.images = {}
        self.cached_img_data = None  # Cached processed image data
        self.last_zoom_level = 1.0  # Track the last zoom level to avoid redundant resizing
        self.current_display = None  # Cache for the displayed image portion
        self.update_coordinates()

    def setup_ui(self):
        file_frame = tk.Frame(self.root)
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
        input_frame = tk.Frame(self.root)
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

        self.image_canvas = tk.Canvas(self.root, width=500, height=500)
        self.image_canvas.pack(fill="both", expand=True, padx=5, pady=5)
        self.image_canvas.bind("<MouseWheel>", self.zoom)
        self.image_canvas.bind("<Button-1>", self.start_pan)
        self.image_canvas.bind("<B1-Motion>", self.pan_image)

        coord_frame = tk.Frame(self.root)
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

    def open_file_dialog(self):
        file_path = filedialog.askopenfilename(filetypes=[("FITS file", ["*.fz", "*fits"] ), ("All files", "*.*")])
        if file_path:
            self.file_path_entry.delete(0, tk.END)
            self.file_path_entry.insert(0, file_path)
            self.load_fits(file_path)

    def im_ref(self):
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
        
        # Display the cropped and resized image
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
        self.im_ref().pan_start_x = event.x
        self.im_ref().pan_start_y = event.y

    def pan_image(self, event):
        """Drag the image in the intuitive direction based on mouse movement."""
        dx = event.x - self.im_ref().pan_start_x
        dy = event.y - self.im_ref().pan_start_y

        # Move in the drag direction
        self.im_ref().offset_x -= dx
        self.im_ref().offset_y -= dy

        # Update start position for continuous panning
        self.im_ref().pan_start_x = event.x
        self.im_ref().pan_start_y = event.y

        # Refresh the display to reflect panning
        self.update_display_image()
        
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