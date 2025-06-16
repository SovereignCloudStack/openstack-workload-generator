import logging
import os
import sys

import yaml
from openstack.compute.v2.keypair import Keypair
from openstack.connection import Connection
from openstack.identity.v3.domain import Domain
from openstack.identity.v3.project import Project

from .helpers import ProjectCache, Config
from .machine import WorkloadGeneratorMachine
from .user import WorkloadGeneratorUser
from .network import WorkloadGeneratorNetwork

LOGGER = logging.getLogger()


class WorkloadGeneratorProject:

    def __init__(
        self,
        admin_conn: Connection,
        project_name: str,
        domain: Domain,
        user: WorkloadGeneratorUser,
    ):
        self._admin_conn: Connection = admin_conn
        self._project_conn: Connection | None = None
        self.project_name: str = project_name
        self.security_group_name_ingress: str = f"ingress-ssh-{project_name}"
        self.security_group_name_egress: str = f"egress-any-{project_name}"
        self.domain: Domain = domain
        self.ssh_proxy_jump: str | None = None
        self.user: WorkloadGeneratorUser = user
        self.obj: Project = self._admin_conn.identity.find_project(
            project_name, domain_id=self.domain.id
        )
        if self.obj:
            ProjectCache.add(
                self.obj.id, {"name": self.obj.name, "domain_id": self.domain.id}
            )
        self.workload_network: WorkloadGeneratorNetwork | None = (
            WorkloadGeneratorProject._get_network(
                admin_conn,
                self.obj,
                self.security_group_name_ingress,
                self.security_group_name_egress,
            )
        )
        self.workload_machines: dict[str, WorkloadGeneratorMachine] = (
            WorkloadGeneratorProject._get_machines(
                admin_conn,
                self.obj,
                self.security_group_name_ingress,
                self.security_group_name_egress,
            )
        )
        self.ssh_key: Keypair | None = None

    @property
    def project_conn(self) -> Connection:
        if self._project_conn:
            return self._project_conn

        LOGGER.info(
            f"Establishing a connection for {ProjectCache.ident_by_id(self.obj.id)}"
        )
        self._project_conn = self._admin_conn.connect_as(
            domain_id=self.obj.domain_id,
            project_id=self.obj.id,
            username=self.user.user_name,
            password=self.user.user_password,
        )
        if not self._project_conn:
            raise RuntimeError(
                f"Unable to create a project connection {ProjectCache.ident_by_id(self.obj.id)}"
            )
        return self._project_conn

    @staticmethod
    def _get_network(
        conn: Connection,
        obj: Project,
        security_group_name_ingress: str,
        security_group_name_egress: str,
    ) -> None | WorkloadGeneratorNetwork:
        if not obj:
            return None
        return WorkloadGeneratorNetwork(
            conn, obj, security_group_name_ingress, security_group_name_egress
        )

    @staticmethod
    def _get_machines(
        conn: Connection,
        obj: Project,
        security_group_name_ingress: str,
        security_group_name_egress: str,
    ) -> dict[str, WorkloadGeneratorMachine]:
        result: dict[str, WorkloadGeneratorMachine] = dict()
        if not obj:
            return result

        for server in conn.compute.servers(all_projects=True, project_id=obj.id):
            workload_server = WorkloadGeneratorMachine(
                conn,
                obj,
                server.name,
                security_group_name_ingress,
                security_group_name_egress,
            )
            workload_server.obj = server
            result[workload_server.machine_name] = workload_server
        return result

    def get_machines(self, machines: list[str]) -> list[WorkloadGeneratorMachine]:
        result: list[WorkloadGeneratorMachine] = []
        if self.obj is None:
            return result
        for machine in machines:
            if machine in self.workload_machines:
                result.append(self.workload_machines[machine])
        return result

    def get_role_id_by_name(self, role_name: str, required: bool = True) -> str | None:
        for role in self._admin_conn.identity.roles():
            if role.name == role_name:
                return role.id
        if required:
            raise RuntimeError(f"No such role {role_name}")
        else:
            return None

    def assign_role_to_user_for_project(self, role_name: str, required=True):
        role_id = self.get_role_id_by_name(role_name, required=required)
        if role_id is None and not required:
            LOGGER.info(
                f"No such role {role_name} not assigning it to {ProjectCache.ident_by_id(self.obj.id)}"
            )
            return

        self._admin_conn.identity.assign_project_role_to_user(
            user=self.user.obj.id, project=self.obj.id, role=role_id
        )
        LOGGER.info(
            f"Assigned {role_name} to {self.user.obj.id} for {ProjectCache.ident_by_id(self.obj.id)}"
        )

    def assign_role_to_global_admin_for_project(self, role_name: str):
        user_id = self._admin_conn.session.get_user_id()
        self._admin_conn.identity.assign_project_role_to_user(
            user=user_id, project=self.obj.id, role=self.get_role_id_by_name(role_name)
        )
        LOGGER.info(
            f"Assigned global admin {role_name} to {user_id} for {ProjectCache.ident_by_id(self.obj.id)}"
        )

    def _set_quota(self, quota_category: str):
        if quota_category == "compute_quotas":
            api_area = "compute"
            current_quota = self._admin_conn.compute.get_quota_set(self.obj.id)
        elif quota_category == "block_storage_quotas":
            api_area = "volume"
            current_quota = self._admin_conn.volume.get_quota_set(self.obj.id)
        elif quota_category == "network_quotas":
            api_area = "network"
            current_quota = self._admin_conn.get_network_quotas(self.obj.id)
        else:
            raise RuntimeError(f"Not implemented: {quota_category}")

        LOGGER.debug(f"current quotas for {quota_category} : {current_quota}")

        new_quota = {}
        for key_name in Config.configured_quota_names(quota_category):
            try:
                current_value = getattr(current_quota, key_name)
            except AttributeError:
                LOGGER.error(
                    f"No such {api_area} quota field {key_name} in {current_quota}"
                )
                sys.exit()

            new_value = Config.quota(
                key_name, quota_category, getattr(current_quota, key_name)
            )
            if current_value != new_value:
                LOGGER.info(
                    f"New {api_area} quota for {ProjectCache.ident_by_id(self.obj.id)}"
                    f": {key_name} : {current_value} -> {new_value}"
                )
                new_quota[key_name] = new_value

        if len(new_quota.keys()) > 0:
            set_quota_method = getattr(self._admin_conn, f"set_{api_area}_quotas")
            set_quota_method(self.obj.id, **new_quota)
            LOGGER.info(
                f"Configured {api_area} quotas for {ProjectCache.ident_by_id(self.obj.id)}"
            )
        else:
            LOGGER.info(
                f"{api_area.capitalize()} quotas for {ProjectCache.ident_by_id(self.obj.id)} not changed"
            )

    def adapt_quota(self):
        self._set_quota("compute_quotas")
        self._set_quota("block_storage_quotas")
        self._set_quota("network_quotas")

    def create_and_get_project(self) -> Project:
        if self.obj:
            self.adapt_quota()
            self.workload_network = WorkloadGeneratorNetwork(
                self._admin_conn,
                self.obj,
                self.security_group_name_ingress,
                self.security_group_name_egress,
            )
            self.workload_network.create_and_get_network_setup()
            return self.obj

        self.obj = self._admin_conn.identity.create_project(
            name=self.project_name,
            domain_id=self.domain.id,
            description="Auto generated",
            enabled=True,
        )
        ProjectCache.add(
            self.obj.id, {"name": self.obj.name, "domain_id": self.obj.domain_id}
        )
        LOGGER.info(f"Created {ProjectCache.ident_by_id(self.obj.id)}")
        self.adapt_quota()

        self.assign_role_to_user_for_project("manager")
        self.assign_role_to_user_for_project("load-balancer_member", required=False)
        self.assign_role_to_user_for_project("member")

        self.workload_network = WorkloadGeneratorNetwork(
            self.project_conn,
            self.obj,
            self.security_group_name_ingress,
            self.security_group_name_egress,
        )
        self.workload_network.create_and_get_network_setup()

        return self.obj

    def delete_project(self):

        ##########################################################################################
        # CLEANUP THE PROJECT
        for workload_machine in self.workload_machines.values():
            workload_machine.delete_machine()

        for workload_machine in self.workload_machines.values():
            workload_machine.wait_for_delete()

        self.workload_network.delete_network()

        LOGGER.warning(f"Cleanup of {ProjectCache.ident_by_id(self.obj.id)}")
        self.project_conn.project_cleanup(dry_run=False, wait_timeout=300)
        # This function before this line should do all the steps above, but because of a bug this
        # does not work as expected currently
        # TODO: add bug report reference
        ##########################################################################################

        LOGGER.warning(f"Deleting {ProjectCache.ident_by_id(self.obj.id)}")
        ##########################################################################################
        # DELETE THE PROJECT
        # The following function should also the steps beyond
        # TODO: add bug report reference
        self._admin_conn.identity.delete_project(self.obj.id)

        # Delete the security groups after deleting the project because the "default" security
        # group not seems to be deletable when the project exists
        for sg in self._admin_conn.network.security_groups(project_id=self.obj.id):
            LOGGER.warning(f"Deleting security group: {sg.name} ({sg.id})")
            self._admin_conn.network.delete_security_group(sg.id)
        ##########################################################################################

    def get_and_create_machines(self, machines: list[str], wait_for_machines: bool):
        if "none" in machines:
            LOGGER.warning(
                "Not creating a virtual machine, because 'none' was in the list"
            )
            self.close_connection()
            return

        floating_ips_amount = Config.get_number_of_floating_ips_per_project()

        for nr, machine_name in enumerate(sorted(machines)):
            if machine_name not in self.workload_machines:
                machine = WorkloadGeneratorMachine(
                    self.project_conn,
                    self.obj,
                    machine_name,
                    self.security_group_name_ingress,
                    self.security_group_name_egress,
                )

                if (
                    self.workload_network is None
                    or self.workload_network.obj_network is None
                ):
                    raise RuntimeError("No Workload network object")

                machine.create_or_get_server(
                    self.workload_network.obj_network, wait_for_machines
                )

                if machine.floating_ip:
                    self.ssh_proxy_jump = machine.floating_ip

                self.workload_machines[machine.machine_name] = machine

            if floating_ips_amount > 0:
                self.workload_machines[machine_name].add_floating_ip()
                self.ssh_proxy_jump = self.workload_machines[machine_name].floating_ip
                floating_ips_amount -= 1

        self.close_connection()

    def dump_inventory_hosts(self, directory_location: str):
        for name, workload_machine in self.workload_machines.items():
            if workload_machine.obj is None:
                raise RuntimeError(
                    f"Invalid reference to server for {workload_machine.machine_name}"
                )

            workload_machine.update_assigned_ips()

            if not workload_machine.internal_ip:
                raise RuntimeError(
                    f"Unable to get associated ip address for {workload_machine.machine_name}"
                )

            data: dict[str, str | dict[str, str]] = {
                "openstack": {
                    "machine_id": workload_machine.obj.id,
                    "machine_status": workload_machine.obj.status,
                    "hypervisor": workload_machine.obj[
                        "OS-EXT-SRV-ATTR:hypervisor_hostname"
                    ],
                    "domain": self.domain.name,
                    "project": workload_machine.project.name,
                },
                "hostname": workload_machine.machine_name,
                "ansible_host": workload_machine.floating_ip
                or workload_machine.internal_ip,
                "internal_ip": workload_machine.internal_ip,
            }

            if self.ssh_proxy_jump and not workload_machine.floating_ip:
                data["ansible_ssh_common_args"] = f"-o ProxyJump={self.ssh_proxy_jump} "

            base_dir = f"{directory_location}/{self.domain.name}-{workload_machine.project.name}-{workload_machine.machine_name}"

            filename = f"{base_dir}/data.yml"
            os.makedirs(base_dir, exist_ok=True)
            with open(filename, "w") as file:
                LOGGER.info(
                    f"Creating ansible_inventory_file {filename} for host {data['hostname']}"
                )
                yaml.dump(data, file, default_flow_style=False, explicit_start=True)

    def get_or_create_ssh_key(self):
        self.ssh_key = self.project_conn.compute.find_keypair(
            Config.get_admin_vm_ssh_keypair_name()
        )
        if not self.ssh_key:
            LOGGER.info(
                f"Create SSH keypair '{Config.get_admin_vm_ssh_keypair_name()} in {ProjectCache.ident_by_id(self.obj.id)}"
            )
            self.ssh_key = self.project_conn.compute.create_keypair(
                name=Config.get_admin_vm_ssh_keypair_name(),
                public_key=Config.get_admin_vm_ssh_key(),
            )

    def close_connection(self):
        LOGGER.info(f"Closing connection for {ProjectCache.ident_by_id(self.obj.id)}")
        if self._project_conn:
            self._project_conn.close()
            self._project_conn = None

    def get_clouds_yaml_data(self) -> dict[str, str | bool | dict[str, str]]:
        data: dict[str, bool | str | dict[str, str]] = {
            "auth": {
                "username": self.user.user_name,
                "project_name": self.project_name,
                "auth_url": self.project_conn.session.auth.auth_url,
                "project_domain_name": self.domain.name,
                "user_domain_name": self.domain.name,
                "password": self.user.user_password,
            },
            "verify": Config.get_verify_ssl_certificate(),
            "cacert": self.project_conn.verify,
            "identity_api_version": "3",
        }
        return data
