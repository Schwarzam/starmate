import customtkinter as ctk
from starmate.variables import colors, fonts

from logpool import control

from starmate.fetch_data.gaia import gaia_query
from astropy.table import Table


class QueryObject:
    def __init__(self, master, menu_callback, manager):
        self.master = master
        self.manager = manager
        
        # Destroy all widgets in the master frame
        for widget in self.master.winfo_children():
            widget.destroy()
        
        # Store callback
        self.menu_callback = menu_callback
        
        # Main Menu Button at the top center
        self.master.main_menu_button = ctk.CTkButton(
            self.master, 
            text="Main Menu", 
            font=fonts.md, 
            fg_color=colors.accent, 
            text_color=colors.text,
            command=menu_callback
        )
        self.master.main_menu_button.pack(side="top", pady=(50, 20))
        ra, dec = self.manager.viewer.get_panel_ra_dec()
        
        control.submit(self.query_gaia, ra, dec)
    
    def populate_on_result(self, result: Table):
        """Populate master with information from the result table."""
        # Clear any previous result widgets in master
        for widget in self.master.winfo_children():
            widget.destroy()
            
        # Main Menu Button at the top center
        self.master.main_menu_button = ctk.CTkButton(
            self.master, 
            text="Main Menu", 
            font=fonts.md, 
            fg_color=colors.accent, 
            text_color=colors.text,
            command=self.menu_callback
        )
        self.master.main_menu_button.pack(side="top", pady=(50, 20))

        # Display a title for the results
        title_label = ctk.CTkLabel(
            self.master, 
            text="Query Results",
            font=fonts.lg,
            text_color=colors.text
        )
        title_label.pack(pady=(10, 5))

        # Create a frame to hold the results in a structured way, centered within the master
        results_frame = ctk.CTkFrame(self.master)
        results_frame.pack(pady=40, padx=40, expand=True)  # Center `results_frame` within its parent

        # Define the columns and data to display
        columns_to_display = result.columns
        labels = columns_to_display

        # Display the first row of data
        obj_data = result[0]  # Assuming we're taking the first row

        # Populate each row in the results frame and center the content
        for i, (label, column) in enumerate(zip(labels, columns_to_display)):
            value = obj_data[column]

            # Label for the data description, centered horizontally
            label_widget = ctk.CTkLabel(
                results_frame, 
                text=f"{label}:",
                font=fonts.md, 
                text_color=colors.text
            )
            label_widget.grid(row=i, column=0, sticky="e", padx=5)  # Align right for even spacing

            # Value for the data entry, aligned with the label
            value_widget = ctk.CTkLabel(
                results_frame, 
                text=f"{value:.4f}" if isinstance(value, float) else str(value),
                font=fonts.md,
                text_color=colors.text
            )
            value_widget.grid(row=i, column=1, sticky="w", padx=5)  # Align left for even spacing
            
        # TODO: add save button
    
    def query_gaia(self, ra, dec, arcsecs = 2):
        control.info(f"Querying GAIA within {arcsecs} arcsec...")
        res = gaia_query(ra, dec, 2)
        
        if len(res) == 0:
            control.info("No stars found.")
            return

        self.populate_on_result(res)
        
    
                
            
            