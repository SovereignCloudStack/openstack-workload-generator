import logging
from typing import Tuple
import coloredlogs

import re
import argparse

LOGGER = logging.getLogger()


def setup_logging(log_level: str) -> Tuple[logging.Logger, str]:
    log_format_string = \
        '%(asctime)-10s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    logger = logging.getLogger()
    log_file = "STDOUT"
    logging.basicConfig(format=log_format_string,
                        level=log_level)

    coloredlogs.DEFAULT_FIELD_STYLES["levelname"] = {'bold': True, 'color': ''}
    coloredlogs.install(fmt=log_format_string, level=log_level.upper())

    return logger, log_file


def cloud_checker(value: str) -> str:
    if not re.fullmatch("[a-zA-Z0-9]+", value):
        raise argparse.ArgumentTypeError('specify a value for os_cloud')
    return value


def item_checker(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9]+[a-zA-Z0-9\-]*[a-zA-Z0-9]+", value):
        raise argparse.ArgumentTypeError('specify a valid name for an item')
    return value
