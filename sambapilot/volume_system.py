"""Sondes locales Linux explicitement demandées : table et métadonnées, sans sous-processus."""

import errno
import os
from pathlib import Path, PurePosixPath
import platform

from .volumes import DirectoryObservation, MAX_MOUNTINFO_BYTES


class HostVolumeProbe:
    mode = 'live'

    def system(self):
        return platform.system()

    def mountinfo(self):
        try:
            with Path('/proc/self/mountinfo').open('rb') as stream:
                data = stream.read(MAX_MOUNTINFO_BYTES + 1)
            if len(data) > MAX_MOUNTINFO_BYTES:
                return '', 'oversized'
            return data.decode('utf-8'), None
        except (OSError, UnicodeError):
            return '', 'unavailable'

    def directory(self, path):
        path_flag = getattr(os, 'O_PATH', None)
        if path_flag is None:
            return DirectoryObservation('unknown')
        descriptor = None
        flags = path_flag | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        try:
            descriptor = os.open('/', flags)
            for part in PurePosixPath(path).parts[1:]:
                child = os.open(part, flags, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            device = os.fstat(descriptor).st_dev
            return DirectoryObservation('present', f'{os.major(device)}:{os.minor(device)}')
        except FileNotFoundError:
            return DirectoryObservation('missing')
        except OSError as error:
            return DirectoryObservation('not-directory' if error.errno in {errno.ELOOP, errno.ENOTDIR} else 'unknown')
        finally:
            if descriptor is not None:
                os.close(descriptor)
