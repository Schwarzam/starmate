import argparse

import customtkinter as ctk

import tkinter.font as tkFont

import os
import pyglet

import starmate
from starmate.fonts.font_manager import FontManager
from starmate.fits_viewer import FITSViewer

from logpool import control

class Manager:
    def __init__(self):
        self.root = ctk.CTk()
        
        self.root.title("starmate")
        self.sidebar_visible = False  # Track if the sidebar is visible

        
        parser = argparse.ArgumentParser(description="CLI for astroxs package")
        self.args = parser.parse_args()

        self.viewer = FITSViewer(self.root, self.args)

    def start(self):
        self.root.mainloop()
        
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


def main():

    # Define CLI arguments here, e.g.,
    # parser.add_argument('arg_name', help="Description of argument")

    manager.root.mainloop()
