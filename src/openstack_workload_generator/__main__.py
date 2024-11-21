#!/usr/bin/env python3

import argparse
import logging
import sys
import os
import time
from pprint import pformat

import yaml

from helpers import setup_logging, cloud_checker, item_checker
from openstack.connection import Connection
from openstack.config import loader

import landscape

LOGGER = logging.getLogger()

parser = argparse.ArgumentParser(
    prog='Create workloads on openstack installations')

parser.add_argument('--log_level', metavar='loglevel', type=str,
                    default="INFO", help='The loglevel')

parser.add_argument('--os_cloud', type=cloud_checker,
                    default=os.environ.get("OS_CLOUD", "admin"),
                    help='The openstack config to use')

parser.add_argument('--ansible_inventory', type=str, nargs="?",
                    help="Dump the created servers as an ansible inventory to the specified directory")

parser.add_argument('--config', type=str,
                    default="test-default.yaml",
                    help='The config file for environment creation')

exclusive_group = parser.add_mutually_exclusive_group(required=True)

exclusive_group.add_argument('--create_domains', type=item_checker, nargs="+", default=None,
                             help='A list of domains to be created')

exclusive_group.add_argument('--delete_domains', type=item_checker, nargs="+", default=None,
                             help='A list of domains to be deleted')

exclusive_group.add_argument('--show_secrets', '-s', type=str, nargs="+", default=None,
                             help='Show all or a number of secrets')

parser.add_argument('--create_projects', '-p', type=item_checker, nargs="+", default=["test1"],
                    help='A list of projects to be created in the created domains')

parser.add_argument('--create_machines', '-m', type=item_checker, nargs="+", default=["test1"],
                    help='A list of vms to be created in the created domains')

args = parser.parse_args()

if args.os_cloud == "":
    sys.exit(1)

setup_logging(args.log_level)


def establish_connection():
    config = loader.OpenStackConfig()
    cloud_config = config.get_one(args.os_cloud)
    return Connection(config=cloud_config)


def get_effective_config():
    try:
        if not str(args.config).startswith("/"):
            args.config = \
                str(os.path.realpath(os.path.dirname(os.path.realpath(__file__))) + "/../../profiles/default.yaml")

        with open(args.config, 'r') as file:
            landscape.CONFIG = yaml.safe_load(file)
            LOGGER.info("The effective configuration: \n>>>\n" + pformat(landscape.CONFIG, indent=2, compact=False)
                        + "\n<<<")
    except Exception as e:
        LOGGER.error(f"Unable to read configuration: {e}")
        sys.exit(1)


time_start = time.time()

if args.create_domains:
    conn = establish_connection()
    get_effective_config()
    scs_domains: dict[str, landscape.SCSLandscapeTestDomain] = dict()

    count_domains = len(args.create_domains)
    count_projects = count_domains * len(args.create_projects)
    count_hosts = count_projects * len(args.create_machines)
    LOGGER.info(
        f"Creating {count_domains} domains, with {count_projects} projects, with {count_hosts} machines in summary")

    for domain_name in args.create_domains:
        domain = landscape.SCSLandscapeTestDomain(conn, domain_name)
        domain.create_and_get_domain()
        scs_domains[domain_name] = domain

    for scs_domain in scs_domains.values():
        scs_domain.create_and_get_projects(args.create_projects)

    for scs_domain in scs_domains.values():
        for project in scs_domain.scs_projects.values():
            if project.project_name not in args.create_projects:
                continue
            project.get_and_create_machines(args.create_machines)
            if args.ansible_inventory:
                project.dump_inventory_hosts(args.ansible_inventory)

    duration = (time.time() - time_start) / 60
    item_rate = duration / (count_domains + count_projects + count_hosts)
    LOGGER.info(f"Execution finished after {int(duration)} minutes, item rate {item_rate}/item")

if args.delete_domains:
    conn = establish_connection()
    get_effective_config()
    for domain_name in args.delete_domains:
        os = landscape.SCSLandscapeTestDomain(conn, domain_name)
        os.delete_domain()

sys.exit(0)
