import logging
import os
import sys
from pprint import pformat
from typing import Tuple
import coloredlogs

import re
import argparse

import yaml

LOGGER = logging.getLogger()


class Config:
    _config: dict[str, str | dict[str, str]] = dict()
    _file: str = None

    @staticmethod
    def get(key: str, regex: str = ".+",
            multi_line: bool = False, parent_key: str | None = None, default: str | list[str] | None = None) -> str | \
                                                                                                                list[
                                                                                                                    str]:
        lines = [default]
        try:
            if parent_key:
                lines = str(Config._config[parent_key][key]).splitlines()
            else:
                lines = str(Config._config[key]).splitlines()
        except KeyError:
            LOGGER.info(f"config does not contain : {parent_key or 'ROOT'} -> {key}, using >>>{default}<<<")
            if lines is None:
                sys.exit(1)

        if len(lines) > 1 and multi_line is False:
            LOGGER.error(f"{key}='{Config._config[key]}' contains multiple lines")
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

    @staticmethod
    def load_config(config_file: str):
        try:
            if not str(config_file).startswith("/"):
                config_file = \
                    str(os.path.realpath(
                        os.path.dirname(os.path.realpath(__file__))) + "/../../../profiles/default.yaml")

            Config._file = config_file
            with open(config_file, 'r') as file:
                Config._config = yaml.safe_load(file)

        except Exception as e:
            LOGGER.error(f"Unable to read configuration: {e}")
            sys.exit(1)

    @staticmethod
    def show_effective_config():
        LOGGER.info(
            "The effective configuration from %s : \n>>>\n%s\n<<<" % (
                Config._file, pformat(Config._config, indent=2, compact=False))
        )


class DomainCache:
    _domains: dict[str, str] = dict()

    @staticmethod
    def ident_by_id(domain_id: str) -> str:
        if domain_id not in DomainCache._domains:
            raise RuntimeError(f"There is no domain with id {domain_id}")
        return f"domain '{DomainCache._domains[domain_id]}/{domain_id}'"

    @staticmethod
    def add(domain_id: str, name: str):
        DomainCache._domains[domain_id] = name


class ProjectCache:
    PROJECT_CACHE: dict[str, dict[str, str]] = dict()

    @staticmethod
    def ident_by_id(project_id: str) -> str:
        if project_id not in ProjectCache.PROJECT_CACHE:
            raise RuntimeError(f"There is no project with id {project_id}")
        project = f'{ProjectCache.PROJECT_CACHE[project_id]["name"]}/{project_id}'
        domain = DomainCache.ident_by_id(ProjectCache.PROJECT_CACHE[project_id]["domain_id"])
        return f"project '{project}' in {domain}"

    @staticmethod
    def add(project_id: str, data: dict[str,str]):
        ProjectCache.PROJECT_CACHE[project_id] = data


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
