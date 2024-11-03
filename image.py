from astropy.io import fits
from astropy.wcs import WCS

class FitsImage:
    
    def __init__(self, image_data, header):
        self.image_data = image_data
        self.header = header
        
        self.wcs_info = WCS(header)
        
        # Control variables for zooming and panning
        self.zoom_level = 1.0
        self.pan_start_x = None
        self.pan_start_y = None
        
        self.offset_x = 0
        self.offset_y = 0
        
        