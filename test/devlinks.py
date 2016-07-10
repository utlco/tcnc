#!/usr/bin/env python
#
#-----------------------------------------------------------------------------
# Copyright 2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
This creates symbolic links to the Inkscape extensions in the
user's $HOME/.config/inkscape/extensions folder. This is intended
for a development environment where extension code can be modified
and tested while Inkscape is running.

Inkscape runs an extension as a separate process which makes this
possible.

This should work with Linux, MacOS, and Windows/Cygwin. If you
are developing on Windows without Cygwin then YMMV.
"""

import sys
import os
import errno
import distutils.util
from os import path

INKINX_SRC_DIR = path.abspath('../inkinx')

INKEXT_PKG = 'tcnc'
INKEXT_SRC_DIR = path.abspath('../')

HOME = os.environ['HOME']
INKEXT_DST_DIR = path.join(HOME, path.normpath('.config/inkscape/extensions'))


def main():
    # Create symbolic links to Inkscape extension INX files
    inkinx_files = os.listdir(INKINX_SRC_DIR)
    for inxfile in inkinx_files:
        inxpath_src = path.join(INKINX_SRC_DIR, inxfile)
        inxpath_dst = path.join(INKEXT_DST_DIR, inxfile)
        print inxpath_dst + ' --> ' + inxpath_src
        # If the installed extension already exists and is
        # not a symbolic link then ask for confirmation to
        # remove it first.
        if confirm_remove_nonsymlink(inxpath_dst):
            # Remove the existing INX file or link (if it exists).
            try:
                os.remove(inxpath_dst)
            except OSError, error:
                # Ignore File Doesn't Exist errors..
                if error.errno != errno.ENOENT:
                    print error
                    exit(-1)
            # Create a symbolic link to the devalopment INX file
            # in the Inkscape extensions folder.
            try:
                os.symlink(inxpath_src, inxpath_dst)
            except OSError, error:
                print error
                exit(-1)
        else:
            print 'Not creating link to ' + inxfile
    # Create symbolic link to the extension development package
    inkext_src = path.join(INKEXT_SRC_DIR, INKEXT_PKG)
    inkext_dst = path.join(INKEXT_DST_DIR, INKEXT_PKG)
    if confirm_remove_nonsymlink(inkext_dst):
        try:
            print 'Removing ' + inkext_dst
            os.remove(inkext_dst)
        except OSError, error:
            # Ignore File Doesn't Exist errors..
            if error.errno != errno.ENOENT:
                print error
                exit(-1)
        # Create a symbolic link to the development INX file
        # in the Inkscape extensions folder.
        try:
            print 'Creating symbolic link to ' + inkext_src
            os.symlink(inkext_src, inkext_dst)
        except OSError, error:
            print error
            exit(-1)
    else:
        print 'Not creating link to ' + INKEXT_PKG


def confirm_remove_nonsymlink(filepath):
    remove_path = True
    if path.exists(filepath) and not path.islink(filepath):
        remove_path = query_yesno('Remove existing file %s?' % filepath)
    return remove_path


def query_yesno(querystr, default_no=True):
    if default_no is None:
        prompt = ' [y|n] '
    elif default_no:
        prompt = ' [y|N] '
    else:
        prompt = ' [Y|n] '
    sys.stdout.write(querystr + prompt)
    while True:
        try:
            return distutils.util.strtobool(raw_input().lower())
        except ValueError:
            print 'Please enter yes or no.'


if __name__ == "__main__":
    main()

