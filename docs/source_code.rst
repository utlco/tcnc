===========
Source Code
===========

Modules
-------

.. toctree::
    :maxdepth: 2

    api_extensions.rst

    api_inkscape.rst

    api_svg.rst

    api_geom.rst

    api_cam.rst

* :ref:`modindex`


Notes
-----

While performance
is important, maintainability and clarity has been more of a priority.

My memory is too unreliable to understand some opaque code I wrote
two months ago, so I've tried to mitigate this somewhat.
I'm sure there are bugs.

Why do it
.........
You may be wondering why I didn't just use or extend **gcodetools**,
which is currently packaged with Inkscape.
Well, to be honest I found the author's code difficult to follow
and it was very time consuming to customize for my needs.
I had a hard time understanding the author's biarc
curve approximation algorithm so I went to primary
sources and wrote my own version that works pretty well (maybe even
a bit better).

Like any programmer I've a mild case of NIH syndrome and I also just
wanted code that I understood well and could modify easily and quickly
for project-specific requirements.

Lots of people use gcodetools and it has many more features
(such as pocketing and raster fills).
I highly recommend checking it out.

Unit confusion
..............
Unit handling in SVG and Inkscape is confusing at best.

The problem mainly stems from SVG's viewbox/viewport handling and
Inkscape's concept of a 'document unit'.
In addition, the SVG `viewbox` attribute can specify
a box with a different aspect ratio than its parent - which is really only
relevant in web browser contexts.
Inkscape calls document units 'default units' in the UI,
which further confuses things.
Weirdly, the default document unit is pixels
even when using a document template specified in inches or mm.

Anyway for the purposes of using tcnc as an Inkscape extension,
the simplest way to deal with this
is in *File->Document Properties...*,
set the 'default units' to the same value as the units used to specify the
document size, and to use either inches or mm for both.

Inkscape extensions
...................
If you are wondering how to build an Inkscape extension then it might
be helpful to look at this source code. There are some reusable components
as well that make writing extensions a little easier.

I suggest also taking a look at clearly written and well documented extensions
such as the
[Eggbot](https://github.com/evil-mad/EggBot) extension.
Documentation about Inkscape extensions is fairly poor
and the best way to learn how to write one is to look at previous attempts.

Feel free to reuse
..................
There are also some handy libraries, such as the SVG and geometry modules,
that are more generally useful. I rewrote the Inkscape extension classes
partly because Inkscape version .91 broke my extensions (mainly because of unit
handling) and I just wanted to
hoist more of the biolerplate involved with writing extensions.

I added a **docunits** option checker to convert UI values to current
document units automatically. The creation of a debug layer and
logging output file is done by the extension base class as well.

If you find any of this useful, great!

Apologia
........
I've been slowly converting
doc strings to the Google python style since it's more readable than
the standard reStructuredText style. There's currently a mix of the
two styles... Sphinx handles both just fine.

Testing has been artisinal.

Most modules produce a lot of pylint warnings.

An attempt has been made to start migrating the code to full
python3 compatibility, but this has not been tested. Inkscape
still depends on Python 2.6+...

Emails, pull requests, feature requests,
and issues are infrequently examined and may be left ignored
for an uncomfortably long period of time... Sorry about that.
Bug reports are welcome in any case.

