===============
Installing Tcnc
===============


For now installation must be done by hand...

Example shell commands should work on MacOS/Linux.
For Windows/Cygwin see :ref:`location`.

1. `Download <https://github.com/utlco/tcnc/archive/master.zip>`_
   the latest version::

      curl -L -O "https://github.com/utlco/tcnc/archive/master.zip"

2. Unzip/extract the downloaded archive file (tcnc-master.zip)::

      unzip tcnc-master.zip

3. Copy or move the Inkscape extension description (.inx) files
   in **tcnc-master/inkinx**
   to the Inkscape user extension folder::

      cp tcnc-master/inkinx/\*.inx ~/.config/inkscape/extensions

4. Copy or move the entire **tcnc** folder from **tcnc-master**
   to the Inkscape user extension folder::

      cp -R tcnc-master/tcnc ~/.config/inkscape/extensions

5. Restart Inkscape.

.. _location:

Inkscape user extension folder location
---------------------------------------

* MacOS, Linux:

   `~/.config/inkscape/extensions`, where *~* is your home
   directory (i.e. /Users/YourUserName).

* Windows:

   `C:\\Users\\YourUserName\\.Appdata\\Roaming\\inkscape\\extensions`

