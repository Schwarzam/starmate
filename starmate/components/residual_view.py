import customtkinter as ctk
from starmate.variables import colors, fonts
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from logpool import control

class ResidualView:
    def __init__(self, master, menu_callback, manager):
        self.master = master
        self.menu_callback = menu_callback
        self.manager = manager

        # Destroy all widgets in the master frame
        for widget in self.master.winfo_children():
            widget.destroy()

        # Back Button at the top
        back_button = ctk.CTkButton(
            self.master,
            text="Back to Table",
            font=fonts.md,
            fg_color=colors.accent,
            text_color=colors.text,
            command=self.back_to_table
        )
        back_button.pack(side="top", pady=(10, 10), padx=10)

        # Title
        title_label = ctk.CTkLabel(
            self.master,
            text="Residual Analysis",
            font=fonts.lg,
            text_color=colors.text
        )
        title_label.pack(pady=(0, 10))

        # Instructions
        instructions = ctk.CTkLabel(
            self.master,
            text="Select two measurements of the same type to calculate residual",
            font=fonts.sm,
            text_color=colors.text_secondary
        )
        instructions.pack(pady=(0, 10))

        # Selection frame
        selection_frame = ctk.CTkFrame(self.master, fg_color=colors.bg)
        selection_frame.pack(pady=10, padx=10, fill="x")

        # Get all measurements
        measurements = self.manager.measurement_manager.measurements
        measurement_options = [f"{m.id[:8]} - {m.measurement_type} - {m.image_name}" for m in measurements]

        # Measurement 1 selector
        m1_label = ctk.CTkLabel(selection_frame, text="Measurement 1:", font=fonts.sm, text_color=colors.text)
        m1_label.pack(anchor="w", padx=10, pady=(5, 0))

        self.measurement1_selector = ctk.CTkComboBox(
            selection_frame,
            values=measurement_options if measurement_options else ["No measurements"],
            font=fonts.sm,
            fg_color=colors.dark,
            text_color=colors.text,
            width=300
        )
        self.measurement1_selector.pack(padx=10, pady=(0, 10))

        # Measurement 2 selector
        m2_label = ctk.CTkLabel(selection_frame, text="Measurement 2:", font=fonts.sm, text_color=colors.text)
        m2_label.pack(anchor="w", padx=10, pady=(5, 0))

        self.measurement2_selector = ctk.CTkComboBox(
            selection_frame,
            values=measurement_options if measurement_options else ["No measurements"],
            font=fonts.sm,
            fg_color=colors.dark,
            text_color=colors.text,
            width=300
        )
        self.measurement2_selector.pack(padx=10, pady=(0, 10))

        # Calculate button
        calculate_button = ctk.CTkButton(
            selection_frame,
            text="Calculate Residual",
            command=self.calculate_residual,
            font=fonts.md,
            fg_color=colors.green,
            text_color=colors.text,
            width=200
        )
        calculate_button.pack(pady=10)

        # Plot frame
        self.plot_frame = ctk.CTkFrame(self.master, fg_color=colors.dark)
        self.plot_frame.pack(pady=10, padx=10, fill="both", expand=True)

        # Store measurements for reference
        self.measurements = measurements

    def back_to_table(self):
        """Return to measurement table."""
        from starmate.components.measurement_table import MeasurementTable
        MeasurementTable(self.master, self.menu_callback, manager=self.manager)

    def calculate_residual(self):
        """Calculate and display residual between two measurements."""
        # Clear previous plot
        for widget in self.plot_frame.winfo_children():
            widget.destroy()

        # Get selected measurement IDs
        m1_selection = self.measurement1_selector.get()
        m2_selection = self.measurement2_selector.get()

        if m1_selection == "No measurements" or m2_selection == "No measurements":
            control.warn("Please select valid measurements.")
            return

        # Extract IDs from selection strings (format: "id[:8] - type - image")
        m1_id_short = m1_selection.split(" - ")[0]
        m2_id_short = m2_selection.split(" - ")[0]

        # Find full measurement IDs
        m1_id = None
        m2_id = None
        for m in self.measurements:
            if m.id.startswith(m1_id_short):
                m1_id = m.id
            if m.id.startswith(m2_id_short):
                m2_id = m.id

        if not m1_id or not m2_id:
            control.warn("Could not find selected measurements.")
            return

        # Calculate residual
        residual = self.manager.measurement_manager.calculate_residual(m1_id, m2_id)

        if residual is None:
            control.warn("Cannot calculate residual: measurements must be of the same type and have pixel values.")
            return

        # Plot residual
        self.plot_residual(residual, m1_id_short, m2_id_short)

        control.info(f"Residual calculated: mean={residual.mean():.2f}, std={residual.std():.2f}")

    def plot_residual(self, residual, m1_name, m2_name):
        """Plot the residual values."""
        # Create figure
        fig = Figure(figsize=(5, 4), dpi=100, facecolor=colors.dark)
        ax = fig.add_subplot(111, facecolor=colors.dark)

        # Plot residual
        ax.plot(residual, color=colors.accent, linewidth=2, label="Residual")
        ax.axhline(y=0, color="white", linestyle="--", linewidth=1, alpha=0.5)
        ax.axhline(y=residual.mean(), color=colors.green, linestyle="--", linewidth=1, label=f"Mean: {residual.mean():.2f}")

        # Fill area
        ax.fill_between(range(len(residual)), residual, alpha=0.3, color=colors.accent)

        # Styling
        ax.set_title(f"Residual: {m1_name} - {m2_name}", color=colors.text, fontsize=12)
        ax.set_xlabel("Position", color=colors.text)
        ax.set_ylabel("Residual Intensity", color=colors.text)
        ax.grid(True, color="gray", alpha=0.3)
        ax.tick_params(colors=colors.text)
        ax.legend(facecolor=colors.dark, edgecolor="white", labelcolor=colors.text)

        # Set spine colors
        for spine in ax.spines.values():
            spine.set_edgecolor(colors.text)

        fig.tight_layout()

        # Embed plot
        canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        # Display statistics
        stats_frame = ctk.CTkFrame(self.plot_frame, fg_color=colors.bg)
        stats_frame.pack(pady=10, padx=10, fill="x")

        stats_text = f"Mean: {residual.mean():.2f}  |  Std Dev: {residual.std():.2f}  |  Min: {residual.min():.2f}  |  Max: {residual.max():.2f}"
        stats_label = ctk.CTkLabel(stats_frame, text=stats_text, font=fonts.sm, text_color=colors.text)
        stats_label.pack(pady=5)
