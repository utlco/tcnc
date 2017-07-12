#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import os
import io
import fnmatch
import logging


logger = logging.getLogger(__name__)

DEFAULT_DIR = '~'
DEFAULT_BASENAME = 'output'
DEFAULT_EXT = '.ngc'


def create_pathname(filepath, append_suffix=False,
                    default_dir=DEFAULT_DIR,
                    default_basename=DEFAULT_BASENAME,
                    default_ext=DEFAULT_EXT):
    """Generate an absolute file path name based on the specified path.
    The pathname can optionally have an auto-incrementing numeric suffix.

    Args:
        filepath: Pathname of output file. If the directory, file name, or
            file extension are missing then defaults will be used.
        append_suffix: Append an auto-incrementing numeric suffix to the
            file name if True. Default is False.

    Returns:
        An absolute path name.
    """
    filepath = os.path.abspath(os.path.expanduser(filepath.strip()))
    filedir, basename = os.path.split(filepath)
    if not filedir:
        filedir = os.path.abspath(os.path.expanduser(default_dir))
    file_root, file_ext = os.path.splitext(basename)
    if not file_root:
        file_root = default_basename
    if not file_ext:
        file_ext = default_ext
    basename = file_root + file_ext # Rebuild in case of defaults
    if append_suffix:
        # Get a list of existing files that match the numeric suffix.
        # They should already be sorted.
        filter_str = '%s_[0-9]*%s' % (file_root, file_ext)
        files = fnmatch.filter(os.listdir(filedir), filter_str)
        if len(files) > 0:
            # Get the suffix from the last one and add one to it.
            # This seems overly complicated but it takes care of the case
            # where the user deletes a file in the middle of the
            # sequence, which guarantees the newest file will always
            # have the highest numeric suffix.
            last_file = files[-1]
            file_root, file_ext = os.path.splitext(last_file)
            if len(file_root) > 4:
                try:
                    suffix = int(file_root[-4:]) + 1
                except ValueError:
                    suffix = 0
            basename = file_root[:-4] + ('%04d' % suffix) + file_ext
        else:
            basename = file_root + '_0000' + file_ext
    return os.path.join(filedir, basename)
