import customtkinter as ctk
from starmate.variables import colors, fonts
from tkinter import ttk
import tkinter as tk

class MeasurementTable:
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
            text="Measurement Records",
            font=fonts.lg,
            text_color=colors.text
        )
        title_label.pack(pady=(0, 10))

        # Control buttons frame
        control_frame = ctk.CTkFrame(self.master, fg_color=colors.bg)
        control_frame.pack(pady=5, padx=10, fill="x")

        delete_button = ctk.CTkButton(
            control_frame,
            text="Delete",
            command=self.delete_selected,
            font=fonts.sm,
            fg_color=colors.red,
            text_color=colors.text,
            width=80
        )
        delete_button.pack(side="left", padx=2)

        toggle_vis_button = ctk.CTkButton(
            control_frame,
            text="Toggle Vis",
            command=self.toggle_visibility,
            font=fonts.sm,
            fg_color=colors.blue,
            text_color=colors.text,
            width=80
        )
        toggle_vis_button.pack(side="left", padx=2)

        clear_all_button = ctk.CTkButton(
            control_frame,
            text="Clear All",
            command=self.clear_all,
            font=fonts.sm,
            fg_color=colors.red,
            text_color=colors.text,
            width=80
        )
        clear_all_button.pack(side="left", padx=2)

        residual_button = ctk.CTkButton(
            control_frame,
            text="Residual",
            command=self.show_residual,
            font=fonts.sm,
            fg_color=colors.green,
            text_color=colors.text,
            width=80
        )
        residual_button.pack(side="left", padx=2)

        # Create a frame for the table with scrollbar
        table_frame = ctk.CTkFrame(self.master, fg_color=colors.dark)
        table_frame.pack(pady=10, padx=10, fill="both", expand=True)

        # Create Treeview for table display
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                       background=colors.dark,
                       foreground=colors.text,
                       rowheight=25,
                       fieldbackground=colors.dark,
                       borderwidth=0)
        style.map('Treeview', background=[('selected', colors.accent)])
        style.configure("Treeview.Heading",
                       background=colors.bg,
                       foreground=colors.text,
                       relief="flat",
                       borderwidth=0)

        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side="right", fill="y")

        # Table columns
        columns = ("ID", "Type", "Image", "Details", "Count/Stats", "Visible")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings",
                                yscrollcommand=scrollbar.set, selectmode="browse")

        scrollbar.config(command=self.tree.yview)

        # Define column headings and widths
        self.tree.heading("ID", text="ID")
        self.tree.heading("Type", text="Type")
        self.tree.heading("Image", text="Image")
        self.tree.heading("Details", text="Details")
        self.tree.heading("Count/Stats", text="Count/Stats")
        self.tree.heading("Visible", text="Visible")

        self.tree.column("ID", width=80, anchor="w")
        self.tree.column("Type", width=80, anchor="w")
        self.tree.column("Image", width=120, anchor="w")
        self.tree.column("Details", width=180, anchor="w")
        self.tree.column("Count/Stats", width=150, anchor="w")
        self.tree.column("Visible", width=60, anchor="center")

        self.tree.pack(fill="both", expand=True)

        # Bind selection event
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # Populate the table
        self.refresh_table()

        # Auto-refresh every 500ms
        self.auto_refresh()

    def refresh_table(self):
        """Refresh the table with current measurements."""
        # Check if the tree widget still exists
        if not self.tree.winfo_exists():
            return

        try:
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Get all measurements
            measurements = self.manager.measurement_manager.measurements

            # Populate table
            for measurement in measurements:
                info = measurement.get_display_info()

                # Build details string based on type
                details = ""
                count_stats = ""

                if measurement.measurement_type == "Line":
                    details = f"Length: {measurement.get_length():.2f} px"
                    count_stats = "N/A"
                elif measurement.measurement_type == "Circle":
                    details = f"R: {measurement.radius:.2f} px, A: {measurement.get_area():.2f} px²"
                    count_stats = f"N={measurement.interior_count}, μ={measurement.interior_mean:.2f}"
                elif measurement.measurement_type == "Ellipse":
                    details = f"Axes: ({measurement.semi_major:.1f}, {measurement.semi_minor:.1f}) px"
                    count_stats = f"N={measurement.interior_count}, μ={measurement.interior_mean:.2f}"

                visible_str = "✓" if measurement.visible else "✗"

                self.tree.insert("", "end", iid=measurement.id,
                               values=(info["ID"], info["Type"], info["Image"], details, count_stats, visible_str))
        except Exception:
            # Widget has been destroyed, stop auto-refresh
            return

    def auto_refresh(self):
        """Auto-refresh the table periodically."""
        if not self.tree.winfo_exists():
            return  # Stop refreshing if widget is destroyed

        try:
            self.refresh_table()
            self.master.after(500, self.auto_refresh)
        except Exception:
            # Widget destroyed during refresh
            pass

    def on_select(self, event):
        """Handle selection of a measurement in the table."""
        selection = self.tree.selection()
        if selection:
            measurement_id = selection[0]
            self.manager.measurement_manager.select_measurement(measurement_id)

    def delete_selected(self):
        """Delete the selected measurement."""
        selection = self.tree.selection()
        if selection:
            measurement_id = selection[0]
            self.manager.measurement_manager.remove_measurement(measurement_id)
            self.refresh_table()
            self.manager.viewer.update_display_image()

    def toggle_visibility(self):
        """Toggle visibility of the selected measurement."""
        selection = self.tree.selection()
        if selection:
            measurement_id = selection[0]
            self.manager.measurement_manager.toggle_visibility(measurement_id)
            self.refresh_table()
            self.manager.viewer.update_display_image()

    def clear_all(self):
        """Clear all measurements."""
        self.manager.measurement_manager.clear_all()
        self.refresh_table()
        self.manager.viewer.update_display_image()

    def show_residual(self):
        """Show residual calculation UI."""
        from starmate.components.residual_view import ResidualView
        ResidualView(self.master, self.menu_callback, manager=self.manager)
