import inspect
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Tuple, Any
import coloredlogs

import re
import argparse

import yaml

LOGGER = logging.getLogger()


class Config:
    _config: dict[str, str | dict[str, str] | None] = {
        "admin_domain_password": "",
        "admin_vm_password": "",
        "admin_vm_ssh_key": "",
        "admin_vm_ssh_keypair_name": "my_ssh_public_key",
        "project_ipv4_subnet": "192.168.200.0/24",
        "public_network": "public",
        "network_mtu": "0",
        "number_of_floating_ips_per_project": "1",
        "vm_flavor": "SCS-1L-1",
        "vm_image": "Ubuntu 24.04",
        "vm_volume_size_gb": "10",
        "verify_ssl_certificate": "false",
        "cloud_init_extra_script": """#!/bin/bash\necho "HELLO WORLD"; date > READY; whoami >> READY""",
        "wait_for_server_timeout": "300",
    }

    _file: str | None = None

    @staticmethod
    def get(key: str, regex: str = ".+", multi_line: bool = False) -> str:
        if key not in Config._config:
            LOGGER.error(f"{key} not in config")
            sys.exit(1)

        values: list[str] = []
        if multi_line:
            values = str(Config._config[key]).splitlines()
        else:
            values.append(str(Config._config[key]))

        for value in values:
            matcher = re.compile(regex, re.MULTILINE | re.DOTALL)
            if not matcher.fullmatch(value):
                LOGGER.error(
                    f"{key} : >>>{value}<<< : does not match to regex >>>{regex}<<<"
                )
                sys.exit(1)

        if len(values) > 1:
            return "\n".join(values)
        else:
            return values[0]

    @staticmethod
    def load_config(config_file: str):
        potential_profile_file = str(
            os.path.realpath(os.path.dirname(os.path.realpath(__file__)))
            + f"/../../../profiles/{config_file}"
        )

        if os.getenv("OPENSTACK_WORKLOAD_MANAGER_PROFILES", None):
            potential_profile_file = str(
                Path(
                    os.getenv("OPENSTACK_WORKLOAD_MANAGER_PROFILES", "NONE")
                )  # satisfy type-check
                / Path(config_file)
            )
            LOGGER.info(
                "Environment variable OPENSTACK_WORKLOAD_MANAGER_PROFILES set,"
                f" searching for potential {potential_profile_file}"
            )

        if os.path.exists(config_file):
            Config._file = config_file
        elif not str(config_file).startswith("/") and os.path.exists(
            potential_profile_file
        ):
            Config._file = potential_profile_file
        else:
            LOGGER.error(
                f"Cannot find a profile at {config_file} or {potential_profile_file}"
            )
            sys.exit(1)

        Config._file = os.path.realpath(Config._file)

        try:
            LOGGER.info(f"Reading {Config._file}")
            with open(str(Config._file), "r") as file_fd:
                Config._config.update(yaml.safe_load(file_fd))

        except Exception as e:
            LOGGER.error(f"Unable to read configuration: {e}")
            sys.exit(1)

    @staticmethod
    def check_config(cls):
        methods = inspect.getmembers(cls, predicate=inspect.isfunction)
        for name, method in methods:
            if name.startswith("get_"):  # Check for "get_" prefix
                method()
        for quota_type in ["compute_quotas", "block_storage_quotas", "network_quotas"]:
            if quota_type not in Config._config:
                continue
            for key_name in Config._config[quota_type].keys():
                Config.quota(key_name, quota_type, 0)

    @staticmethod
    def show_effective_config():
        Config.check_config(Config)
        LOGGER.info(
            "The effective configuration from %s : \n>>>\n---\n%s\n<<<"
            % (
                Config._file,
                yaml.dump(Config._config, default_flow_style=False, width=10000),
            )
        )

    @staticmethod
    def get_public_network() -> str:
        return Config.get("public_network", "[a-zA-Z][a-zA-Z0-9]*")

    @staticmethod
    def get_number_of_floating_ips_per_project() -> int:
        return int(Config.get("number_of_floating_ips_per_project", r"[1-9]\d*"))

    @staticmethod
    def get_admin_vm_password() -> str:
        return Config.get("admin_vm_password")

    @staticmethod
    def get_vm_flavor() -> str:
        return Config.get("vm_flavor")

    @staticmethod
    def get_cloud_init_extra_script() -> str:
        return Config.get("cloud_init_extra_script", multi_line=True)

    @staticmethod
    def get_vm_image() -> str:
        return Config.get("vm_image")

    @staticmethod
    def get_vm_volume_size_gb() -> int:
        return int(Config.get("vm_volume_size_gb", regex=r"\d+"))

    @staticmethod
    def get_admin_vm_ssh_keypair_name() -> str:
        return Config.get("admin_vm_ssh_keypair_name")

    @staticmethod
    def get_wait_for_server_timeout() -> int:
        return int(Config.get("wait_for_server_timeout", regex=r"\d+"))

    @staticmethod
    def get_project_ipv4_subnet() -> str:
        return Config.get("project_ipv4_subnet", regex=r"\d+\.\d+\.\d+\.\d+/\d\d")

    @staticmethod
    def get_admin_vm_ssh_key() -> str:
        return Config.get("admin_vm_ssh_key", r"ssh-\S+\s\S+\s\S+", multi_line=True)

    @staticmethod
    def get_admin_domain_password() -> str:
        return Config.get("admin_domain_password", regex=r".{5,}")

    @staticmethod
    def get_verify_ssl_certificate() -> bool:
        value = Config.get("verify_ssl_certificate", regex=r"true|false|True|False")
        if value.lower() == "false":
            return False
        else:
            return True

    @staticmethod
    def configured_quota_names(quota_category: str) -> list[str]:
        if quota_category in Config._config:
            value = Config._config[quota_category]
            if isinstance(value, dict):
                return list(value.keys())
        return []

    @staticmethod
    def quota(quota_name: str, quota_category: str, default_value: int) -> int:
        if quota_category in Config._config:
            value = Config._config.get(quota_name, default_value)
            if isinstance(value, int):
                return value
            else:
                LOGGER.error(
                    f"Quota {quota_category} -> {quota_name} is not an integer"
                )
                sys.exit(1)
        else:
            return default_value

    @staticmethod
    def get_network_mtu():
        return int(Config.get("network_mtu", regex=r"\d+"))


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
        domain = DomainCache.ident_by_id(
            ProjectCache.PROJECT_CACHE[project_id]["domain_id"]
        )
        return f"project '{project}' in {domain}"

    @staticmethod
    def add(project_id: str, data: dict[str, str]):
        ProjectCache.PROJECT_CACHE[project_id] = data


def setup_logging(log_level: str) -> Tuple[logging.Logger, str]:
    log_format_string = (
        "%(asctime)-10s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    logger = logging.getLogger()
    log_file = "STDOUT"
    logging.basicConfig(format=log_format_string, level=log_level)

    coloredlogs.DEFAULT_FIELD_STYLES["levelname"] = {"bold": True, "color": ""}
    coloredlogs.install(fmt=log_format_string, level=log_level.upper())

    return logger, log_file


def cloud_checker(value: str) -> str:
    if not re.fullmatch("[a-zA-Z0-9-]+", value):
        raise argparse.ArgumentTypeError("specify a value for os_cloud")
    return value


def item_checker(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9]+[a-zA-Z0-9\-]*[a-zA-Z0-9]+", value):
        raise argparse.ArgumentTypeError("specify a valid name for an item")
    return value


def iso_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def deep_merge_dict(d1: dict, d2: dict) -> dict[str, Any]:
    result = d1.copy()
    for key, value in d2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dict(result[key], value)
        else:
            result[key] = value
    return result
