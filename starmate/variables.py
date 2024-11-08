from starmate.utils import DotDict

# font_name = "Agave"
font_name = "JetBrainsMono Nerd Font"
fonts = DotDict(
    {
        "sm": (font_name, 10),
        "md": (font_name, 12),
        "lg": (font_name, 14),
        "xl": (font_name, 16),
        "2xl": (font_name, 18),
        "3xl": (font_name, 20),
        "4xl": (font_name, 22),
    }
)

colors = DotDict(
    {
        "bg": "#333233",
        "dark": "#1f1e1f",
        "blue": "#305770",
        "fg": "#ffffff",
        "accent": "#f4a261",
        "error": "#e63946",
        "warning": "#f1faee",
        "info": "#a8dadc",
        "success": "#457b9d",
        "text": "#ffffff",
    }
)