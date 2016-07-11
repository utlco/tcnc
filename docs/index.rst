
====
Tcnc
====

.. toctree::
    :maxdepth: 1

    usage_tcnc.rst
    source_code.rst

* :ref:`genindex`

* :ref:`search`

Introduction
------------
Tcnc is an Inkscape extension that generates G-code targeted for a four (or 3.5)
axis CNC machine controlled by LinuxCNC v2.4+. The fourth axis (A) is angular
and is assumed to rotate about a vertical Z axis. The tool path is calculated
so that the A axis is kept tangent to movement along the X and Y axis. This is
designed to move a tangential tool
such as a brush, scraper, or knife centered along the path.

Tcnc will calculate tool paths to compensate for a trailing tool offset (such as
a flexible brush whose contact with the surface trails behind the Z axis
center) and can also perform automatic filleting to compensate for distortions
caused by tool width. See :ref:`trail-offset` and :ref:`tool-width`.

There is an optional feature that will smooth the path by adding very small arc
fillets at non-tangent path vertices, which can speed up feed rates. This is
probably not necessary if LinuxCNC version 2.8+ is used since it has built-in
toolpath blending.

Bezier curves are converted to circular arcs using a biarc approximation method.
Compared to using line segment approximation this results in much smaller G
code files (by orders of magnitude) and faster machine operation. Accuracy is
very good.

Tcnc is currently used to produce G code for a painting apparatus based on a
modified Fletcher 6100 CNC mat cutter controlled by LinuxCNC. A stepper
controlled Z axis was added. The original pneumatic tool pusher was left on and
is triggered by **spindle_on**. This allows for fast brush lifts along with
very fine Z axis control. I haven't tested this with anything else so YMMV.

Tcnc does not perform tool path buffering to compensate for kerf created by
cutting tools such as router bits, lasers, plasma cutters, or water jets. If
kerf is not an issue or the user is willing to manually compensate for it by
adjusting the input paths then this might work just fine for these applications.

**Tcnc** is an ongoing project that is mainly designed for my personal use and
some of the features may seem weirdly specific.

There is absolutely no warranty for any purpose whatsoever. Use at your own risk.

Installation
------------

For now installation must be done by hand...

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


