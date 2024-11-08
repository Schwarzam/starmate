import customtkinter as ctk
from starmate.variables import colors, fonts

class CoordinateInput:
    def __init__(self, master, go_callback, menu_callback):
        self.master = master
        
        # Destroy all widgets in the master frame
        for widget in self.master.winfo_children():
            widget.destroy()
        
        # Store callback
        self.go_callback = go_callback
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

        # Frame for RA and Dec to keep them side by side
        input_frame = ctk.CTkFrame(self.master, fg_color=colors.bg)
        input_frame.pack(pady=5)

        # RA Input field
        self.master.entry1 = ctk.CTkEntry(input_frame, placeholder_text="Enter RA", width=150)
        self.master.entry1.pack(side="left", padx=10, pady=10)

        # Dec Input field
        self.master.entry2 = ctk.CTkEntry(input_frame, placeholder_text="Enter Dec", width=150)
        self.master.entry2.pack(side="left", padx=10, pady=10)

        zoom_frame = ctk.CTkFrame(self.master, fg_color=colors.bg)
        zoom_frame.pack(pady=5)
        
        # Label above the Zoom input
        self.master.zoom_label = ctk.CTkLabel(zoom_frame, text="Zoom Factor", font=fonts.sm, text_color=colors.text)
        self.master.zoom_label.pack(pady=(10, 0))  # Add slight space between label and input

        # Zoom Input centered below RA and Dec
        self.master.entry3 = ctk.CTkEntry(zoom_frame, placeholder_text="Zoom Level", width=150)
        self.master.entry3.pack(pady=(0, 10), padx=10)
        self.master.entry3.insert(0, "2")

        # "Go" button below Zoom input
        self.master.go_button = ctk.CTkButton(self.master, text="Go", command=self.on_go_clicked, font=fonts.md, fg_color=colors.accent)
        self.master.go_button.pack(pady=(10, 20))


    def on_go_clicked(self):
        # Retrieve values from inputs
        value1 = self.master.entry1.get()
        value2 = self.master.entry2.get()
        value3 = self.master.entry3.get()
        
        value1 = float(value1)
        value2 = float(value2)
        value3 = float(value3)
    
        # Call the callback with the values
        if self.go_callback:
            self.go_callback(value1, value2, value3)
            