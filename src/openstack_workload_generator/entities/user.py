import logging

from openstack.connection import Connection
from openstack.identity.v3.domain import Domain
from openstack.identity.v3.user import User

from .helpers import Config, DomainCache

LOGGER = logging.getLogger()


class WorkloadGeneratorUser:

    def __init__(self, conn: Connection, user_name: str, domain: Domain):
        self.conn = conn
        self.user_name = user_name
        self.user_password = Config.get_admin_domain_password()
        self.domain: Domain = domain
        self.obj = self.conn.identity.find_user(
            user_name, query={"domain_id": self.domain.id}
        )

    def assign_role_to_user(self, role_name: str):
        self.conn.identity.assign_project_role_to_user(
            self.obj.id, self.domain.id, self.get_role_id_by_name(role_name)
        )
        LOGGER.info(
            f"Assigned role '{role_name}' to user '{self.obj.name}' in {DomainCache.ident_by_id(self.domain.id)}"
        )

    def create_and_get_user(self) -> User:

        if self.obj:
            LOGGER.info(
                f"User {self.user_name} already exists in {DomainCache.ident_by_id(self.domain.id)}"
            )
            return self.obj

        self.obj = self.conn.identity.create_user(
            name=self.user_name,
            password=self.user_password,
            domain_id=self.domain.id,
            enabled=True,
        )
        self.assign_role_to_user("manager")
        LOGGER.info(
            f"Created user {self.obj.name} / {self.obj.id} with password {self.obj.password} in {DomainCache.ident_by_id(self.domain.id)}"
        )
        return self.obj

    def delete_user(self):
        if not self.obj:
            return
        self.conn.identity.delete_user(self.obj.id)
        LOGGER.warning(f"Deleted user: {self.obj.name} / {self.obj.id}")
        self.obj = None

    def get_role_id_by_name(self, role_name) -> str:
        for role in self.conn.identity.roles():
            if role.name == role_name:
                return role.id
        raise RuntimeError(f"No such role {role_name}")
