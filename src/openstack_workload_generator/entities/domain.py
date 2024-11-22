import logging

from .helpers import DomainCache

from openstack.connection import Connection
from openstack.identity.v3.domain import Domain
from .project import WorkloadGeneratorProject

from .user import WorkloadGeneratorTestUser

LOGGER = logging.getLogger()

class WorkloadGeneratorDomain:

    def __init__(self, conn: Connection, domain_name: str):
        self.conn = conn
        self.domain_name = domain_name
        self.obj: Domain = self.conn.identity.find_domain(domain_name)
        if self.obj:
            DomainCache.add(self.obj.id,self.obj.name)
        self.workload_user = WorkloadGeneratorDomain._get_user(conn, domain_name, self.obj)
        self.workload_projects: dict[str, WorkloadGeneratorProject] = WorkloadGeneratorDomain._get_projects(
            conn, self.obj, self.workload_user)

    @staticmethod
    def _get_user(conn: Connection, domain_name: str, obj: Domain):
        if not obj:
            return None
        return WorkloadGeneratorTestUser(conn, f"{domain_name}-admin", obj)

    @staticmethod
    def _get_projects(conn: Connection, domain: Domain | None, user: WorkloadGeneratorTestUser | None) \
            -> dict[str, WorkloadGeneratorProject]:
        if not domain or not user:
            return dict()
        result: dict[str, WorkloadGeneratorProject] = dict()
        for project in conn.identity.projects(domain_id=domain.id):
            result[project.name] = WorkloadGeneratorProject(conn, project.name, domain, user)
        return result

    def create_and_get_domain(self) -> Domain:
        if self.obj:
            return self.obj

        self.obj = self.conn.identity.create_domain(
            name=self.domain_name,
            description="Automated creation",
            enabled=True
        )
        DomainCache.add(self.obj.id, self.obj.name)
        LOGGER.info(f"Created {DomainCache.ident_by_id(self.obj.id)}")

        self.workload_user = WorkloadGeneratorDomain._get_user(self.conn, self.domain_name, self.obj)
        return self.obj

    def disable_domain(self):
        domain = self.conn.identity.update_domain(self.obj.id, enabled=False)
        return domain

    def get_projects(self, projects: list[str]) -> list[WorkloadGeneratorProject]:
        if self.obj is None:
            return []

        for project in projects:
            if project in self.workload_projects:
                yield self.workload_projects[project]

    def delete_domain(self):
        if self.obj is None:
            return

        for project in self.workload_projects.values():
            project.delete_project()

        self.workload_user.delete_user()
        self.disable_domain()
        domain = self.conn.identity.delete_domain(self.obj.id)
        LOGGER.warning(f"Deleted {DomainCache.ident_by_id(self.obj.id)}")
        self.obj = None
        return domain

    def create_and_get_projects(self, create_projects: list[str]):
        self.workload_user.create_and_get_user()

        if "none" in create_projects:
            LOGGER.warning("Not creating a project, because 'none' was in the list")

        for project_name in create_projects:
            if project_name in self.workload_projects:
                continue
            project = WorkloadGeneratorProject(self.conn, project_name, self.obj, self.workload_user)
            project.create_and_get_project()
            project.get_or_create_ssh_key()
            self.workload_projects[project_name] = project
            project.close_connection()

    def create_and_get_machines(self, machines: list[str]):
        for project in self.workload_projects.values():
            project.get_and_create_machines(machines)
