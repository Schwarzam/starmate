import tkinter as tk
from tkinter import filedialog, ttk
from astropy.io import fits
from PIL import Image, ImageTk
import numpy as np
import os
from image import FitsImage
from PIL import ImageDraw

import tkinter.font as tkFont

import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from skimage.draw import line
import pyglet

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

MAX_DISPLAY_SIZE = 2000  # Limit to a maximum display size to reduce lag

class FITSViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("FITS Viewer")
        self.sidebar_visible = False  # Track if the sidebar is visible

        # Set the default font style
        font_path = os.path.join(os.path.dirname(__file__), "JetBrainsMono-VariableFont_wght.ttf")
        pyglet.font.add_file(str(font_path))
        # Verify if the font was loaded
        if pyglet.font.have_font("JetBrains Mono"):
            print("Font loaded successfully.")
        else:
            print("Font not found.")
            
        custom_font = tkFont.Font(family="JetBrains Mono")  # Set size as needed
        self.root.option_add("*Font", custom_font)
        
        
        # Create the main container frame
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        # Sidebar (initially hidden)
        self.sidebar_frame = tk.Frame(self.main_frame, width=200, relief="sunken", borderwidth=2)
        self.sidebar_frame.pack(side="right", fill="y")
        self.sidebar_frame.pack_forget()  # Start with the sidebar hidden
        
        # Initialize the Combobox to select active images
        self.image_selector = ttk.Combobox(self.main_frame, state="readonly", postcommand=self.update_image_list)
        self.image_selector.pack(side="top", padx=10, pady=5)
        self.image_selector.bind("<<ComboboxSelected>>", self.change_active_image)
        
        # Bind the "1" key to toggle coordinate freezing
        self.root.bind("1", self.toggle_freeze_coords)
        
        self.coords_frozen = False  # Track if coordinates are frozen
        
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
        self.update_thumbnail()

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
        coord_frame.pack(side="left", anchor="w", padx=10, pady=10)
        
        self.info_text = tk.Text(
            coord_frame,
            width=30,
            height=10,
            borderwidth=0,  # Removes border
            highlightthickness=0,  # Removes highlight border
            font=("Courier", 10),  # Set font to monospace
            background=coord_frame.cget("background")  # Match the background of parent frame
        )
        self.info_text.pack(side="left", anchor="w", padx=5, pady=5)
        
        # Thumbnail canvas
        self.thumbnail_canvas = tk.Canvas(coord_frame, width=100, height=100)
        self.thumbnail_canvas.pack(side="left", padx=5, pady=5)

        # Matplotlib plot canvas
        self.plot_frame = tk.Frame(coord_frame)
        self.plot_frame.pack(side="left", padx=5, pady=5)
        
    def update_image_list(self):
        """Update the combobox with loaded images."""
        self.image_selector['values'] = list(self.images.keys())
        if self.active_image:
            self.image_selector.set(self.active_image)
            
            
    def change_active_image(self, event):
        """Change the active image based on the combobox selection."""
        selected_image = self.image_selector.get()
        if selected_image in self.images:
            self.active_image = selected_image
            self.update_display_image()
    
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

    def im_ref(self) -> FitsImage:
        if self.active_image is None:
            return None
        return self.images[self.active_image]

    def load_fits(self, file_path):
        try:
            hdu = int(self.hdu_numinput.get())
            image_name = os.path.basename(file_path)
            im = FitsImage.load(file_path, hdu_index=hdu)
            
            im.plot_frame = self.plot_frame
            
            self.images[image_name] = im
            self.active_image = image_name
            
            self.update_display_image()
 
        except Exception as e:
            print(f"Error loading file: {e}")

    def update_image_cache(self):
        if self.active_image is None:
            return
        self.im_ref().update_image_cache(
            self.pmin_entry.get(), 
            self.pmax_entry.get()
        )
        self.update_display_image()

    def update_display_image(self):
        """Efficiently update the display by only rendering the visible portion of the image."""
        self.tk = self.im_ref().update_display_image(self.image_canvas)
        self.image_canvas.delete("all")
        self.image_canvas.create_image(0, 0, anchor="nw", image=self.tk)
        
    def update_thumbnail(self):
        """Update the thumbnail to show the area around the cursor."""
        if self.coords_frozen:
            self.root.after(50, self.update_thumbnail)
            return
        
        if self.active_image is None:
            self.root.after(50, self.update_thumbnail)
            return
        
        thumbnail_image = self.im_ref().get_thumbnail(
            self.image_canvas, 
            size = (10, 10),
            final_size = (100, 100)
        )
        
        self.thumbnail_photo = ImageTk.PhotoImage(thumbnail_image)
        self.thumbnail_canvas.create_image(0, 0, anchor="nw", image=self.thumbnail_photo)
        self.root.after(50, self.update_thumbnail)
        

    def zoom(self, event):
        """Zoom in or out relative to the mouse position."""
        if not self.active_image:
            return
        self.im_ref().zoom(event)
        self.update_display_image()

    def start_pan(self, event):
        """Start panning by recording the initial click position."""
        if not self.active_image:
            return
        self.im_ref().pan_start_x = event.x
        self.im_ref().pan_start_y = event.y

    def pan_image(self, event):
        """Drag the image in the intuitive direction based on mouse movement."""
        if not self.active_image or self.drawing_mode:
            return
        self.im_ref().pan_image(event)
        self.update_display_image()
        
    def toggle_drawing_mode(self):
        """Enable or disable line drawing mode."""
        self.drawing_mode = not self.drawing_mode
        if self.drawing_mode:
            self.im_ref().line_start = None
            self.im_ref().line_end = None
            self.image_canvas.unbind("<Button-1>")
            self.image_canvas.bind("<Button-1>", self.handle_canvas_click)  # Bind for drawing
            print("Drawing mode enabled.")
        else:
            self.image_canvas.unbind("<Button-1>")
            self.image_canvas.bind("<Button-1>", self.start_pan)  # Re-bind for panning
            print("Drawing mode disabled.")
    

    def handle_canvas_click(self, event):
        """Handle clicks on the canvas for drawing a line between two points."""
        if not self.drawing_mode:
            return
        
        update = self.im_ref().handle_canvas_click(
            event, 
            self.image_canvas, 
            self.update_line_position,
            self.toggle_drawing_mode
        )
        if update:
            self.update_display_image()  # Update display to finalize the line

    def update_line_position(self, event):
        """Update the end point of the line as the mouse moves for real-time drawing."""
        if self.im_ref().update_line_position(event):
            self.update_display_image()
        
    def toggle_freeze_coords(self, event):
        """Toggle freezing of coordinates display."""
        self.coords_frozen = not self.coords_frozen
        if self.coords_frozen:
            print("Coordinates frozen.")
        else:
            print("Coordinates unfrozen.")
            self.update_coordinates()  # Ensure coordinates start updating again if unfrozen

    
    def update_coordinates(self):
        if self.coords_frozen:
            # Skip updating if coordinates are frozen
            return
        
        if not self.active_image:
            # Schedule the next update
            self.root.after(50, self.update_coordinates)
            return 
        
        # Get mouse position relative to the canvas
        x_canvas = self.image_canvas.winfo_pointerx() - self.image_canvas.winfo_rootx()
        y_canvas = self.image_canvas.winfo_pointery() - self.image_canvas.winfo_rooty()

        # Calculate the actual position on the full image, accounting for zoom and offsets
        x_image = (x_canvas + self.im_ref().offset_x) / self.im_ref().zoom_level
        y_image = (y_canvas + self.im_ref().offset_y) / self.im_ref().zoom_level
        x_int, y_int = round(x_image) - 1, round(y_image) - 1

        final_text = ''
        
        ra_value = ''
        dec_value = ''
        x_value = ''
        y_value = ''
        pixel_value = ''
        
        # Ensure coordinates are within the image boundaries
        if 0 <= x_int < self.im_ref().image_data.shape[1] and 0 <= y_int < self.im_ref().image_data.shape[0]:
            # Get pixel value from the full-resolution data
            pixel_value = self.im_ref().image_data[y_int, x_int]
            
            # Calculate RA and Dec if WCS information is available
            if hasattr(self.im_ref(), 'wcs_info') and self.im_ref().wcs_info:
                ra_dec = self.im_ref().wcs_info.wcs_pix2world([[x_image, y_image]], 1)[0]
                ra, dec = ra_dec[0], ra_dec[1]
                ra_value = f"{ra:.4f}"
                dec_value = f"{dec:.4f}"
            else:
                # Set RA/Dec to None if no WCS information
                ra_value = "N/A"
                dec_value = "N/A"
            
            # Update coordinate labels
            x_value = f"{x_image:.2f}"
            y_value = f"{y_image:.2f}"
            pixel_value = f"{pixel_value:.4f}"
        else:
            # Clear labels if outside image bounds
            x_value = "N/A"
            y_value = "N/A"
            ra_value = "N/A"
            dec_value = "N/A"
            pixel_value = "N/A"
            
        # Format text
        final_text = f"""\
|------------------------|
|      Coordinates       |
|------------------------|
| x     | {x_value:<13}  |
| y     | {y_value:<13}  |
| RA    | {ra_value:<13}  |
| Dec   | {dec_value:<13}  |
| Pixel | {pixel_value:<13}  |
|------------------------|
"""

        # Enable editing to update the text, then disable it again to make it read-only
        self.info_text.configure(state='normal')
        self.info_text.delete(1.0, tk.END)  # Clear previous content
        self.info_text.insert(tk.END, final_text)  # Insert new content
        self.info_text.configure(state='disabled')  # Make read-only again

        # Schedule the next update
        self.root.after(50, self.update_coordinates)

root = tk.Tk()
viewer = FITSViewer(root)
root.mainloop()