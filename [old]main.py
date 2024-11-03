import tkinter as tk
from tkinter import filedialog
from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image, ImageTk
import numpy as np

class FITSViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("FITS Viewer")

        # Variables
        self.image_data = None
        self.wcs_info = None
        self.zoom_level = 1.0
        self.pan_start_x = None
        self.pan_start_y = None
        self.offset_x = 0
        self.offset_y = 0

        # Setup UI
        self.setup_ui()
        
        # Start update loop for coordinates and preview
        self.update_coordinates()

    def setup_ui(self):
        # File path entry and browse button
        file_frame = tk.Frame(self.root)
        file_frame.pack(fill="x", padx=5, pady=5)
        self.file_path_entry = tk.Entry(file_frame, width=50)
        self.file_path_entry.pack(side="left", fill="x", expand=True)
        browse_button = tk.Button(file_frame, text="Browse FITS File", command=self.open_file_dialog)
        browse_button.pack(side="right")

        # Sliders for pmin and pmax
        slider_frame = tk.Frame(self.root)
        slider_frame.pack(fill="x", padx=5, pady=5)
        self.pmin_slider = tk.Scale(slider_frame, from_=0, to=100, orient="horizontal", label="pmin", command=self.update_image)
        self.pmin_slider.set(2)
        self.pmin_slider.pack(side="left", fill="x", expand=True)
        self.pmax_slider = tk.Scale(slider_frame, from_=0, to=100, orient="horizontal", label="pmax", command=self.update_image)
        self.pmax_slider.set(98)
        self.pmax_slider.pack(side="left", fill="x", expand=True)

        # Main canvas for image display with zoom control and panning
        self.canvas = tk.Canvas(self.root, width=500, height=500)
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)
        self.canvas.bind("<MouseWheel>", self.zoom)
        self.canvas.bind("<Button-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.pan_image)

        # Small canvas for preview
        preview_frame = tk.Frame(self.root)
        preview_frame.pack()
        tk.Label(preview_frame, text="Zoomed Preview", font=("Arial", 10)).pack()
        self.preview_canvas = tk.Canvas(preview_frame, width=50, height=50, borderwidth=1, relief="solid")
        self.preview_canvas.pack()

        # Coordinate display boxes
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
        """Open a file dialog to select a FITS file."""
        file_path = filedialog.askopenfilename(filetypes=[("FITS files", ["*.fz", "*fits"]), ("All files", "*.*")])
        if file_path:
            self.file_path_entry.delete(0, tk.END)
            self.file_path_entry.insert(0, file_path)
            self.load_fits(file_path)

    def load_fits(self, file_path, hdu_num = 1):
        """Load and display the FITS image, set up WCS."""
        try:
            with fits.open(file_path) as hdul:
                self.image_data = hdul[hdu_num].data
                self.wcs_info = WCS(hdul[hdu_num].header)
                
            self.zoom_level = 1.0  # Reset zoom level
            self.offset_x = self.offset_y = 0  # Reset offsets for panning
            self.update_image()
        except Exception as e:
            print(f"Error loading file: {e}")

    def update_image(self, event=None):
        """Update the image based on pmin and pmax values."""
        if self.image_data is not None:
            vmin = np.percentile(self.image_data, int(self.pmin_slider.get()))
            vmax = np.percentile(self.image_data, int(self.pmax_slider.get()))
            img_data = np.clip(self.image_data, vmin, vmax)
            img_data = (255 * (img_data - vmin) / (vmax - vmin)).astype(np.uint8)

            # Apply zoom without smoothing by using nearest neighbor interpolation
            img = Image.fromarray(img_data)
            img = img.resize((int(img.width * self.zoom_level), int(img.height * self.zoom_level)), Image.NEAREST)
            self.tk_img = ImageTk.PhotoImage(image=img)
            self.canvas.delete("all")
            self.canvas.create_image(self.offset_x, self.offset_y, anchor="nw", image=self.tk_img)
            
    def zoom(self, event):
        """Zoom in or out on the image."""
        if event.delta > 0:
            self.zoom_level *= 1.1  # Zoom in
        elif event.delta < 0:
            self.zoom_level /= 1.1  # Zoom out
        self.update_image()

    def start_pan(self, event):
        """Initialize panning."""
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def pan_image(self, event):
        """Pan the image by dragging."""
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        self.offset_x += dx
        self.offset_y += dy
        self.update_image()
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def get_zoomed_preview(self, x, y):
        """Get a 50x50 zoomed view around the current mouse location."""
        half_size = 25  # Half the preview size for centering
        x0, y0 = max(0, x - half_size), max(0, y - half_size)
        x1, y1 = min(self.image_data.shape[1], x + half_size), min(self.image_data.shape[0], y + half_size)
        
        # Extract the region and resize to fill the preview canvas
        region = self.image_data[y0:y1, x0:x1]
        img = Image.fromarray((255 * (region - region.min()) / (region.max() - region.min())).astype(np.uint8))
        zoomed_img = img.resize((50, 50), Image.NEAREST)
        self.preview_img = ImageTk.PhotoImage(zoomed_img)
        self.preview_canvas.create_image(0, 0, anchor="nw", image=self.preview_img)

    def update_coordinates(self):
        """Continuously update coordinates based on mouse position."""
        if self.image_data is not None and self.wcs_info is not None:
            x, y = (self.canvas.winfo_pointerx() - self.canvas.winfo_rootx() - self.offset_x) / self.zoom_level, \
                   (self.canvas.winfo_pointery() - self.canvas.winfo_rooty() - self.offset_y) / self.zoom_level
            x_int, y_int = int(x), int(y)
            if 0 <= x_int < self.image_data.shape[1] and 0 <= y_int < self.image_data.shape[0]:
                pixel_value = self.image_data[y_int, x_int]
                ra_dec = self.wcs_info.wcs_pix2world([[x, y]], 1)[0]
                ra, dec = ra_dec[0], ra_dec[1]
                self.x_label.config(text=f"X: {x:.2f}")
                self.y_label.config(text=f"Y: {y:.2f}")
                self.ra_label.config(text=f"RA: {ra:.4f}")
                self.dec_label.config(text=f"Dec: {dec:.4f}")
                self.pixel_value_label.config(text=f"Value: {pixel_value}")
                
                # Update zoomed preview
                self.get_zoomed_preview(x_int, y_int)
        self.root.after(50, self.update_coordinates)  # Schedule the next update

    def get_interpolated_value(self, x, y):
        """Perform bilinear interpolation to get the pixel value at a subpixel location."""
        x0, y0 = int(x), int(y)
        dx, dy = x - x0, y - y0
        if 0 <= x0 < self.image_data.shape[1] - 1 and 0 <= y0 < self.image_data.shape[0] - 1:
            top_left = self.image_data[y0, x0]
            top_right = self.image_data[y0, x0 + 1]
            bottom_left = self.image_data[y0 + 1, x0]
            bottom_right = self.image_data[y0 + 1, x0 + 1]
            top = top_left * (1 - dx) + top_right * dx
            bottom = bottom_left * (1 - dx) + bottom_right * dx
            return top * (1 - dy) + bottom * dy
        return self.image_data[y0, x0]

root = tk.Tk()
viewer = FITSViewer(root)
root.mainloop()



        
    # def update_display_image(self):
    #     """Use the cached image data to update the display, optimizing performance."""
    #     if self.cached_img_data is None:
    #         return  # If no cache is available, skip

    #     img = Image.fromarray(self.cached_img_data)
    #     max_dim = max(img.width, img.height)
    #     scale_factor = min(MAX_DISPLAY_SIZE / max_dim, 1)
    #     new_width = int(img.width * scale_factor * self.im_ref().zoom_level)
    #     new_height = int(img.height * scale_factor * self.im_ref().zoom_level)
    #     img = img.resize((new_width, new_height), Image.NEAREST)
        
    #     self.tk_img = ImageTk.PhotoImage(image=img)
    #     self.image_canvas.delete("all")
    #     self.image_canvas.create_image(self.im_ref().offset_x, self.im_ref().offset_y, anchor="nw", image=self.tk_img)

    # def zoom(self, event):
    #     """Zoom in or out relative to the mouse position."""
    #     zoom_factor = 1.1 if event.delta > 0 else 0.9
    #     new_zoom_level = self.im_ref().zoom_level * zoom_factor

    #     # Only update display if zoom level has changed
    #     if abs(new_zoom_level - self.last_zoom_level) > 0.05:
    #         x_mouse = (event.x - self.im_ref().offset_x) / self.im_ref().zoom_level
    #         y_mouse = (event.y - self.im_ref().offset_y) / self.im_ref().zoom_level

    #         self.im_ref().zoom_level = new_zoom_level
    #         self.last_zoom_level = new_zoom_level

    #         # Adjust offsets to zoom relative to the mouse position
    #         self.im_ref().offset_x = event.x - x_mouse * self.im_ref().zoom_level
    #         self.im_ref().offset_y = event.y - y_mouse * self.im_ref().zoom_level
    #         self.update_display_image()
