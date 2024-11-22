import base64
import logging

from openstack.compute.v2.server import Server
from openstack.connection import Connection
from openstack.identity.v3.project import Project
from openstack.network.v2.network import Network

from .helpers import Config, ProjectCache

LOGGER = logging.getLogger()

class WorkloadGeneratorMachine:

    def __init__(self, conn: Connection, project: Project, machine_name: str,
                 security_group_name_ingress: str,
                 security_group_name_egress: str
                 ):
        self.conn = conn
        self.machine_name = machine_name
        self.root_password = Config.get_admin_vm_password()
        self.floating_ip: str | None = None
        self.internal_ip: str | None = None
        self.security_group_name_ingress = security_group_name_ingress
        self.security_group_name_egress = security_group_name_egress
        self.project = project
        self.obj: Server | None = conn.compute.find_server(self.machine_name)

    @property
    def server_ident(self) -> str:
        if self.obj is None:
            return "DOES NOT EXIST"
        return f"server {self.obj.name}/{self.obj.id}"

    def get_image_id_by_name(self, image_name):
        for image in self.conn.image.images():
            if image.name == image_name:
                return image.id
        return None

    def get_flavor_id_by_name(self, flavor_name):
        for flavor in self.conn.compute.flavors():
            if flavor.name == flavor_name:
                return flavor.id
        return None

    def delete_machine(self):
        LOGGER.warning(f"Deleting machine {self.machine_name} in {ProjectCache.ident_by_id(self.project.id)}")
        self.conn.delete_server(self.obj.id)

    def wait_for_delete(self):
        self.conn.compute.wait_for_delete(self.obj)
        LOGGER.warning(f"Machine {self.machine_name} in {self.obj.project_id} is deleted now")

    def create_or_get_server(self, network: Network):

        if self.obj:
            LOGGER.info(f"Server {self.obj.name}/{self.obj.id} in {ProjectCache.ident_by_id(self.obj.project_id)} already exists")
            return

        # https://docs.openstack.org/openstacksdk/latest/user/resources/compute/v2/server.html#openstack.compute.v2.server.Server
        self.obj = self.conn.compute.create_server(
            name=self.machine_name,
            flavor_id=self.get_flavor_id_by_name(Config.get_vm_flavor()),
            networks=[{"uuid": network.id}],
            admin_password=self.root_password,
            description="automatically created",
            block_device_mapping_v2=[{
                "boot_index": 0,
                "uuid": self.get_image_id_by_name(Config.get_vm_image()),
                "source_type": "image",
                "destination_type": "volume",
                "volume_size": Config.get_vm_volume_size_gb(),
                "delete_on_termination": True,
            }],
            user_data=WorkloadGeneratorMachine._get_user_script(),
            security_groups=[
                {"name": self.security_group_name_ingress},
                {"name": self.security_group_name_egress},
            ],
            key_name=Config.get_admin_vm_ssh_keypair_name(),
        )
        LOGGER.info(f"Created server {self.obj.name}/{self.obj.id} in {ProjectCache.ident_by_id(network.project_id)}")

    @staticmethod
    def _get_user_script() -> str:
        cloud_init_script = "\n".join(Config.get_cloud_init_extra_script())
        cloud_init_script = base64.b64encode(cloud_init_script.encode('utf-8')).decode('utf-8')
        return cloud_init_script

    def update_assigned_ips(self):
        if self.obj.addresses:
            for network_name, addresses in self.obj.addresses.items():
                for address in addresses:
                    if address['OS-EXT-IPS:type'] == 'floating':
                        if self.floating_ip and self.floating_ip != address['addr']:
                            raise RuntimeError("More than one address of type 'floating'")
                        self.floating_ip = address['addr']
                    elif address['OS-EXT-IPS:type'] == 'fixed':
                        if self.internal_ip and self.internal_ip != address['addr']:
                            raise RuntimeError("More than one address of type 'fixed'")
                        self.internal_ip = address['addr']
                    else:
                        raise NotImplementedError(f"{address} not implemented")

    def add_floating_ip(self):
        public_network = self.conn.network.find_network(Config.get_public_network())
        if not public_network:
            LOGGER.error(f"There is no '{public_network}' network")
            return

        self.update_assigned_ips()

        if self.floating_ip:
            LOGGER.info(
                f"Floating ip is already added to {self.obj.name}/{self.obj.id} in domain {self.project.domain_id}")
        else:
            LOGGER.info(f"Add floating ip {self.obj.name}/{self.obj.id} in {ProjectCache.ident_by_id(self.project.id)}")
            self.wait_for_server()
            new_floating_ip = self.conn.network.create_ip(floating_network_id=public_network.id)
            server_port = list(self.conn.network.ports(device_id=self.obj.id))[0]
            self.conn.network.add_ip_to_port(server_port, new_floating_ip)
            self.floating_ip = new_floating_ip.floating_ip_address

    def wait_for_server(self):
        self.conn.compute.wait_for_server(
            self.obj,
            wait=Config.get_wait_for_server_timeout(),
        )

    def start_server(self):
        if self.obj.status != 'ACTIVE':
            self.conn.compute.start_server(self.obj.id)
            LOGGER.info(f"Server '{self.obj.name}' started successfully.")
        else:
            LOGGER.info(f"Server '{self.obj.name}' is already running.")

    def stop_server(self):
        if self.obj.status == 'ACTIVE':
            self.conn.compute.stop_server(self.obj.id)
            LOGGER.info(f"Server '{self.obj.name}' started successfully.")
        else:
            LOGGER.info(f"Server '{self.obj.name}' is already running.")
