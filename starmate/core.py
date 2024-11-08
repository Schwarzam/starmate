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

from starmate.components.go_to_position import CoordinateInput

class Manager:
    def __init__(self):
        control.keep_in_memory = True
        control.simple_log = True
        control.callback = self.update_terminal
        
        
        
        self.active_image = None
        self.images = {}
        
        self.drawing_mode = False
        
        
        
        ctk.set_appearance_mode("dark")
        self.root = ctk.CTk()
        self.root.geometry("1360x900")
        self.load_font()
        
        self.root.title("starmate")

        self.init_mainframe()
        self.init_sidebar()
        
        
        
        parser = argparse.ArgumentParser(description="CLI for astroxs package")
        self.args = parser.parse_args()
        self.viewer = FITSViewer(self, self.root, self.args)
        
        self.sidebar_menu()
        
        self.setup_terminal()
        
        control.info("started starmate")
    
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
        self.main_frame = ctk.CTkFrame(self.root, fg_color=colors.bg)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Content frame inside main_frame for UI elements
        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color=colors.bg)
        self.content_frame.pack(side="left", fill="both", padx=10, pady=10)
        
        # Frame to hold the ComboBox and Change Image button
        selector_frame = ctk.CTkFrame(self.content_frame, fg_color=colors.bg)
        selector_frame.pack(side="top", padx=5, pady=10, fill="x")

        # ComboBox setup
        self.image_selector = ctk.CTkComboBox(
            selector_frame,
            height=25,
            width=400,
            fg_color=colors.bg,
            text_color=colors.text,
            font=fonts.sm,
            command=self.change_active_image,
        )
        self.image_selector.configure(values=[])
        self.image_selector.set("Select Image")
        
        self.image_selector.pack(side="left", padx=5)

    def setup_terminal(self):
        # Terminal Frame
        self.terminal_frame = ctk.CTkFrame(
            self.viewer.bottoml_frame
        )
        self.terminal_frame.pack(side="left", expand=True, fill="both")
        # Terminal-like text box
        self.terminal_textbox = ctk.CTkTextbox(
            self.terminal_frame, fg_color="black", text_color=colors.text, width=400
        )
        self.terminal_textbox.pack(padx=10, expand=True, fill="both")
        
    
    def init_sidebar(self):
        # Sidebar (initially hidden)
        self.sidebar_frame = ctk.CTkFrame(
            self.main_frame, fg_color=colors.bg
        )
        self.sidebar_frame.pack(side="right", expand=True, fill="both", padx=(0, 10), pady=10)
        
        self.sidebar_content = ctk.CTkFrame(
            self.sidebar_frame, fg_color=colors.dark
        )
        self.sidebar_content.pack(side="top", expand=True, fill="both", padx=10, pady=10)
        
        
        self.plot = ctk.CTkFrame(
            self.sidebar_frame, fg_color=colors.dark
        )
        self.plot.pack(side="bottom", anchor="s", fill="x", expand=True, padx=10)
        
        self.plot_frame = ctk.CTkFrame(
            self.plot, fg_color=colors.dark
        )
        self.plot_frame.pack(side="bottom", padx=10, fill="x")
        
        
    def sidebar_menu(self):
        # destroy the sidebar content
        for widget in self.sidebar_content.winfo_children():
            widget.destroy()
        
        draw_line_button = ctk.CTkButton(
            self.sidebar_content,
            text="Draw Line",
            command=self.toggle_drawing_mode,
            font=fonts.md,
            fg_color=colors.bg,
            text_color=colors.text,
        )
        draw_line_button.pack(pady=10, padx=10, side="left", anchor="nw")
        
        go_to_position_button = ctk.CTkButton(
            self.sidebar_content,
            text="Go to Position",
            command=lambda: CoordinateInput(
                self.sidebar_content,
                self.viewer.center_on_coordinate,
                self.sidebar_menu
            ),
            font=fonts.md,
            fg_color=colors.bg,
            text_color=colors.text,
        )
        go_to_position_button.pack(pady=10, padx=10, side="left", anchor="nw")

    def update_terminal(self, log_message):
        """Updates the terminal text box with lines from the terminal_lines array."""
        self.terminal_textbox.insert("end", log_message + "\n")  # Add each line followed by a newline
        self.terminal_textbox.see("end")  # Auto-scroll to the latest line
    
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
            control.info("Drawing mode enabled.")
        else:
            self.viewer.image_canvas.unbind("<Button-1>")
            self.viewer.image_canvas.bind("<Button-1>", self.viewer.start_pan)  # Re-bind for panning
            control.info("Drawing mode disabled.")
    
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