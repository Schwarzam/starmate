import customtkinter as ctk
from starmate.variables import colors, fonts
from starmate.image import FitsImage
from logpool import control
import numpy as np

class CutoutTool:
    def __init__(self, master, menu_callback, manager):
        self.master = master
        self.menu_callback = menu_callback
        self.manager = manager

        # Destroy all widgets in the master frame
        for widget in self.master.winfo_children():
            widget.destroy()

        # Main Menu Button at the top
        main_menu_button = ctk.CTkButton(
            self.master,
            text="Main Menu",
            font=fonts.md,
            fg_color=colors.accent,
            text_color=colors.text,
            command=menu_callback
        )
        main_menu_button.pack(side="top", pady=(10, 10), padx=10)

        # Title
        title_label = ctk.CTkLabel(
            self.master,
            text="Create Image Cutout",
            font=fonts.lg,
            text_color=colors.text
        )
        title_label.pack(pady=(0, 10))

        # Instructions
        instructions = ctk.CTkLabel(
            self.master,
            text="Define a region to extract from the current image",
            font=fonts.sm,
            text_color=colors.text_secondary
        )
        instructions.pack(pady=(0, 10))

        # Input frame
        input_frame = ctk.CTkFrame(self.master, fg_color=colors.bg)
        input_frame.pack(pady=10, padx=10, fill="x")

        # Center X
        cx_label = ctk.CTkLabel(input_frame, text="Center X:", font=fonts.sm, text_color=colors.text)
        cx_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.center_x_entry = ctk.CTkEntry(input_frame, placeholder_text="X coordinate", width=150, font=fonts.sm)
        self.center_x_entry.grid(row=0, column=1, padx=10, pady=5)

        # Center Y
        cy_label = ctk.CTkLabel(input_frame, text="Center Y:", font=fonts.sm, text_color=colors.text)
        cy_label.grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.center_y_entry = ctk.CTkEntry(input_frame, placeholder_text="Y coordinate", width=150, font=fonts.sm)
        self.center_y_entry.grid(row=1, column=1, padx=10, pady=5)

        # Width
        width_label = ctk.CTkLabel(input_frame, text="Width (px):", font=fonts.sm, text_color=colors.text)
        width_label.grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.width_entry = ctk.CTkEntry(input_frame, placeholder_text="Width", width=150, font=fonts.sm)
        self.width_entry.grid(row=2, column=1, padx=10, pady=5)
        self.width_entry.insert(0, "100")

        # Height
        height_label = ctk.CTkLabel(input_frame, text="Height (px):", font=fonts.sm, text_color=colors.text)
        height_label.grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.height_entry = ctk.CTkEntry(input_frame, placeholder_text="Height", width=150, font=fonts.sm)
        self.height_entry.grid(row=3, column=1, padx=10, pady=5)
        self.height_entry.insert(0, "100")

        # Cutout name
        name_label = ctk.CTkLabel(input_frame, text="Name:", font=fonts.sm, text_color=colors.text)
        name_label.grid(row=4, column=0, sticky="w", padx=10, pady=5)
        self.name_entry = ctk.CTkEntry(input_frame, placeholder_text="Cutout name", width=150, font=fonts.sm)
        self.name_entry.grid(row=4, column=1, padx=10, pady=5)
        self.name_entry.insert(0, "cutout")

        # Buttons frame
        buttons_frame = ctk.CTkFrame(self.master, fg_color=colors.bg)
        buttons_frame.pack(pady=20)

        use_current_button = ctk.CTkButton(
            buttons_frame,
            text="Use Current Position",
            command=self.use_current_position,
            font=fonts.sm,
            fg_color=colors.blue,
            text_color=colors.text,
            width=150
        )
        use_current_button.pack(side="left", padx=5)

        interactive_button = ctk.CTkButton(
            buttons_frame,
            text="Select Interactively",
            command=self.start_interactive_selection,
            font=fonts.sm,
            fg_color=colors.blue,
            text_color=colors.text,
            width=150
        )
        interactive_button.pack(side="left", padx=5)

        create_button = ctk.CTkButton(
            buttons_frame,
            text="Create Cutout",
            command=self.create_cutout,
            font=fonts.md,
            fg_color=colors.green,
            text_color=colors.text,
            width=150
        )
        create_button.pack(side="left", padx=5)

        # Status label
        self.status_label = ctk.CTkLabel(
            self.master,
            text="",
            font=fonts.sm,
            text_color=colors.accent
        )
        self.status_label.pack(pady=10)

    def use_current_position(self):
        """Use the current canvas center position as cutout center."""
        if not self.manager.active_im():
            control.warn("No active image.")
            return

        # Get canvas center in image coordinates
        center_x, center_y = self.manager.im_ref().get_canvas_center_pos()
        x_image, y_image = self.manager.im_ref().canvas_pos_to_xy(center_x, center_y)

        self.center_x_entry.delete(0, "end")
        self.center_x_entry.insert(0, str(int(x_image)))

        self.center_y_entry.delete(0, "end")
        self.center_y_entry.insert(0, str(int(y_image)))

        self.status_label.configure(text=f"Position set to ({int(x_image)}, {int(y_image)})")

    def start_interactive_selection(self):
        """Start interactive rectangle selection mode."""
        if not self.manager.active_im():
            control.warn("No active image.")
            return

        control.info("Interactive selection: Click two corners of the region to extract.")
        self.status_label.configure(text="Click two corners on the image...")

        # Store selection state
        self.selection_points = []

        # Bind canvas clicks
        self.manager.viewer.image_canvas.unbind("<Button-1>")
        self.manager.viewer.image_canvas.bind("<Button-1>", self.handle_selection_click)

    def handle_selection_click(self, event):
        """Handle clicks during interactive selection."""
        x_image, y_image = self.manager.im_ref().get_image_xy_mouse()
        self.selection_points.append((x_image, y_image))

        if len(self.selection_points) == 1:
            control.info(f"First corner set at ({int(x_image)}, {int(y_image)}). Click second corner.")
        elif len(self.selection_points) == 2:
            # Calculate cutout parameters
            x1, y1 = self.selection_points[0]
            x2, y2 = self.selection_points[1]

            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            width = abs(x2 - x1)
            height = abs(y2 - y1)

            # Update entries
            self.center_x_entry.delete(0, "end")
            self.center_x_entry.insert(0, str(int(center_x)))

            self.center_y_entry.delete(0, "end")
            self.center_y_entry.insert(0, str(int(center_y)))

            self.width_entry.delete(0, "end")
            self.width_entry.insert(0, str(int(width)))

            self.height_entry.delete(0, "end")
            self.height_entry.insert(0, str(int(height)))

            self.status_label.configure(text=f"Region selected: {int(width)}x{int(height)} at ({int(center_x)}, {int(center_y)})")

            # Restore normal mode
            self.manager.viewer.image_canvas.unbind("<Button-1>")
            self.manager.viewer.image_canvas.bind("<Button-1>", self.manager.viewer.start_pan)
            self.selection_points = []

            control.info("Selection complete. Click 'Create Cutout' to extract the region.")

    def create_cutout(self):
        """Create the cutout from the specified region."""
        if not self.manager.active_im():
            control.warn("No active image.")
            return

        try:
            # Get parameters
            center_x = int(float(self.center_x_entry.get()))
            center_y = int(float(self.center_y_entry.get()))
            width = int(float(self.width_entry.get()))
            height = int(float(self.height_entry.get()))
            name = self.name_entry.get().strip()

            if not name:
                name = "cutout"

            # Get the active image
            active_image = self.manager.im_ref()

            # Calculate bounds
            x_start = max(0, center_x - width // 2)
            x_end = min(active_image.image_data.shape[1], center_x + width // 2)
            y_start = max(0, center_y - height // 2)
            y_end = min(active_image.image_data.shape[0], center_y + height // 2)

            # Extract cutout
            cutout_data = active_image.image_data[y_start:y_end, x_start:x_end].copy()

            # Create a new header (copy from original but update dimensions)
            cutout_header = active_image.header.copy()
            cutout_header['NAXIS1'] = cutout_data.shape[1]
            cutout_header['NAXIS2'] = cutout_data.shape[0]

            # Update WCS if present
            if 'CRPIX1' in cutout_header:
                cutout_header['CRPIX1'] -= x_start
            if 'CRPIX2' in cutout_header:
                cutout_header['CRPIX2'] -= y_start

            # Create unique name
            base_name = f"{name}_cutout"
            unique_name = base_name
            counter = 1
            while unique_name in self.manager.images:
                unique_name = f"{base_name}_{counter}"
                counter += 1

            # Create FitsImage from cutout
            cutout_image = FitsImage.load_f_data(cutout_data, cutout_header, self.manager, unique_name)

            # Add to manager
            self.manager.images[unique_name] = cutout_image

            # Update image selector
            self.manager.viewer.update_image_list()

            # Automatically switch to the new cutout
            self.manager.image_selector.set(unique_name)
            self.manager.change_active_image()

            control.info(f"Cutout '{unique_name}' created successfully: {cutout_data.shape[1]}x{cutout_data.shape[0]} px")
            self.status_label.configure(text=f"Cutout '{unique_name}' created!")

            # Return to main menu
            self.master.after(1500, self.menu_callback)

        except ValueError as e:
            control.warn(f"Invalid input: {e}")
            self.status_label.configure(text="Error: Invalid input values")
        except Exception as e:
            control.warn(f"Error creating cutout: {e}")
            self.status_label.configure(text=f"Error: {e}")
