import argparse

import customtkinter as ctk

import tkinter.font as tkFont

import os
import pyglet

import starmate
from starmate.fonts.font_manager import FontManager
from starmate.fits_viewer import FITSViewer

from starmate.image import FitsImage
from starmate.variables import colors, fonts

from logpool import control

class Manager:
    def __init__(self):
        self.root = ctk.CTk()
        self.load_font()
        
        self.root.title("starmate")
        self.sidebar_visible = False  # Track if the sidebar is visible
        
        self.init_mainframe()
        self.init_sidebar()
        
        self.sidebar_menu()
        
        parser = argparse.ArgumentParser(description="CLI for astroxs package")
        self.args = parser.parse_args()

        self.active_image = None
        self.images = {}
        
        self.drawing_mode = False
        
        self.viewer = FITSViewer(self, self.root, self.args)

        

    
    def active_im(self) -> bool:
        if self.active_image is None:
            return False 
        return True
    
    def im_ref(self) -> FitsImage:
        if self.active_im():
            return self.images[self.active_image]

    def start(self):
        self.root.mainloop()
        
    def init_mainframe(self):
        # Main Frame using ctk
        self.main_frame = ctk.CTkFrame(self.root, fg_color=colors.bg, width=1600)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Frame to hold the ComboBox and Change Image button
        selector_frame = ctk.CTkFrame(self.main_frame, fg_color=colors.bg)
        selector_frame.pack(side="top", padx=10, pady=10, fill="x")

        # ComboBox setup
        self.image_selector = ctk.CTkComboBox(
            selector_frame,
            height=30,
            width=400,
            fg_color=colors.bg,
            text_color=colors.text,
            font=fonts.md,
        )
        self.image_selector.configure(values=[])
        self.image_selector.set("Select Image")
        
        self.image_selector.pack(side="left", padx=5, pady=10)

        # Button to manually change the image based on ComboBox selection
        change_image_button = ctk.CTkButton(
            selector_frame,
            text=f"Change Image",
            command=self.change_active_image,
            font=fonts.md,
            fg_color=colors.accent,
            text_color=colors.text,
        )
        change_image_button.pack(side="left", padx=10)


    def init_sidebar(self):
        # Sidebar (initially hidden)
        self.sidebar_frame = ctk.CTkFrame(
            self.main_frame, width=200, fg_color=colors.bg
        )
        self.sidebar_frame.pack(side="right", fill="y", padx=10, pady=10)
        self.sidebar_frame.pack_forget()  # Start with the sidebar hidden
        
    def sidebar_menu(self):
        # Sidebar Content with padding
        ctk.CTkLabel(
            self.sidebar_frame,
            text="Sidebar Content",
            fg_color=colors.bg,
            text_color=colors.text,
            font=fonts.lg,
        ).pack(pady=10)

        draw_line_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Draw Line",
            command=self.toggle_drawing_mode,
            font=fonts.md,
            fg_color=colors.accent,
            text_color=colors.text,
        )
        draw_line_button.pack(pady=5)

    
    def toggle_drawing_mode(self):
        """Enable or disable line drawing mode."""
        if not self.active_im():
            return
        
        self.drawing_mode = not self.drawing_mode
        if self.drawing_mode:
            self.im_ref().line_start = None
            self.im_ref().line_end = None
            self.viewer.image_canvas.unbind("<Button-1>")
            self.viewer.image_canvas.bind(
                "<Button-1>", self.viewer.handle_canvas_click
            )  # Bind for drawing
            print("Drawing mode enabled.")
        else:
            self.viewer.image_canvas.unbind("<Button-1>")
            self.viewer.image_canvas.bind("<Button-1>", self.viewer.start_pan)  # Re-bind for panning
            print("Drawing mode disabled.")
    
    
    def toggle_sidebar(self):
        """Toggle the visibility of the sidebar."""
        if self.sidebar_visible:
            self.sidebar_frame.pack_forget()  # Hide the sidebar
        else:
            self.sidebar_frame.pack(side="right", fill="y")  # Show the sidebar
        self.sidebar_visible = not self.sidebar_visible  # Update the visibility status

    def change_active_image(self, event=None):
        """Change the active image based on the combobox selection."""
        print("change_active_image")
        selected_image = self.image_selector.get()  # Retrieve the selected image name
        if selected_image in self.images:  # Check if the selected image is valid
            self.active_image = selected_image
            self.viewer.update_display_image()  # Refresh the display to show the selected image
        
    def load_font(self):
        """Load the custom font and add it to the pyglet font registry. """
        # Load the custom font with pyglet
        font_dir = os.path.join(starmate.__path__[0], "fonts", "fonts")
        font_path = os.path.join(font_dir, "JetBrainsMonoNerdFont-Regular.ttf")
        pyglet.font.add_file(font_path)

        success = FontManager.load_font(font_path)
        if not success:
            raise Exception("Failed to load custom font")


manager = Manager()