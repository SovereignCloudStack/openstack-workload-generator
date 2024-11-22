# openstack-workload-generator

The openstack-workload-generator is a tool to generate test workloads on openstack clusters
for the following purposes:

- test new clusters to ensure that basic functionalities are working
- launch a certain workload for performance and reliability tests
- create test setups for openstack tools to test with larger amounts of domains, projects and servers

# General Behavior

The tool uses the Openstack API or the Python Openstack SDK to automatically create and destroy resources in Openstack. 

When creating, the specified resources (e.g. domains, projects, servers, ...) are created if they have not already 
been created. In this way, several creation processes can also be executed in a sequence to create a specific setup 
with certain variants of server properties. The parameters that are used during an execution can be defined 
via a YAML file.

When deleting, the tool proceeds recursively, automatically identifying and deleting all contained resources.

In addition to the servers created, an Ansible inventory directory can also be created, which can be used as the 
basis for later automation.

# Testing Scenarios

## Example usage: A minimal scenario

* 1 domain with
  * one admin user
    * with 1 project
    * assigned roles
    * which then each contain 1 server
          * block storage volume
          * first server has a floating ip
    * one public SSH key
    * a network
    * a subnet
    * a router
    * a security group for ssh ingress access
    * a security group for egress access

### Example output of the creation process

```bash
$ ./openstack_workload_generator --create_domains smoketest1 --create_projects smoketest-project1 --create_machines smoketest-testvm1
2024-11-22 11:16:22 - INFO - helpers.py:69 - The effective configuration from /home/marc/src/github/osba/scs/openstack-workload-generator/src/openstack_workload_generator/entities/../../../profiles/default.yaml : 
>>>
{ 'admin_domain_password': 'yolobanana',
  'admin_vm_password': 'yolobanana',
  'admin_vm_ssh_key': 'ssh-ed25519 '
                      'AAAAC3NzaC1lZDI1NTE5AAAAIACLmNpHitBkZGVbWAFxZjUATNvLjSktAKwokFIQ9Z1k '
                      'schoechlin@osb-alliance.com',
  'admin_vm_ssh_keypair_name': 'my_ssh_public_key',
  'project_ipv4_subnet': '192.168.200.0/24',
  'vm_flavor': 'SCS-1L-1',
  'vm_image': 'Ubuntu 24.04',
  'vm_volume_size_gb': 10}
<<<
2024-11-22 11:16:22 - INFO - __main__.py:80 - Creating 1 domains, with 1 projects, with 1 machines in summary
2024-11-22 11:16:23 - INFO - domain.py:51 - Created domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 11:16:24 - INFO - user.py:22 - Assigned role 'manager' to user 'smoketest1-admin' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 11:16:24 - INFO - user.py:37 - Created user smoketest1-admin / e8c1427ec25547dd9d8eab6a942b0805 with password yolobanana in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 11:16:25 - INFO - project.py:158 - Created project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 11:16:25 - INFO - project.py:136 - Compute quotas for project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd' not changed
2024-11-22 11:16:26 - INFO - project.py:136 - Volume quotas for project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd' not changed
2024-11-22 11:16:26 - INFO - project.py:136 - Network quotas for project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd' not changed
2024-11-22 11:16:26 - INFO - project.py:92 - Assigned manager to e8c1427ec25547dd9d8eab6a942b0805 for project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 11:16:26 - INFO - project.py:92 - Assigned load-balancer_member to e8c1427ec25547dd9d8eab6a942b0805 for project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 11:16:26 - INFO - project.py:92 - Assigned member to e8c1427ec25547dd9d8eab6a942b0805 for project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 11:16:26 - INFO - project.py:49 - Establishing a connection for project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 11:16:29 - INFO - network.py:116 - Created network localnet-smoketest-project1/a5e92142-9842-476e-8bd7-d19b10ddd603 in smoketest-project1/ed5d39e2b5084565991a8c537eae46ae
2024-11-22 11:16:31 - INFO - network.py:133 - Created subnet localnet-smoketest-project1/5d9ebc28-87a2-4622-9882-7629fce8c93d in smoketest-project1/ed5d39e2b5084565991a8c537eae46ae
2024-11-22 11:16:32 - INFO - network.py:97 - Router 'localrouter-smoketest-project1' created with ID: c90fb0af-54c9-42b3-94bc-c9fca9de1a0b
2024-11-22 11:16:35 - INFO - network.py:101 - Router 'localrouter-smoketest-project1' gateway set to external network: public
2024-11-22 11:16:43 - INFO - network.py:103 - Subnet 'localnet-smoketest-project1' added to router 'localrouter-smoketest-project1' as an interface
2024-11-22 11:16:43 - INFO - network.py:180 - Creating ingress security group ingress-ssh-smoketest-project1 for project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 11:16:44 - INFO - network.py:209 - Creating egress security group egress-any-smoketest-project1 for project smoketest-project1/4a6a49520d0848c9a1a8925b64742efd
2024-11-22 11:16:46 - INFO - project.py:241 - Create SSH keypair 'my_ssh_public_key in project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 11:16:46 - INFO - project.py:248 - Closing connection for project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 11:16:46 - INFO - project.py:49 - Establishing a connection for project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 11:16:48 - INFO - helpers.py:32 - config does not contain : ROOT -> cloud_init_extra_script, using >>>#!/bin/bash
echo "HELLO WORLD"; date > READY; whoami >> READY<<<
2024-11-22 11:16:51 - INFO - machine.py:83 - Created server smoketest-testvm1/4196cd5f-b5e8-47cd-a496-6e63d268b506 in project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 11:16:51 - INFO - helpers.py:32 - config does not contain : ROOT -> public_network, using >>>public<<<
2024-11-22 11:16:51 - INFO - machine.py:124 - Add floating ip smoketest-testvm1/4196cd5f-b5e8-47cd-a496-6e63d268b506 in project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 11:16:51 - INFO - helpers.py:32 - config does not contain : ROOT -> wait_for_server_timeout, using >>>300<<<
2024-11-22 11:18:18 - INFO - project.py:248 - Closing connection for project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 11:18:18 - INFO - __main__.py:101 - Execution finished after 1 minutes, item rate 0.6443141142527262/item
```

