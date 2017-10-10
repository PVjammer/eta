'''
Encapsulates an npz file that stores model weights locally in a cache and has
the ability to pull a version of the  weights down from the net.

@todo: this should probably be:
    (1) extended to allow for methods to visualize, display, and debug weights
    (2) refactored out so the actual backing store code can be generally used

Copyright 2017, Voxel51, LLC
voxel51.com

Jason Corso, jjc@voxel51.com
'''
import os

import numpy as np

from config import Config
from eta import constants
import utils as ut


class WeightsConfig(Config):
    '''Weights configuration settings.'''

    def __init__(self, d):
        self.weights_cache = self.parse_string(
            d, "weights_cache", default=constants.DEFAULT_CACHE_DIR)
        self.weights_filename = self.parse_string(d, "weights_filename")
        self.weights_url = self.parse_string(d, "weights_url", default=None)
        self.weights_large_google_drive_file_flag = self.parse_bool(
            d, "weights_large_google_drive_file_flag", default=False)

    @property
    def weights_path(self):
        return os.path.join(self.weights_cache, self.weights_filename)


class Weights(Config):
    '''Weights class that encapsulates model weights and can load them from the
    net if needed (and if paths are provided).

    @todo: Would be great to make this class act like the actual dictionary it
    loads, by overloading/implementing the same methods.
    '''

    def __init__(self, weights_config):
        self.config = weights_config
        self.data = None

        # Check if the file is locally stored.
        if not os.path.isfile(self.config.weights_path):
            if self.config.weights_large_google_drive_file_flag:
                b = ut.download_large_google_drive_file(self.config.weights_url)
            else:
                b = ut.download_file(self.config.weights_url)

            ut.ensure_dir(self.weights_path)
            with open(self.config.weights_path, "wb") as f:
                f.write(b)

        # Can this be ingested directly from 'b' if we downloaded it?
        self.data = np.load(self.config.weights_path)
