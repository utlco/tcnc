#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
A simple library of functions to parse and format CSS style properties.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import string
import numbers

CSS_COLORS = {
    'aliceblue': (240, 248, 255),
    'antiquewhite': (250, 235, 215),
    'aqua': (0, 255, 255),
    'aquamarine': (127, 255, 212),
    'azure': (240, 255, 255),
    'beige': (245, 245, 220),
    'bisque': (255, 228, 196),
    'black': (0, 0, 0),
    'blanchedalmond': (255, 235, 205),
    'blue': (0, 0, 255),
    'blueviolet': (138, 43, 226),
    'brown': (165, 42, 42),
    'burlywood': (222, 184, 135),
    'cadetblue': (95, 158, 160),
    'chartreuse': (127, 255, 0),
    'chocolate': (210, 105, 30),
    'coral': (255, 127, 80),
    'cornflowerblue': (100, 149, 237),
    'cornsilk': (255, 248, 220),
    'crimson': (220, 20, 60),
    'cyan': (0, 255, 255),
    'darkblue': (0, 0, 139),
    'darkcyan': (0, 139, 139),
    'darkgoldenrod': (184, 134, 11),
    'darkgray': (169, 169, 169),
    'darkgreen': (0, 100, 0),
    'darkgrey': (169, 169, 169),
    'darkkhaki': (189, 183, 107),
    'darkmagenta': (139, 0, 139),
    'darkolivegreen': (85, 107, 47),
    'darkorange': (255, 140, 0),
    'darkorchid': (153, 50, 204),
    'darkred': (139, 0, 0),
    'darksalmon': (233, 150, 122),
    'darkseagreen': (143, 188, 143),
    'darkslateblue': (72, 61, 139),
    'darkslategray': (47, 79, 79),
    'darkslategrey': (47, 79, 79),
    'darkturquoise': (0, 206, 209),
    'darkviolet': (148, 0, 211),
    'deeppink': (255, 20, 147),
    'deepskyblue': (0, 191, 255),
    'dimgray': (105, 105, 105),
    'dimgrey': (105, 105, 105),
    'dodgerblue': (30, 144, 255),
    'firebrick': (178, 34, 34),
    'floralwhite': (255, 250, 240),
    'forestgreen': (34, 139, 34),
    'fuchsia': (255, 0, 255),
    'gainsboro': (220, 220, 220),
    'ghostwhite': (248, 248, 255),
    'gold': (255, 215, 0),
    'goldenrod': (218, 165, 32),
    'gray': (128, 128, 128),
    'green': (0, 128, 0),
    'greenyellow': (173, 255, 47),
    'grey': (128, 128, 128),
    'honeydew': (240, 255, 240),
    'hotpink': (255, 105, 180),
    'indianred': (205, 92, 92),
    'indigo': (75, 0, 130),
    'ivory': (255, 255, 240),
    'khaki': (240, 230, 140),
    'lavender': (230, 230, 250),
    'lavenderblush': (255, 240, 245),
    'lawngreen': (124, 252, 0),
    'lemonchiffon': (255, 250, 205),
    'lightblue': (173, 216, 230),
    'lightcoral': (240, 128, 128),
    'lightcyan': (224, 255, 255),
    'lightgoldenrodyellow': (250, 250, 210),
    'lightgray': (211, 211, 211),
    'lightgreen': (144, 238, 144),
    'lightgrey': (211, 211, 211),
    'lightpink': (255, 182, 193),
    'lightsalmon': (255, 160, 122),
    'lightseagreen': (32, 178, 170),
    'lightskyblue': (135, 206, 250),
    'lightslategray': (119, 136, 153),
    'lightslategrey': (119, 136, 153),
    'lightsteelblue': (176, 196, 222),
    'lightyellow': (255, 255, 224),
    'lime': (0, 255, 0),
    'limegreen': (50, 205, 50),
    'linen': (250, 240, 230),
    'magenta': (255, 0, 255),
    'maroon': (128, 0, 0),
    'mediumaquamarine': (102, 205, 170),
    'mediumblue': (0, 0, 205),
    'mediumorchid': (186, 85, 211),
    'mediumpurple': (147, 112, 219),
    'mediumseagreen': (60, 179, 113),
    'mediumslateblue': (123, 104, 238),
    'mediumspringgreen': (0, 250, 154),
    'mediumturquoise': (72, 209, 204),
    'mediumvioletred': (199, 21, 133),
    'midnightblue': (25, 25, 112),
    'mintcream': (245, 255, 250),
    'mistyrose': (255, 228, 225),
    'moccasin': (255, 228, 181),
    'navajowhite': (255, 222, 173),
    'navy': (0, 0, 128),
    'oldlace': (253, 245, 230),
    'olive': (128, 128, 0),
    'olivedrab': (107, 142, 35),
    'orange': (255, 165, 0),
    'orangered': (255, 69, 0),
    'orchid': (218, 112, 214),
    'palegoldenrod': (238, 232, 170),
    'palegreen': (152, 251, 152),
    'paleturquoise': (175, 238, 238),
    'palevioletred': (219, 112, 147),
    'papayawhip': (255, 239, 213),
    'peachpuff': (255, 218, 185),
    'peru': (205, 133, 63),
    'pink': (255, 192, 203),
    'plum': (221, 160, 221),
    'powderblue': (176, 224, 230),
    'purple': (128, 0, 128),
    'red': (255, 0, 0),
    'rosybrown': (188, 143, 143),
    'royalblue': (65, 105, 225),
    'saddlebrown': (139, 69, 19),
    'salmon': (250, 128, 114),
    'sandybrown': (244, 164, 96),
    'seagreen': (46, 139, 87),
    'seashell': (255, 245, 238),
    'sienna': (160, 82, 45),
    'silver': (192, 192, 192),
    'skyblue': (135, 206, 235),
    'slateblue': (106, 90, 205),
    'slategray': (112, 128, 144),
    'slategrey': (112, 128, 144),
    'snow': (255, 250, 250),
    'springgreen': (0, 255, 127),
    'steelblue': (70, 130, 180),
    'tan': (210, 180, 140),
    'teal': (0, 128, 128),
    'thistle': (216, 191, 216),
    'tomato': (255, 99, 71),
    'turquoise': (64, 224, 208),
    'violet': (238, 130, 238),
    'wheat': (245, 222, 179),
    'white': (255, 255, 255),
    'whitesmoke': (245, 245, 245),
    'yellow': (255, 255, 0),
    'yellowgreen': (154, 205, 50),}
