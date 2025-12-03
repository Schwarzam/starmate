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
from starmate.measurements import MeasurementManager

from logpool import control

from starmate.components.go_to_position import CoordinateInput
from starmate.components.macth_frames import MatchFrames
from starmate.components.query_object import QueryObject

class Manager:
    def __init__(self):
        control.keep_in_memory = True
        control.simple_log = True
        control.callback = self.update_terminal
        
        
        
        self.active_image = None
        self.images = {}
        self.drawing_mode = False
        self.measurement_manager = MeasurementManager()

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
            height=30,
            width=400,
            fg_color=colors.bg,
            text_color=colors.text,
            font=fonts.md,
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
            self.terminal_frame, fg_color="black", text_color=colors.text, width=400, font=fonts.sm
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
        # Clear existing sidebar content
        for widget in self.sidebar_content.winfo_children():
            widget.destroy()

        # First Row: Measurement Tools
        row1_frame = ctk.CTkFrame(self.sidebar_content, fg_color=colors.bg)
        row1_frame.pack(fill="x", expand=True, pady=(10, 5), padx=10)

        row1_label = ctk.CTkLabel(
            row1_frame,
            text="Measurement Tools",
            font=fonts.md,
            text_color=colors.text
        )
        row1_label.pack(side="top", anchor="w", padx=10)

        # Measurement tool buttons in a sub-frame
        measurement_buttons_frame = ctk.CTkFrame(row1_frame, fg_color=colors.bg)
        measurement_buttons_frame.pack(side="top", fill="x", padx=10, pady=5)

        measure_line_button = ctk.CTkButton(
            measurement_buttons_frame,
            text="Line",
            command=lambda: self.start_measurement('line'),
            font=fonts.sm,
            fg_color=colors.blue,
            text_color=colors.text,
            width=80
        )
        measure_line_button.pack(side="left", padx=2)

        measure_circle_button = ctk.CTkButton(
            measurement_buttons_frame,
            text="Circle",
            command=lambda: self.start_measurement('circle'),
            font=fonts.sm,
            fg_color=colors.blue,
            text_color=colors.text,
            width=80
        )
        measure_circle_button.pack(side="left", padx=2)

        measure_ellipse_button = ctk.CTkButton(
            measurement_buttons_frame,
            text="Ellipse",
            command=lambda: self.start_measurement('ellipse'),
            font=fonts.sm,
            fg_color=colors.blue,
            text_color=colors.text,
            width=80
        )
        measure_ellipse_button.pack(side="left", padx=2)

        view_measurements_button = ctk.CTkButton(
            measurement_buttons_frame,
            text="View Table",
            command=self.show_measurement_table,
            font=fonts.sm,
            fg_color=colors.green,
            text_color=colors.text,
            width=80
        )
        view_measurements_button.pack(side="left", padx=2)

        # Additional tool buttons
        tools_frame = ctk.CTkFrame(row1_frame, fg_color=colors.bg)
        tools_frame.pack(side="top", fill="x", padx=10, pady=5)

        go_to_position_button = ctk.CTkButton(
            tools_frame,
            text="Go to Position",
            command=lambda: CoordinateInput(
                self.sidebar_content,
                self.viewer.center_on_coordinate,
                self.sidebar_menu
            ),
            font=fonts.sm,
            fg_color=colors.blue,
            text_color=colors.text,
            width=120
        )
        go_to_position_button.pack(side="left", padx=2)

        create_cutout_button = ctk.CTkButton(
            tools_frame,
            text="Create Cutout",
            command=self.start_cutout_selection,
            font=fonts.sm,
            fg_color=colors.blue,
            text_color=colors.text,
            width=120
        )
        create_cutout_button.pack(side="left", padx=2)

        # Second Row: Frame Tools
        row2_frame = ctk.CTkFrame(self.sidebar_content, fg_color=colors.bg)
        row2_frame.pack(fill="x", expand=True, pady=(10, 5), padx=10)

        row2_label = ctk.CTkLabel(
            row2_frame,
            text="Frame Tools",
            font=fonts.md,
            text_color=colors.text
        )
        row2_label.pack(side="top", anchor="w", padx=10)

        match_frames_button = ctk.CTkButton(
            row2_frame,
            text="Match Frames",
            command=lambda: MatchFrames(
                self.sidebar_content,
                self.sidebar_menu,
                manager=self
            ),
            font=fonts.md,
            fg_color=colors.blue,
            text_color=colors.text
        )
        match_frames_button.pack(side="left", padx=10, pady=5)

        # Third Row: Online Query Tools
        row3_frame = ctk.CTkFrame(self.sidebar_content, fg_color=colors.bg)
        row3_frame.pack(fill="x", expand=True, pady=(10, 5), padx=10)

        row3_label = ctk.CTkLabel(
            row3_frame,
            text="Online Query Tools",
            font=fonts.md,
            text_color=colors.text
        )
        row3_label.pack(side="top", anchor="w", padx=10)

        query_gaia = ctk.CTkButton(
            row3_frame,
            text="Query Gaia",
            command=lambda: QueryObject(
                self.sidebar_content,
                self.sidebar_menu,
                manager=self
            ),
            font=fonts.md,
            fg_color=colors.blue,
            text_color=colors.text
        )
        query_gaia.pack(side="left", padx=10, pady=5)

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
            self.viewer.toggle_freeze_coords()
            self.root.focus_set()
        
    def load_font(self):
        """Load the custom font and add it to the pyglet font registry. """
        # Load the custom font with pyglet
        font_dir = os.path.join(starmate.__path__[0], "fonts", "fonts")
        font_path = os.path.join(font_dir, "JetBrainsMonoNerdFont-Regular.ttf")
        pyglet.font.add_file(font_path)

        success = FontManager.load_font(font_path)
        if not success:
            raise Exception("Failed to load custom font")

    # ==================== NEW MEASUREMENT SYSTEM METHODS ====================

    def start_measurement(self, measurement_type):
        """Start a new measurement of the specified type."""
        if not self.active_im():
            control.warn("No active image. Please load an image first.")
            return

        # Start measurement mode in the active image
        self.im_ref().start_measurement(measurement_type)

        # Bind canvas click to measurement handler
        self.viewer.image_canvas.unbind("<Button-1>")
        self.viewer.image_canvas.bind("<Button-1>", self.handle_measurement_click)

        # Bind escape key to cancel measurement
        self.root.bind("<Escape>", self.cancel_measurement)

        control.info(f"Started {measurement_type} measurement. Press ESC to cancel.")

    def handle_measurement_click(self, event):
        """Handle clicks during measurement mode."""
        if not self.active_im():
            return

        finished = self.im_ref().handle_measurement_click(event, self.viewer.image_canvas)

        if finished:
            # Measurement complete, restore normal mode
            self.viewer.image_canvas.unbind("<Button-1>")
            self.viewer.image_canvas.bind("<Button-1>", self.viewer.start_pan)
            self.root.unbind("<Escape>")
            self.viewer.update_display_image()

        # Update display to show temporary measurement
        self.viewer.update_display_image()

    def cancel_measurement(self, event=None):
        """Cancel the current measurement."""
        if not self.active_im():
            return

        self.im_ref().cancel_measurement()

        # Restore normal mode
        self.viewer.image_canvas.unbind("<Button-1>")
        self.viewer.image_canvas.bind("<Button-1>", self.viewer.start_pan)
        self.root.unbind("<Escape>")
        self.viewer.update_display_image()

    def show_measurement_table(self):
        """Show the measurement table UI."""
        from starmate.components.measurement_table import MeasurementTable
        MeasurementTable(self.sidebar_content, self.sidebar_menu, manager=self)

    def start_cutout_selection(self):
        """Start interactive cutout selection."""
        if not self.active_im():
            control.warn("No active image. Please load an image first.")
            return

        from starmate.components.cutout_tool import CutoutTool
        CutoutTool(self.sidebar_content, self.sidebar_menu, manager=self)
        

    


manager = Manager()