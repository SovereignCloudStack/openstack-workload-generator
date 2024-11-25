#!/usr/bin/env python3

import sys
import os
import argparse
import logging
import time

from openstack.connection import Connection
from openstack.config import loader

# $ make type-check
# source venv/bin/activate && python3 -m mypy --no-color-output --pretty src
# src/openstack_workload_generator/__main__.py:12: error: Cannot find implementation or library
# stub for module named "entities"  [import-not-found]
#    from entities import WorkloadGeneratorDomain
#    ^
# src/openstack_workload_generator/__main__.py:13: error: Cannot find implementation or library stub for module
# named "entities.helpers"  [import-not-found]
#    from entities.helpers import setup_logging, cloud_checker, item_checker, Config
#    ^
# src/openstack_workload_generator/__main__.py:13: note: See
# https://mypy.readthedocs.io/en/stable/running_mypy.html#missing-imports
# Found 2 errors in 1 file (checked 9 source files)
# make: *** [Makefile:25: type-check] Error 1

from entities import WorkloadGeneratorDomain  # type: ignore[import-not-found]
from entities.helpers import setup_logging, cloud_checker, item_checker, Config  # type: ignore[import-not-found]

LOGGER = logging.getLogger()

parser = argparse.ArgumentParser(
    prog='Create workloads on openstack installations')

parser.add_argument('--log_level', metavar='loglevel', type=str,
                    default="INFO", help='The loglevel')

parser.add_argument('--os_cloud', type=cloud_checker,
                    default=os.environ.get("OS_CLOUD", "admin"),
                    help='The openstack config to use, defaults to the value of the OS_CLOUD '
                         'environment variable or "admin" if the variable is not set')

parser.add_argument('--ansible_inventory', type=str, nargs="?",
                    help="Dump the created servers as an ansible inventory to the specified directory, "
                         "adds a ssh proxy jump for the hosts without a floating ip")

parser.add_argument('--config', type=str,
                    default="default.yaml",
                    help='The config file for environment creation, define a path to the'
                         ' yaml file or a subpath in the profiles folder')

exclusive_group_domain = parser.add_mutually_exclusive_group(required=True)

exclusive_group_domain.add_argument('--create_domains', type=item_checker, nargs="+", default=None,
                                    metavar="DOMAINNAME",
                                    help='A list of domains to be created')

exclusive_group_domain.add_argument('--delete_domains', type=item_checker, nargs="+", default=None,
                                    metavar="DOMAINNAME",
                                    help='A list of domains to be deleted, all child elements are recursively deleted')

exclusive_group_project = parser.add_mutually_exclusive_group(required=False)

exclusive_group_project.add_argument('--create_projects', type=item_checker, nargs="+", default=None,
                                     metavar="PROJECTNAME",
                                     help='A list of projects to be created in the created domains')

exclusive_group_project.add_argument('--delete_projects', type=item_checker, nargs="+", default=None,
                                     metavar="PROJECTNAME",
                                     help='A list of projects to be deleted in the created '
                                          'domains, all child elements are recursively deleted')

exclusive_group_machines = parser.add_mutually_exclusive_group(required=False)
exclusive_group_machines.add_argument('--create_machines', type=item_checker, nargs="+", default=None,
                                      metavar="SERVERNAME",
                                      help='A list of vms to be created in the created domains')

exclusive_group_machines.add_argument('--delete_machines', type=item_checker, nargs="+", default=None,
                                      metavar="SERVERNAME",
                                      help='A list of vms to be deleted in the created projects')

args = parser.parse_args()

if args.os_cloud == "":
    sys.exit(1)

setup_logging(args.log_level)


def establish_connection():
    config = loader.OpenStackConfig()
    cloud_config = config.get_one(args.os_cloud)
    return Connection(config=cloud_config)


time_start = time.time()

Config.load_config(args.config)
Config.show_effective_config()

if args.create_domains:
    conn = establish_connection()
    workload_domains: dict[str, WorkloadGeneratorDomain] = dict()
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
                    workload_project.get_and_create_machines(args.create_machines)
                    if args.ansible_inventory:
                        workload_project.dump_inventory_hosts(args.ansible_inventory)
                elif args.delete_machines:
                    for machine_obj in workload_project.get_machines(args.delete_machines):
                        machine_obj.delete_machine()
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