"""CSS color names to hex rgb values.

    See:
        https://www.w3.org/TR/css3-color/#svg-color
"""

def inline_style_to_dict(inline_style):
    """Create a dictionary of style properties from an inline style attribute.

    Args:
        inline_style: A string containing the value of a CSS `style` attribute.

    Returns:
        A dictionary of style properties.
    """
    # SVG whitespace
    _SVG_WS = ' \t\r\n\f'
    style_map = {}
    if inline_style is not None and inline_style:
        for style_property in inline_style.split(';'):
            if style_property:
                name, value = style_property.split(':')
                name = name.strip(_SVG_WS)
                value = value.strip(_SVG_WS)
                if name and value:
                    style_map[name] = value
    return style_map


def dict_to_inline_style(style_map):
    """Create an inline style attribute string from a dictionary
    of CSS style properties.

    Args:
        style_map: A dictionary of CSS style properties.

    Returns:
        A string containing inline CSS style properties.
    """
    style_properties = [name + ':' + str(value)
                        for name, value in style_map.items()]
    return ';'.join(style_properties)


def csscolor_to_rgb(css_color):
    """Parse a CSS color property value into an RGB value.

    Args:
        css_color: A CSS color property string. I.e. \"#ffc0ee\" or
            \"white\".

    Returns:
        A tuple containing the RGB values: (r, g, b).

    See:
        https://developer.mozilla.org/en-US/docs/Web/CSS/color
    """
    # Normalize the property string
    rgb = None
    css_color = css_color.strip().lower()
    if css_color.startswith('#'):
        rgb = csshex_to_rgb(css_color)
    elif css_color.startswith('rgb'):
        rgb = cssrgb_to_rgb(css_color)
    elif css_color.startswith('hsl'):
        # TODO: implement hsl conversion
        pass
    else:
        rgb = CSS_COLORS.get(css_color)
        # If it's not a named color then as a last ditch effort
        # see if it might just be missing a '#' prefix. This is
        # not really part of the SVG spec but makes things a little
        # more forgiving...
        if rgb is None and all(c in string.hexdigits for c in css_color):
            rgb = csshex_to_rgb(css_color)
    if rgb is None or not rgb:
        rgb = (0, 0, 0)
    return rgb


