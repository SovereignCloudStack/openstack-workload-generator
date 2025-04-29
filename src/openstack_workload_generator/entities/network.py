import logging

from openstack.connection import Connection
from openstack.exceptions import ResourceNotFound
from openstack.identity.v3.project import Project
from openstack.network.v2.network import Network
from openstack.network.v2.router import Router
from openstack.network.v2.security_group import SecurityGroup
from openstack.network.v2.subnet import Subnet

from .helpers import Config, ProjectCache

LOGGER = logging.getLogger()


class WorkloadGeneratorNetwork:

    def __init__(
        self,
        conn: Connection,
        project: Project,
        security_group_name_ingress: str,
        security_group_name_egress: str,
    ):
        self.project: Project = project
        self.conn = conn
        self.network_name = f"localnet-{self.project.name}"
        self.subnet_name = f"localsubnet-{self.project.name}"
        self.router_name = f"localrouter-{self.project.name}"
        self.security_group_name_ingress = security_group_name_ingress
        self.security_group_name_egress = security_group_name_egress
        self.obj_network: Network | None = WorkloadGeneratorNetwork._find_network(
            self.network_name, conn, project
        )
        self.obj_subnet: Subnet | None = WorkloadGeneratorNetwork._find_subnet(
            self.network_name, conn, project
        )
        self.obj_router: Router | None = WorkloadGeneratorNetwork._find_router(
            self.router_name, conn, project
        )
        self.obj_ingress_security_group: SecurityGroup | None = (
            WorkloadGeneratorNetwork._find_security_group(
                self.security_group_name_ingress, conn, project
            )
        )
        self.obj_egress_security_group: SecurityGroup | None = (
            WorkloadGeneratorNetwork._find_security_group(
                self.security_group_name_egress, conn, project
            )
        )

    @staticmethod
    def _find_security_group(
        name, conn: Connection, project: Project
    ) -> SecurityGroup | None:
        security_groups = [
            group
            for group in conn.network.security_groups(
                name=name, project_id=project.id, domain_id=project.domain_id
            )
        ]
        if len(security_groups) > 1:
            raise RuntimeError(
                f"Error fetching security group for project {project.name}/{project.domain_id}"
            )
        elif len(security_groups) == 1:
            return security_groups[0]
        return None

    @staticmethod
    def _find_router(name, conn: Connection, project: Project) -> Router | None:
        routers = [
            router for router in conn.network.routers(name=name, project_id=project.id)
        ]
        if len(routers) == 0:
            return None
        elif len(routers) == 1:
            return routers[0]
        else:
            raise RuntimeError(
                f"More than one router with the name {name} in {project.name}"
            )

    @staticmethod
    def _find_network(name, conn: Connection, project: Project) -> Network | None:
        networks = [
            network
            for network in conn.network.networks(name=name, project_id=project.id)
        ]
        if len(networks) == 0:
            return None
        elif len(networks) == 1:
            return networks[0]
        else:
            raise RuntimeError(
                f"More the one network with the name {name} in {project.name}"
            )

    @staticmethod
    def _find_subnet(name, conn, project) -> Subnet | None:
        subnet = [
            network
            for network in conn.network.subnets(name=name, project_id=project.id)
        ]
        if len(subnet) == 0:
            return None
        elif len(subnet) == 1:
            return subnet[0]
        else:
            raise RuntimeError(
                f"More the one subnet with the name {name} in {project.name}"
            )

    def create_and_get_network_setup(self) -> Network:
        network = self.create_and_get_network()
        subnet = self.create_and_get_subnet()
        self.create_and_get_router(subnet)
        self.create_and_get_ingress_security_group()
        self.create_and_get_egress_security_group()

        return network

    def create_and_get_router(self, subnet: Subnet) -> Router | None:
        public_network = self.conn.network.find_network(Config.get_public_network())
        if not public_network:
            LOGGER.error(
                f"There is no '{Config.get_public_network()}' network, not adding floating ips"
            )
            return None

        if self.obj_router:
            return self.obj_router

        self.obj_router = self.conn.network.create_router(
            name=self.router_name, admin_state_up=True
        )
        if not self.obj_router:
            raise RuntimeError(f"Unable to create Router '{self.router_name}'")

        LOGGER.info(
            f"Router '{self.obj_router.name}' created with ID: {self.obj_router.id}"
        )
        self.conn.network.update_router(
            self.obj_router, external_gateway_info={"network_id": public_network.id}
        )
        LOGGER.info(
            f"Router '{self.obj_router.name}' gateway set to external network: {public_network.name}"
        )
        self.conn.network.add_interface_to_router(self.obj_router, subnet_id=subnet.id)
        LOGGER.info(
            f"Subnet '{subnet.name}' added to router '{self.obj_router.name}' as an interface"
        )

        return self.obj_router

    def create_and_get_network(self) -> Network:
        if self.obj_network:
            return self.obj_network

        mtu_size = Config.get_network_mtu()
        if mtu_size == 0:
            self.obj_network = self.conn.network.create_network(
                name=self.network_name,
                project_id=self.project.id,
            )
        else:
            self.obj_network = self.conn.network.create_network(
                name=self.network_name,
                project_id=self.project.id,
                mtu=mtu_size,
            )
        if not self.obj_network:
            raise RuntimeError(f"Unable to create network {self.network_name}")

        LOGGER.info(
            f"Created network {self.obj_network.name}/{self.obj_network.id} in {self.project.name}/{self.project.id}"
        )
        return self.obj_network

    def create_and_get_subnet(self) -> Subnet:
        if self.obj_subnet:
            return self.obj_subnet

        if not self.obj_network:
            raise RuntimeError("No network object exists")

        self.obj_subnet = self.conn.network.create_subnet(
            network_id=self.obj_network.id,
            project_id=self.project.id,
            name=self.network_name,
            cidr=Config.get_project_ipv4_subnet(),
            ip_version="4",
            enable_dhcp=True,
            dns_nameservers=["8.8.8.8", "9.9.9.9"],
        )

        if not self.obj_subnet:
            raise RuntimeError(f"No subnet created {self.network_name}")

        LOGGER.info(
            f"Created subnet {self.obj_subnet.name}/{self.obj_subnet.id} in {self.project.name}/{self.project.id}"
        )

        return self.obj_subnet

    def delete_network(self):

        if self.obj_router:
            ports = self.conn.network.ports(device_id=self.obj_router.id)
            for port in ports:
                if port.device_owner == "network:router_interface":
                    self.conn.network.remove_interface_from_router(
                        self.obj_router, subnet_id=port.fixed_ips[0]["subnet_id"]
                    )
                    LOGGER.warning(
                        f"Removed interface from subnet: {port.fixed_ips[0]['subnet_id']}"
                    )
            self.conn.network.update_router(self.obj_router, external_gateway_info=None)
            LOGGER.warning(f"Removed gateway from router {self.obj_router.id}")
            self.conn.delete_router(self.obj_router)
            LOGGER.warning(
                f"Deleted router {self.obj_router.id}/{self.obj_router.name}"
            )

        if self.obj_network:
            for subnet_id in self.obj_network.subnet_ids:
                try:
                    subnet_obj = self.conn.get_subnet_by_id(subnet_id)
                    if subnet_obj:
                        for port in self.conn.network.ports():
                            # port_subnet_ids = [x["subnet_id"] for x in port.fixed_ips if port.status == "DOWN"]
                            port_subnet_ids = [x["subnet_id"] for x in port.fixed_ips]
                            if subnet_obj.id in port_subnet_ids:
                                LOGGER.warning(f"Delete port {port.id}")
                                if port.device_owner == "network:router_interface":
                                    self.conn.network.remove_interface_from_router(
                                        port.device_id, port_id=port.id
                                    )
                                    self.conn.network.delete_router(port.device_id)
                                else:
                                    self.conn.network.delete_port(port.id)
                        LOGGER.warning(
                            f"Delete subnet {subnet_obj.name} of {ProjectCache.ident_by_id(self.obj_subnet.project_id)}"
                        )
                        self.conn.network.delete_subnet(
                            subnet_obj, ignore_missing=False
                        )
                except ResourceNotFound:
                    LOGGER.warning(f"Already deleted subnet {subnet_id}")

            self.conn.network.delete_network(self.obj_network, ignore_missing=False)
            LOGGER.warning(
                f"Deleted network {self.obj_network.name} / {self.obj_network.id}"
            )

    def create_and_get_ingress_security_group(self) -> SecurityGroup:
        if self.obj_ingress_security_group:
            return self.obj_ingress_security_group

        LOGGER.info(
            f"Creating ingress security group {self.security_group_name_ingress} for {ProjectCache.ident_by_id(self.project.id)}"
        )
        self.obj_ingress_security_group = self.conn.network.create_security_group(
            name=self.security_group_name_ingress,
            description="Security group to allow SSH access to instances",
        )

        if not self.obj_ingress_security_group:
            raise RuntimeError("No ingress security group was created")

        self.conn.network.create_security_group_rule(
            security_group_id=self.obj_ingress_security_group.id,
            direction="ingress",
            ethertype="IPv4",
            protocol="icmp",
            remote_ip_prefix="0.0.0.0/0",
        )

        self.conn.network.create_security_group_rule(
            security_group_id=self.obj_ingress_security_group.id,
            direction="ingress",
            ethertype="IPv4",
            protocol="tcp",
            port_range_min=22,
            port_range_max=22,
            remote_ip_prefix="0.0.0.0/0",
        )
        return self.obj_ingress_security_group

    def create_and_get_egress_security_group(self) -> SecurityGroup:
        if self.obj_egress_security_group:
            return self.obj_egress_security_group

        LOGGER.info(
            f"Creating egress security group {self.security_group_name_egress} for "
            f"project {self.project.name}/{self.project.domain_id}"
        )
        self.obj_egress_security_group = self.conn.network.create_security_group(
            name=self.security_group_name_egress,
            description="Security group to allow outgoing access",
        )

        if not self.obj_egress_security_group:
            raise RuntimeError("No ingress security group was created")

        self.conn.network.create_security_group_rule(
            security_group_id=self.obj_egress_security_group.id,
            direction="egress",
            ethertype="IPv4",
            protocol="tcp",
            port_range_min=None,
            port_range_max=None,
            remote_ip_prefix="0.0.0.0/0",
        )
        self.conn.network.create_security_group_rule(
            security_group_id=self.obj_egress_security_group.id,
            direction="egress",
            ethertype="IPv4",
            protocol="icmp",
            remote_ip_prefix="0.0.0.0/0",
        )

        return self.obj_egress_security_group
