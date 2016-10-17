
.. image:: https://readthedocs.org/projects/tcnc/badge/?version=latest
   :target: http://tcnc.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

====
TCNC
====

* Documentation: https://tcnc.readthedocs.io
* GitHub: https://github.com/utlco/tcnc
* Free software: LGPL v3 license

Tcnc is an Inkscape (version .91+) extension that generates
G-code suitable for a
3.5 axis CNC machine controlled by LinuxCNC v2.4+.
The rotational axis (A) is assumed to rotate about
the Z axis and is kept tangent to movement along the X and Y axis.

It is currenty used to produce output for a painting apparatus based on
a modified Fletcher 6100 CNC mat cutter controlled by LinuxCNC. A stepper
controlled Z axis was added. The original pneumatic tool pusher was left on
and is triggered by **spindle_on**. This allows for fast brush lifts along
with very fine Z axis control.
I haven't tested this with anything else so YMMV.

Tcnc uses biarc approximation to convert Bezier curves
into circular arc segments. This produces smaller G code files and
is very accurate.

Machine-specific Behavior
-------------------------
You can specify a tool width in tcnc to compensate for tool trail.
Tool trail is the distance between the center of rotation around the Z axis
and the tool contact point. This is a property of flexible brushes.
This minimizes weird looking brush strokes
during relatively sharp changes in direction and produces a much more accurate
brush path.

Other Inkscape Extensions in This Package
-----------------------------------------

Quasink
.......
Quasink is an Inkscape extension that produces
quasicrystal/Penrose tesselations.
Even and odd degrees of symmetry are supported.
This extension has a lot of obscure options
that are probably only useful to me...

It is based on quasi.c by Eric R. Weeks.
See <http://www.physics.emory.edu/~weeks/software/quasic.html> for more info.

Rhombus fills are done using LUTs instead of the unusual coloring method
used in the original code.

Voronoi
.......
Create Voronoi diagrams from points or the vertices of
arbitrary geometry.

Polysmooth
..........
Smooth polyline/polygons using Bezier splines. Allows the user to
specify the amount of smoothing applied.

Sinewave
........
Create a nice sine wave using cubic Bezier approximation.


Installing tcnc
---------------

1. `Download <https://github.com/utlco/tcnc/archive/master.zip>`_
   the latest version.

2. Unzip/extract the downloaded archive file (master.zip).

3. Copy or move the contents of the **tcnc/inkinx** folder
   to the user Inkscape extension folder.

4. Copy or move the entire **tcnc/tcnc** folder
   to the user Inkscape extension folder.

5. Restart Inkscape.

**Location of user Inkscape extension folder:**

* MacOS, Linux:

    `~/.config/inkscape/extensions`, where *~* is your home
    directory (i.e. /Users/YourUserName).

* Windows:

    `C:\\Users\\YourUserName\\.Appdata\\Roaming\\inkscape\\extensions`

Notes
-----

These extensions do not depend at all on the extension libraries supplied
with Inkscape. In fact, you can run these as standalone command line tools
without Inkscape being installed.


Etc...
------
Tcnc is an ongoing project that is mainly designed for my own use
and some of the features may seem weirdly specific. Some of the code is in
a high state of flux due to rapid cycle experimentation.

There are some handy libraries, such as the SVG and geometry modules,
that are more generally handy. I rewrote the Inkscape extension classes
since the .91 version broke the .48 extensions and I just wanted to
hoist more of the biolerplate involved with writing Inkscape extensions.

I added a **docunits** option checker to convert UI values to current
document units automatically. The creation of a debug layer and
logging output file is done by the extension base class as well.

If you find this useful, great!

There is absolutely no warranty for any purpose whatsoever.
Use at your own risk.

Emails, pull requests, feature requests,
and issues are infrequently examined and may be left ignored
for an uncomfortably long period of time... Sorry about that.