def csshex_to_rgb(hex_color):
    """Convert a CSS hex color property to RGB.

    Args:
        hex_color: A CSS hex property string.

    Returns:
        The RGB value as a tuple of three integers: (r, g, b).
        Returns (0, 0, 0) by default if the hex value can't be parsed.
    """
    rgb = None
    hex_color = hex_color.strip().lstrip('#')
    try:
        if len(hex_color) == 6:
            rgb = (int(hex_color[0:2], 16),
                   int(hex_color[2:4], 16),
                   int(hex_color[4:], 16))
        elif len(hex_color) == 3:
            red = int(hex_color[0], 16)
            green = int(hex_color[1], 16)
            blue = int(hex_color[2], 16)
            rgb = (red * 16 + red, green * 16 + green, blue * 16 + blue)
    except ValueError:
        pass
    if rgb is None:
        rgb = (0, 0, 0)
    return rgb


def cssrgb_to_rgb(rgb_color):
    """Convert a CSS rgb or rgba color property to RGB.

    Args:
        rgb_color: A CSS rgb property string: i.e. `rgb(r, g, b)`.

    Returns:
        The RGB value as a tuple or list of three integers plus
        an optional fourth float value if there is an alpha channel.
        Returns (0, 0, 0) by default if the hex value can't be parsed.
    """
    rgb = []
    numbers = rgb_color.strip().strip('rgba() ').split(',')
    for num in numbers[:4]:
        n = parse_channel_value(num)
        rgb.append(n)
    for unused in range(3 - len(rgb)):
        rgb.append(0)
    if not rgb:
        return (0, 0, 0)
    return rgb


def parse_channel_value(value):
    """Parse a CSS color channel value.

    Args:
        value: A valid CSS color channel value string.
            Can be an integer number or an integer percentage.

    Returns:
        An integer value between 0 and 255.
        Default is 0 if the value isn't a valid channel value.
    """
    n = 0
    value = value.strip()
    try:
        if value.endswith('%'):
            n = int((float(value.rstrip('%')) / 100.0) * 255)
        elif value.isnumeric():
            n = int(value)
    except ValueError:
        pass
    return max(min(n, 255), 0)


def csscolor_to_cssrgb(color):
    """
    Returns a CSS color in the form #rrggbb.
    If `color` is a numeric value then it is converted to
    a grayscale number. If the number is a floating point value
    between zero and one then it is scaled up to 0-255 grayscale.
    If the CSS color can't be parsed then #000000 is returned.

    Args:
        A possibly malformed CSS color string or number.

    Returns:
        A CSS color in the form #rrggbb.
    """
    rgb = None
    if isinstance(color, numbers.Number):
        gray = 0
        if color > 0.0 and color < 1.0:
            gray = int(color * 255)
        elif color < 256:
            gray = int(color)
        rgb = (gray, gray, gray)
    else:
        rgb = csscolor_to_rgb(color)
    if rgb is None:
        return '#000000'
    return '#%02x%02x%02x' % rgb