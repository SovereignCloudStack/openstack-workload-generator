#!/usr/bin/env python3
import shutil
import sys
import os
import argparse
import logging
import time
from typing import Any

import yaml
from openstack.connection import Connection
from openstack.config import loader

from .entities import WorkloadGeneratorDomain
from .entities.helpers import setup_logging, cloud_checker, item_checker, Config, iso_timestamp, deep_merge_dict

LOGGER = logging.getLogger()

parser = argparse.ArgumentParser(prog="Create workloads on openstack installations")

parser.add_argument(
    "--log_level", metavar="loglevel", type=str, default="INFO", help="The loglevel"
)

parser.add_argument(
    "--os_cloud",
    type=cloud_checker,
    default=os.environ.get("OS_CLOUD", "admin"),
    help="The openstack config to use, defaults to the value of the OS_CLOUD "
    'environment variable or "admin" if the variable is not set',
)

parser.add_argument(
    "--ansible_inventory",
    type=str,
    nargs="?",
    help="Dump the created servers as an ansible inventory to the specified directory, "
    "adds a ssh proxy jump for the hosts without a floating ip",
)

parser.add_argument(
    "--clouds_yaml", type=str, nargs="?", help="Use a specific clouds.yaml file"
)

parser.add_argument(
    "--wait_for_machines",
    action="store_true",
    help="Wait for every machine to be created "
    "(normally the provisioning only waits for machines which use floating ips)",
)

parser.add_argument(
    "--generate_clouds_yaml",
    type=str,
    nargs="?",
    help="Generate a openstack clouds.yaml file",
)


parser.add_argument(
    "--config",
    type=str,
    default="default.yaml",
    help="The config file for environment creation, define a path to the"
    " yaml file or a subpath in the profiles folder",
)

exclusive_group_domain = parser.add_mutually_exclusive_group(required=True)

exclusive_group_domain.add_argument(
    "--create_domains",
    type=item_checker,
    nargs="+",
    default=None,
    metavar="DOMAINNAME",
    help="A list of domains to be created",
)

exclusive_group_domain.add_argument(
    "--delete_domains",
    type=item_checker,
    nargs="+",
    default=None,
    metavar="DOMAINNAME",
    help="A list of domains to be deleted, all child elements are recursively deleted",
)

exclusive_group_project = parser.add_mutually_exclusive_group(required=False)

exclusive_group_project.add_argument(
    "--create_projects",
    type=item_checker,
    nargs="+",
    default=None,
    metavar="PROJECTNAME",
    help="A list of projects to be created in the created domains",
)

exclusive_group_project.add_argument(
    "--delete_projects",
    type=item_checker,
    nargs="+",
    default=None,
    metavar="PROJECTNAME",
    help="A list of projects to be deleted in the created "
    "domains, all child elements are recursively deleted",
)

exclusive_group_machines = parser.add_mutually_exclusive_group(required=False)
exclusive_group_machines.add_argument(
    "--create_machines",
    type=item_checker,
    nargs="+",
    default=None,
    metavar="SERVERNAME",
    help="A list of vms to be created in the created domains",
)

exclusive_group_machines.add_argument(
    "--delete_machines",
    type=item_checker,
    nargs="+",
    default=None,
    metavar="SERVERNAME",
    help="A list of vms to be deleted in the created projects",
)

args = parser.parse_args()

if args.os_cloud == "":
    sys.exit(1)

setup_logging(args.log_level)


def establish_connection():
    if args.clouds_yaml is None:
        config = loader.OpenStackConfig()
    else:
        LOGGER.info(f"Loading connection configuration from {args.clouds_yaml}")
        config = loader.OpenStackConfig(config_files=[args.clouds_yaml])
    cloud_config = config.get_one(args.os_cloud)
    return Connection(config=cloud_config)


time_start = time.time()

Config.load_config(args.config)
Config.show_effective_config()

if args.create_domains:
    conn = establish_connection()
    workload_domains: dict[str, WorkloadGeneratorDomain] = dict()
    clouds_yaml_data: dict[str, dict[str, Any]] = dict()
    for domain_name in args.create_domains:
        domain = WorkloadGeneratorDomain(conn, domain_name)
        domain.create_and_get_domain()
        workload_domains[domain_name] = domain

    if args.create_projects:
        for workload_domain in workload_domains.values():
            workload_domain.create_and_get_projects(args.create_projects)

        for workload_domain in workload_domains.values():
            for workload_project in workload_domain.get_projects(args.create_projects):
                if args.create_machines:
                    workload_project.get_and_create_machines(
                        args.create_machines, args.wait_for_machines
                    )
                    if args.ansible_inventory:
                        workload_project.dump_inventory_hosts(args.ansible_inventory)
                    if args.clouds_yaml:
                        clouds_yaml_data[
                            f"{workload_domain.domain_name}-{workload_project.project_name}"
                        ] = workload_project.get_clouds_yaml_data()
                elif args.delete_machines:
                    for machine_obj in workload_project.get_machines(
                        args.delete_machines
                    ):
                        machine_obj.delete_machine()
        if args.generate_clouds_yaml:
            LOGGER.info(f"Creating a a clouds yaml : {args.generate_clouds_yaml}")
            clouds_yaml_data_new = {"clouds": clouds_yaml_data}
            if os.path.exists(args.generate_clouds_yaml):
                with open(args.generate_clouds_yaml, "r") as file:
                    existing_data = yaml.safe_load(file)
                backup_file = f"{args.generate_clouds_yaml}_{iso_timestamp()}"
                logging.warning(
                    f"File {args.generate_clouds_yaml}, making an backup to {backup_file} and adding the new values"
                )
                shutil.copy2(
                    args.generate_clouds_yaml,
                    f"{args.generate_clouds_yaml}_{iso_timestamp()}",
                )
                clouds_yaml_data_new = deep_merge_dict(
                    existing_data, clouds_yaml_data_new
                )

            with open(args.generate_clouds_yaml, "w") as file:
                yaml.dump(
                    clouds_yaml_data_new,
                    file,
                    default_flow_style=False,
                    explicit_start=True,
                )
        sys.exit(0)
    elif args.delete_projects:
        conn = establish_connection()
        for domain_name in args.create_domains:
            domain_obj = WorkloadGeneratorDomain(conn, domain_name)
            for project_obj in domain_obj.get_projects(args.delete_projects):
                project_obj.delete_project()
        sys.exit(0)

    duration = (time.time() - time_start) / 60
    LOGGER.info(f"Execution finished after {int(duration)} minutes")
elif args.delete_domains:
    conn = establish_connection()
    for domain_name in args.delete_domains:
        domain_obj = WorkloadGeneratorDomain(conn, domain_name)
        domain_obj.delete_domain()
    sys.exit(0)

sys.exit(0)
