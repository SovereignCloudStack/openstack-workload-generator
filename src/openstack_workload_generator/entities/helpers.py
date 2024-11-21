import logging
import sys
from typing import Tuple
import coloredlogs

import re
import argparse

LOGGER = logging.getLogger()

class Config:
    CONFIG: dict[str, str | dict[str, str]] = dict()

    @staticmethod
    def get(key: str, regex: str = ".+",
            multi_line: bool = False, parent_key: str | None = None, default: str | list[str] | None = None) -> str | \
                                                                                                                       list[
                                                                                                                           str]:
        lines = [default]
        try:
            if parent_key:
                lines = str(Config.CONFIG[parent_key][key]).splitlines()
            else:
                lines = str(Config.CONFIG[key]).splitlines()
        except KeyError:
            LOGGER.info(f"config does not contain : {parent_key or 'ROOT'} -> {key}, using >>>{default}<<<")
            if lines is None:
                sys.exit(1)

        if len(lines) > 1 and multi_line is False:
            LOGGER.error(f"{key}='{Config.CONFIG[key]}' contains multiple lines")
            sys.exit(1)

        for line in lines:
            matcher = re.compile(regex, re.MULTILINE | re.DOTALL)
            if not matcher.fullmatch(str(line)):
                LOGGER.error(f"{key} : >>>{line}<<< : does not match to regex >>>{regex}<<<")
                sys.exit(1)

        if not multi_line:
            return str(lines[0])
        else:
            return [str(val) for val in lines]


class DomainCache:
    DOMAIN_CACHE: dict[str, str] = dict()

    @staticmethod
    def domain_ident(domain_id: str) -> str:
        if domain_id not in DomainCache.DOMAIN_CACHE:
            raise RuntimeError(f"There is no domain with id {domain_id}")
        return f"domain '{DomainCache.DOMAIN_CACHE[domain_id]}/{domain_id}'"

class ProjectCache:
    PROJECT_CACHE: dict[str, dict[str, str]] = dict()

    @staticmethod
    def project_ident(project_id: str) -> str:
        if project_id not in ProjectCache.PROJECT_CACHE:
            raise RuntimeError(f"There is no project with id {project_id}")
        project = f'{ProjectCache.PROJECT_CACHE[project_id]["name"]}/{project_id}'
        domain = DomainCache.domain_ident(ProjectCache.PROJECT_CACHE[project_id]["domain_id"])
        return f"project '{project}' in {domain}"

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

