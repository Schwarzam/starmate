import customtkinter as ctk
from starmate.variables import colors, fonts

class MatchFrames:
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

        
        # Frame for RA and Dec to keep them side by side
        input_frame = ctk.CTkFrame(self.master, fg_color=colors.bg)
        input_frame.pack(pady=5)

        self.master.button1 = ctk.CTkButton(
            input_frame, 
            text="physical", 
            command= lambda : self.on_go_clicked("physical"), 
            font=fonts.md, 
            fg_color=colors.accent
        )
        self.master.button1.pack(side="left", padx=10, pady=10)

        self.master.button2 = ctk.CTkButton(
            input_frame, 
            text="coordinates", 
            command= lambda : self.on_go_clicked("coordinates"), 
            font=fonts.md, 
            fg_color=colors.accent
        )
        self.master.button2.pack(side="left", padx=10, pady=10)

    def on_go_clicked(self, typ = "physical"):
        # Call the callback with the values
        center_x, center_y = self.manager.im_ref().get_canvas_center_pos()
        x_image, y_image = self.manager.im_ref().canvas_pos_to_xy(center_x, center_y)
        ra, dec = self.manager.im_ref().get_image_canvas_center_coords()
        
        zoom_level = self.manager.im_ref().zoom_level
        
        for image in self.manager.images:
            if typ == "coordinates":
                self.manager.images[image].center_on_coordinate(ra, dec, zoom_level)
        
            if typ == "physical":
                self.manager.images[image].center_on_xy(x_image, y_image, zoom_level)
                
            
            