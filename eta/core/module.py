'''
Core module infrastructure.

Copyright 2017, Voxel51, LLC
voxel51.com

Brian Moore, brian@voxel51.com
'''
# pragma pylint: disable=redefined-builtin
# pragma pylint: disable=unused-wildcard-import
# pragma pylint: disable=wildcard-import
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import *
# pragma pylint: enable=redefined-builtin
# pragma pylint: enable=unused-wildcard-import
# pragma pylint: enable=wildcard-import

from eta.core.config import Config
from eta.core import log


def setup(module_config):
    '''Perform module setup.

    Args:
        module_config: a Config instance derived from BaseModuleConfig
    '''
    # Setup logging
    log.custom_setup(module_config.logging_config)


class BaseModuleConfig(Config):
    '''Base module configuration settings.'''

    def __init__(self, d):
        self.logging_config = self.parse_object(
            d, "logging_config", log.LoggingConfig,
            default=log.LoggingConfig.default())