### Example of the cleanup process
```
./openstack_workload_generator --delete_domains smoketest1
2024-11-22 12:32:16 - WARNING - machine.py:48 - Deleting machine smoketest-testvm1 in project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 12:32:21 - WARNING - machine.py:53 - Machine smoketest-testvm1 in ed5d39e2b5084565991a8c537eae46ae is deleted now
2024-11-22 12:32:25 - WARNING - network.py:146 - Removed interface from subnet: 5d9ebc28-87a2-4622-9882-7629fce8c93d
2024-11-22 12:32:27 - WARNING - network.py:148 - Removed gateway from router c90fb0af-54c9-42b3-94bc-c9fca9de1a0b
2024-11-22 12:32:27 - WARNING - network.py:150 - Deleted router c90fb0af-54c9-42b3-94bc-c9fca9de1a0b/localrouter-smoketest-project1
2024-11-22 12:32:28 - WARNING - network.py:161 - Delete port 3168dba8-0735-47e5-84da-59f9d508b49a
2024-11-22 12:32:29 - WARNING - network.py:167 - Delete subnet localnet-smoketest-project1 of project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 12:32:29 - WARNING - network.py:174 - Deleted network localnet-smoketest-project1 / a5e92142-9842-476e-8bd7-d19b10ddd603
2024-11-22 12:32:29 - WARNING - project.py:183 - Cleanup of project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 12:32:29 - INFO - project.py:49 - Establishing a connection for project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 12:32:35 - WARNING - project.py:190 - Deleting project 'smoketest-project1/ed5d39e2b5084565991a8c537eae46ae' in domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
2024-11-22 12:32:35 - WARNING - project.py:200 - Deleting security group: default (88ceab77-b2c7-4986-8463-a157fbafbcfc)
2024-11-22 12:32:36 - WARNING - user.py:45 - Deleted user: smoketest1-admin / e8c1427ec25547dd9d8eab6a942b0805
2024-11-22 12:32:36 - WARNING - domain.py:70 - Deleted domain 'smoketest1/4a6a49520d0848c9a1a8925b64742efd'
```

## Example usage: A tiny scenario

* 2 domains with
  * one admin user
    * each with 2 projects
    * assigned roles
    * which then each contain 2 servers
          * block storage volume
          * first server has a floating ip
    * one public SSH key
    * a network
    * a subnet
    * a router
    * a security group for ssh ingress access
    * a security group for egress access

```
./openstack_workload_generator \
    --create_domains smoketest{1..2} \
    --create_projects smoketest-project{1..2} \
    --create_machines smoketest-testvm{1..2}
```

