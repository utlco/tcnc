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

PROJ_DIR = path.abspath('../')
TEST_PKG = 'test'
INKEXT_PKG = 'tcnc'

HOME = os.environ['HOME']
INKEXT_DST_DIR = path.join(HOME, path.normpath('.config/inkscape/extensions'))


def main():
    # Create symbolic links to Inkscape extension INX files
    link_inx_files(INKINX_SRC_DIR)
    # Create symbolic link to the extension development package
    inkext_src = path.join(PROJ_DIR, INKEXT_PKG)
    inkext_dst = path.join(INKEXT_DST_DIR, INKEXT_PKG)
    create_symlink(inkext_src, inkext_dst)
    # Create symbolic links to extensions in the test folder
    test_pkg_dir = path.join(PROJ_DIR, TEST_PKG)
    test_pkg_link = path.join(INKEXT_DST_DIR, TEST_PKG)
    link_inx_files(test_pkg_dir)
    create_symlink(test_pkg_dir, test_pkg_link)


def link_inx_files(src_dir):
    """Create symbolic links to Inkscape extension INX files
    """
    inkinx_files = os.listdir(src_dir)
    for inxfile in inkinx_files:
        dummy, ext = path.splitext(inxfile)
        if ext.lower() != '.inx':
            continue
        inxpath_src = path.join(src_dir, inxfile)
        inxpath_dst = path.join(INKEXT_DST_DIR, inxfile)
        create_symlink(inxpath_src, inxpath_dst)


def create_symlink(pathname, symlink_pathname):
    """
    Args:
        pathname: Pathname of file to create a symbolic link to
        symlink_pathname: Name of symbolic link
    """
    # If the symbolic link already exists or a file
    # of the same name exists then remove it.
    if path.exists(symlink_pathname):
        if not path.islink(symlink_pathname):
            query_str = 'Remove existing file %s?' % symlink_pathname
            # If the symlink pathname is an actual file then
            # get confirmation from user to delete it.
            if not query_yesno(query_str):
                print 'Not creating link to ' + pathname
                return
        try:
            print 'Removing ' + symlink_pathname
            os.remove(symlink_pathname)
        except OSError, error:
            print error
            exit(-1)
    # Create a symbolic link to the pathname.
    try:
        print symlink_pathname + ' --> ' + pathname
        os.symlink(pathname, symlink_pathname)
    except OSError, error:
        print error
        exit(-1)

def confirm_remove_nonsymlink(filepath):
    remove_path = True
    if path.exists(filepath) and not path.islink(filepath):
        # If the file exists and is not a symbolic link then
        # confirm removal.
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

