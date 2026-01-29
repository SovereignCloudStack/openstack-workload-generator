import logging

from openstack.connection import Connection
from . import WorkloadGeneratorProject
from .helpers import Config

LOGGER = logging.getLogger()


class WorkloadGeneratorLoadBalancer:
    def __init__(
        self,
        project: WorkloadGeneratorProject,
    ):
        self.conn: Connection = project.project_conn
        self.project = project
        self.lb = None
        self.listener = None
        self.pool = None
        self.health_monitor = None

    def get_load_balancer_by_name(self, name: str):
        for lb in self.conn.load_balancer.load_balancers(name=name):
            if lb.name == name:
                return lb
        return None

    def get_listener_by_name(self, name: str):
        for listener in self.conn.load_balancer.listeners(name=name):
            if listener.name == name:
                return listener
        return None

    def get_pool_by_name(self, name: str):
        for pool in self.conn.load_balancer.pools(name=name):
            if pool.name == name:
                return pool
        return None

    def get_health_monitor_for_pool(self, pool_id: str):
        for hm in self.conn.load_balancer.health_monitors():
            if hm.pool_id == pool_id:
                return hm
        return None

    def get_and_create_load_balancer(
        self,
    ):
        self.lb = self.get_load_balancer_by_name(Config.get_lb_name())
        if self.lb is not None:
            LOGGER.info(
                f"Load balancer with name {Config.get_lb_name()} already exists"
            )
        else:
            LOGGER.info(f"Create load balancer with name {Config.get_lb_name()}")
            self.lb = self.conn.load_balancer.create_load_balancer(
                name=Config.get_lb_name(),
                vip_subnet_id=self.project.vip_subnet_id,
            )
            self.conn.load_balancer.wait_for_load_balancer(self.lb.id)

        self.listener = self.get_listener_by_name(Config.get_lb_listener_name())
        if self.listener is not None:
            LOGGER.info(
                f"Load balancer listener with name {Config.get_lb_listener_name()} already exists"
            )
        else:
            LOGGER.info(
                f"Create load balancer listener with name {Config.get_lb_listener_name()} on tcp port {Config.get_lb_listener_port()}"
            )
            self.listener = self.conn.load_balancer.create_listener(
                name=Config.get_lb_listener_name(),
                loadbalancer_id=self.lb.id,
                protocol="TCP",
                protocol_port=Config.get_lb_member_tcp_port(),
            )
            self.conn.load_balancer.wait_for_load_balancer(self.lb.id)

        self.pool = self.get_pool_by_name(Config.get_lb_pool_name())
        if self.pool is not None:
            LOGGER.info(
                f"Load balancer pool with name {Config.get_lb_pool_name()} already exists"
            )
        else:
            LOGGER.info(
                f"Create load balancer pool with name {Config.get_lb_pool_name()}"
            )
            self.pool = self.conn.load_balancer.create_pool(
                name=Config.get_lb_pool_name(),
                listener_id=self.listener.id,
                protocol="TCP",
                lb_algorithm="ROUND_ROBIN",
            )
            self.conn.load_balancer.wait_for_load_balancer(self.lb.id)

        self.health_monitor = self.get_health_monitor_for_pool(self.pool.id)
        if self.health_monitor is not None:
            LOGGER.info(
                f"Health monitor for pool with name {Config.get_lb_pool_name()} already exists"
            )
        else:
            self.conn.load_balancer.create_health_monitor(
                self.pool.id, type="TCP", delay=5, timeout=3, max_retries=3
            )

    def add_member_to_load_balancer(self, ip: str):
        if self.lb is None:
            raise RuntimeError("Loadbalancer has not been created of gathered")

        self.conn.load_balancer.create_member(
            self.pool.id,
            address=ip,
            protocol_port=Config.get_lb_member_tcp_port(),
            subnet_id=self.project.vip_subnet_id,
        )

    def add_members_to_load_balancer(self):
        for machine in self.project.workload_machines:
            LOGGER.info(f"Adding member to load balancer with ip {machine.internal_ip}")
            self.add_member_to_load_balancer(machine.internal_ip)
