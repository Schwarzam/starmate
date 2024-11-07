import customtkinter as ctk

import tkinter as tk

from tkinter import filedialog
from tkinter import font as tkFont
from astropy.io import fits
from PIL import Image, ImageTk
import numpy as np
import os
import pyglet

from starmate.image import FitsImage
from starmate.variables import fonts, colors

import starmate

MAX_DISPLAY_SIZE = 2000  # Limit to a maximum display size to reduce lag

class FITSViewer:
    def __init__(self, manager, root, args):
        self.root = root
        self.manager : starmate.core.Manager = manager

        
        # Bind key to toggle coordinate freezing
        self.root.bind("1", self.toggle_freeze_coords)

        # Additional attributes
        self.coords_frozen = False
        
        self.line_start = None
        self.line_end = None
        self.line_id = None

        # Content frame inside main_frame for UI elements
        self.content_frame = ctk.CTkFrame(self.manager.main_frame, fg_color=colors.bg)
        self.content_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        # Setup main UI components
        self.setup_ui()

        self.update_coordinates()
        self.update_thumbnail()

    def setup_ui(self):
        # Main file frame and canvas inside content_frame with padding
        file_frame = ctk.CTkFrame(self.content_frame, fg_color=colors.bg)
        file_frame.pack(fill="x", padx=10, pady=10)

        self.file_path_entry = ctk.CTkEntry(
            file_frame,
            width=40,
            fg_color=colors.bg,
            text_color=colors.text,
            font=fonts.md,
        )
        self.file_path_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)

        browse_button = ctk.CTkButton(
            file_frame,
            text="Browse FITS File",
            command=self.open_file_dialog,
            font=fonts.md,
            fg_color=colors.accent,
            text_color=colors.text,
        )
        browse_button.pack(side="right", padx=5, pady=5)


        # pmin and pmax inputs with an "Apply" button with padding
        input_frame = ctk.CTkFrame(self.content_frame, fg_color=colors.bg)
        input_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            input_frame,
            text="pmin:",
            fg_color=colors.bg,
            text_color=colors.text,
            font=fonts.md,
        ).pack(side="left", padx=5)
        self.pmin_entry = ctk.CTkEntry(
            input_frame,
            width=50,
            fg_color=colors.bg,
            text_color=colors.text,
            font=fonts.md,
        )
        self.pmin_entry.insert(0, "0")
        self.pmin_entry.pack(side="left", padx=5)

        ctk.CTkLabel(
            input_frame,
            text="pmax:",
            fg_color=colors.bg,
            text_color=colors.text,
            font=fonts.md,
        ).pack(side="left", padx=5)
        self.pmax_entry = ctk.CTkEntry(
            input_frame,
            width=50,
            fg_color=colors.bg,
            text_color=colors.text,
            font=fonts.md,
        )
        self.pmax_entry.insert(0, "100")
        self.pmax_entry.pack(side="left", padx=5)

        apply_button = ctk.CTkButton(
            input_frame,
            text="Apply",
            command=self.update_image_cache,
            font=fonts.md,
            fg_color=colors.accent,
            text_color=colors.text,
        )
        apply_button.pack(side="left", padx=10)

        # Sidebar Toggle Button
        toggle_sidebar_button = ctk.CTkButton(
            input_frame,
            text="Tools",
            command=self.manager.toggle_sidebar,
            font=fonts.md,
            fg_color=colors.accent,
            text_color=colors.text,
        )
        toggle_sidebar_button.pack(side="right", padx=10)

        # Canvas to display the FITS image with padding
        self.image_canvas = ctk.CTkCanvas(
            self.content_frame, width=500, height=500, bg=colors.bg
        )
        self.image_canvas.pack(fill="both", expand=True, padx=10, pady=10)
        self.image_canvas.bind("<MouseWheel>", self.zoom)
        self.image_canvas.bind("<Button-1>", self.start_pan)
        self.image_canvas.bind("<B1-Motion>", self.pan_image)

        # Create coord_frame, thumbnail, and plot_frame inside content_frame
        coord_frame = ctk.CTkFrame(self.content_frame, fg_color=colors.bg)
        coord_frame.pack(side="left", padx=10, pady=10)

        # Coordinate labels in coord_frame
        self.x_label = ctk.CTkLabel(
            coord_frame,
            text="X:",
            fg_color=colors.bg,
            text_color=colors.text,
            font=fonts.md,
        )
        self.x_value = ctk.CTkLabel(
            coord_frame,
            text="N/A",
            fg_color=colors.bg,
            text_color=colors.text,
            font=fonts.md,
        )
        self.y_label = ctk.CTkLabel(
            coord_frame,
            text="Y:",
            fg_color=colors.bg,
            text_color=colors.text,
            font=fonts.md,
        )
        self.y_value = ctk.CTkLabel(
            coord_frame,
            text="N/A",
            fg_color=colors.bg,
            text_color=colors.text,
            font=fonts.md,
        )
        self.ra_label = ctk.CTkLabel(
            coord_frame,
            text="RA:",
            fg_color=colors.bg,
            text_color=colors.text,
            font=fonts.md,
        )
        self.ra_value = ctk.CTkLabel(
            coord_frame,
            text="N/A",
            fg_color=colors.bg,
            text_color=colors.text,
            font=fonts.md,
        )
        self.dec_label = ctk.CTkLabel(
            coord_frame,
            text="Dec:",
            fg_color=colors.bg,
            text_color=colors.text,
            font=fonts.md,
        )
        self.dec_value = ctk.CTkLabel(
            coord_frame,
            text="N/A",
            fg_color=colors.bg,
            text_color=colors.text,
            font=fonts.md,
        )
        self.pixel_label = ctk.CTkLabel(
            coord_frame,
            text="Pixel:",
            fg_color=colors.bg,
            text_color=colors.text,
            font=fonts.md,
        )
        self.pixel_value = ctk.CTkLabel(
            coord_frame,
            text="N/A",
            fg_color=colors.bg,
            text_color=colors.text,
            font=fonts.md,
        )

        labels = [
            (self.x_label, self.x_value),
            (self.y_label, self.y_value),
            (self.ra_label, self.ra_value),
            (self.dec_label, self.dec_value),
            (self.pixel_label, self.pixel_value),
        ]

        for row, (label, value) in enumerate(labels):
            label.grid(
                row=row, column=0, padx=10, pady=1, sticky="w"
            )  # Align label to the left (west)
            value.grid(
                row=row, column=1, padx=10, pady=1, sticky="e"
            )  # Align value to the right (east)

        # Add a button below the labels to copy RA and Dec values
        copy_button = ctk.CTkButton(
            coord_frame,
            text="Copy RA DEC",
            command=self.copy_ra_dec_to_clipboard,
            font=fonts.md,
            fg_color=colors.accent,
            text_color=colors.text,
        )
        copy_button.grid(row=len(labels), column=0, columnspan=2, padx=10, pady=10)
        
        thumbnail_frame = ctk.CTkFrame(self.content_frame, fg_color=colors.bg)
        thumbnail_frame.pack(side="right", padx=10, pady=10)

        plot_frame = ctk.CTkFrame(self.content_frame, fg_color=colors.bg)
        plot_frame.pack(side="right", padx=10, pady=10)
        
        # Thumbnail canvas in thumbnail_frame
        self.thumbnail_canvas = ctk.CTkCanvas(
            thumbnail_frame, width=100, height=100, bg=colors.bg
        )
        self.thumbnail_canvas.pack(padx=10, pady=10)

        # Plot frame in plot_frame
        self.plot_frame = ctk.CTkFrame(plot_frame, fg_color=colors.bg)
        self.plot_frame.pack(padx=10, pady=10)

    def copy_ra_dec_to_clipboard(self):
        ra_text = self.ra_value.cget("text")
        dec_text = self.dec_value.cget("text")
        clipboard_text = f"{ra_text} {dec_text}"
        self.root.clipboard_clear()
        self.root.clipboard_append(clipboard_text)
        print(f"Copied to clipboard: {clipboard_text}")

    def update_image_list(self):
        """Update the combobox with loaded images."""
        # Ensure that the values are assigned directly to the CTkComboBox widget
        self.manager.image_selector.configure(values=list(self.manager.images.keys()))
        if self.manager.active_im():
            self.manager.image_selector.set(self.manager.active_image)

    def change_active_image(self, event=None):
        """Change the active image based on the combobox selection."""
        print("change_active_image")
        selected_image = self.manager.image_selector.get()  # Retrieve the selected image name
        if selected_image in self.manager.images:  # Check if the selected image is valid
            self.active_image = selected_image
            self.update_display_image()  # Refresh the display to show the selected image

    def open_file_dialog(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("FITS file", ["*.fz", "*fits"]), ("All files", "*.*")]
        )
        if file_path:
            self.file_path_entry.delete(0, tk.END)
            self.file_path_entry.insert(0, file_path)
            self.load_fits(file_path)

    def load_hdu(self, data, header, image_name):
        im = FitsImage.load_f_data(data, header, manager=self.manager)

        im.plot_frame = self.plot_frame

        self.manager.images[image_name] = im
        self.manager.active_image = image_name
    
    def load_fits(self, file_path):
        try:
            image_name = os.path.basename(file_path)
            
            hdus = fits.open(file_path)  # Check if the file is a valid FITS file
            for hdu_num, hdu in enumerate(hdus):
                # Check if the HDU has image data
                if hdu.data is not None and hdu.is_image:
                    if hdu.data.ndim == 3:
                        for i in range(hdu.data.shape[0]):
                            print(hdu.data[i].shape)
                            self.load_hdu(hdu.data[i], hdu.header, f"[HDU {hdu_num}][dim {i}] - {image_name}")
                    
                    else:
                        self.load_hdu(hdu.data, hdu.header, f"[HDU {hdu_num}] - {image_name}")

            # Manually update the image list
            self.update_image_list()
            self.update_display_image()

        except Exception as e:
            print(f"Error loading file: {e}")

    def update_image_cache(self):
        if not self.manager.active_im():
            return
        self.manager.im_ref().update_image_cache(self.pmin_entry.get(), self.pmax_entry.get())
        self.update_display_image()

    def update_display_image(self):
        """Efficiently update the display by only rendering the visible portion of the image."""
        self.tk = self.manager.im_ref().update_display_image(self.image_canvas)
        self.image_canvas.delete("all")
        self.image_canvas.create_image(0, 0, anchor="nw", image=self.tk)

    def update_thumbnail(self):
        """Update the thumbnail to show the area around the cursor."""
        if self.coords_frozen:
            self.root.after(50, self.update_thumbnail)
            return

        if not self.manager.active_im():
            self.root.after(50, self.update_thumbnail)
            return

        thumbnail_image = self.manager.im_ref().get_thumbnail(
            self.image_canvas, size=(10, 10), final_size=(100, 100)
        )

        self.thumbnail_photo = ImageTk.PhotoImage(thumbnail_image)
        self.thumbnail_canvas.create_image(
            0, 0, anchor="nw", image=self.thumbnail_photo
        )
        self.root.after(50, self.update_thumbnail)

    def zoom(self, event):
        """Zoom in or out relative to the mouse position."""
        if not self.manager.active_im():
            return
        self.manager.im_ref().zoom(event)
        self.update_display_image()

    def start_pan(self, event):
        """Start panning by recording the initial click position."""
        if not self.manager.active_im():
            return
        self.manager.im_ref().pan_start_x = event.x
        self.manager.im_ref().pan_start_y = event.y

    def pan_image(self, event):
        """Drag the image in the intuitive direction based on mouse movement."""
        if not self.manager.active_im() or self.manager.drawing_mode:
            return
        self.manager.im_ref().pan_image(event)
        self.update_display_image()

    def handle_canvas_click(self, event):
        """Handle clicks on the canvas for drawing a line between two points."""
        if not self.manager.drawing_mode:
            return

        update = self.manager.im_ref().handle_canvas_click(
            event,
            self.image_canvas,
            self.update_line_position
        )
        if update:
            self.update_display_image()  # Update display to finalize the line

    def update_line_position(self, event):
        """Update the end point of the line as the mouse moves for real-time drawing."""
        if self.manager.im_ref().update_line_position(event):
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
            return

        if not self.manager.active_im():
            # Schedule the next update
            self.root.after(50, self.update_coordinates)
            return

        # Get mouse position relative to the canvas
        x_canvas = self.image_canvas.winfo_pointerx() - self.image_canvas.winfo_rootx()
        y_canvas = self.image_canvas.winfo_pointery() - self.image_canvas.winfo_rooty()

        # Calculate the actual position on the full image, accounting for zoom and offsets
        x_image = (x_canvas + self.manager.im_ref().offset_x) / self.manager.im_ref().zoom_level
        y_image = (y_canvas + self.manager.im_ref().offset_y) / self.manager.im_ref().zoom_level
        x_int, y_int = round(x_image) - 1, round(y_image) - 1

        # Default values
        x_value, y_value, ra_value, dec_value, pixel_value = (
            "N/A",
            "N/A",
            "N/A",
            "N/A",
            "N/A",
        )

        # Ensure coordinates are within the image boundaries
        if (
            0 <= x_int < self.manager.im_ref().image_data.shape[1]
            and 0 <= y_int < self.manager.im_ref().image_data.shape[0]
        ):
            pixel_value = f"{self.manager.im_ref().image_data[y_int, x_int]:.4f}"

            # Calculate RA and Dec if WCS information is available
            if hasattr(self.manager.im_ref(), "wcs_info") and self.manager.im_ref().wcs_info:
                ra_dec = self.manager.im_ref().wcs_info.wcs_pix2world([[x_image, y_image]], 1)[
                    0
                ]
                ra_value, dec_value = f"{ra_dec[0]:.4f}", f"{ra_dec[1]:.4f}"

            # Update coordinate labels
            x_value = f"{x_image:.2f}"
            y_value = f"{y_image:.2f}"

        # Update label text
        self.x_value.configure(text=x_value)
        self.y_value.configure(text=y_value)
        self.ra_value.configure(text=ra_value)
        self.dec_value.configure(text=dec_value)
        self.pixel_value.configure(text=pixel_value)

        # Schedule the next update
        self.root.after(50, self.update_coordinates)
