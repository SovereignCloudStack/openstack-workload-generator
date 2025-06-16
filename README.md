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
with certain variants of server properties. If provider network is defined the first host in the project gets a floati

The parameters that are used during an execution can be defined 
via a YAML file.

When deleting, the tool proceeds recursively, automatically identifying and deleting all contained resources.

In addition to the servers created, an Ansible inventory directory can also be created, which can be used as the 
basis for later automation.

# Usage

```
$ openstack_workload_generator --help
usage: Create workloads on openstack installations [-h] [--log_level loglevel] [--os_cloud OS_CLOUD] [--ansible_inventory [ANSIBLE_INVENTORY]]
                                                   [--clouds_yaml [CLOUDS_YAML]] [--wait_for_machines] [--generate_clouds_yaml [GENERATE_CLOUDS_YAML]]
                                                   [--config CONFIG] (--create_domains DOMAINNAME [DOMAINNAME ...] | --delete_domains DOMAINNAME [DOMAINNAME ...])
                                                   [--create_projects PROJECTNAME [PROJECTNAME ...] | --delete_projects PROJECTNAME [PROJECTNAME ...]]
                                                   [--create_machines SERVERNAME [SERVERNAME ...] | --delete_machines SERVERNAME [SERVERNAME ...]]

options:
  -h, --help            show this help message and exit
  --log_level loglevel  The loglevel
  --os_cloud OS_CLOUD   The openstack config to use, defaults to the value of the OS_CLOUD environment variable or "admin" if the variable is not set
  --ansible_inventory [ANSIBLE_INVENTORY]
                        Dump the created servers as an ansible inventory to the specified directory, adds a ssh proxy jump for the hosts without a floating ip
  --clouds_yaml [CLOUDS_YAML]
                        Use a specific clouds.yaml file
  --wait_for_machines   Wait for every machine to be created (normally the provisioning only waits for machines which use floating ips)
  --generate_clouds_yaml [GENERATE_CLOUDS_YAML]
                        Generate a openstack clouds.yaml file
  --config CONFIG       The config file for environment creation, define a path to the yaml file or a subpath in the profiles folder of the tool (you can overload
                        the search path by setting the OPENSTACK_WORKLOAD_MANAGER_PROFILES environment variable)
  --create_domains DOMAINNAME [DOMAINNAME ...]
                        A list of domains to be created
  --delete_domains DOMAINNAME [DOMAINNAME ...]
                        A list of domains to be deleted, all child elements are recursively deleted
  --create_projects PROJECTNAME [PROJECTNAME ...]
                        A list of projects to be created in the created domains
  --delete_projects PROJECTNAME [PROJECTNAME ...]
                        A list of projects to be deleted in the created domains, all child elements are recursively deleted
  --create_machines SERVERNAME [SERVERNAME ...]
                        A list of vms to be created in the created domains
  --delete_machines SERVERNAME [SERVERNAME ...]
                        A list of vms to be deleted in the created projects
```

# Configuration

The following cnfigurations:

* `admin_domain_password`
  * the password for the domain users which are created (User `<domain-name>_admin`)
  * If you add "ASK_PASSWORD" as a value, the password will be asked in an interactive way
* `admin_vm_password`:
  * the password for the operating system user (the username depends on the type of image you are using)
  * If you add "ASK_PASSWORD" as a value, the password will be asked in an interactive way
* `vm_flavor`:
  * the name of the flavor used to create virtual machines
  * see `openstack flavor list`
* `vm_image`:
  * the name of the image used to create virtual machines
  * see `openstack image list`
* `vm_volume_size_gb`:
  * the size of the persistent root volume
* `project_ipv4_subnet`:
  * the network cidr of the internal network
* `*_quotas`:
  * the quotas for the created projects
  * execute the tool with `--log_level DEBUG` to see the configurable values
* `public_network`:
  * The name of the public network which is used for floating ips
* `admin_vm_ssh_key`:
  * A multiline string which ssh public keys

```

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
$ ./openstack_workload_generator\
    --create_domains smoketest1\
    --create_projects smoketest-project1\
    --create_machines smoketest-testvm1\
    --ansible_inventory /tmp/stresstest-inventory
2024-11-28 15:51:15 - INFO - helpers.py:76 - Reading /home/marc/src/github/osba/scs/openstack-workload-generator/profiles/default.yaml
2024-11-28 15:51:15 - INFO - helpers.py:99 - The effective configuration from /home/marc/src/github/osba/scs/openstack-workload-generator/profiles/default.yaml : 
>>>
---
admin_domain_password: yolobanana
admin_vm_password: yolobanana
admin_vm_ssh_key: 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIACLmNpHitBkZGVbWAFxZjUATNvLjSktAKwokFIQ9Z1k schoechlin@osb-alliance.com

  ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDyw2z/C+5YugYNXQXbeop0AcOjmWZCvcmci/vOAboO8 schoone@osb-alliance.com

  ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHsMKOr3TEolg4+4hny/zBe4kLcjzkm+vkc932498fVD kipke@osb-alliance.com

  ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILa+/eL5ZM3AWKgm1h4/EFU9hOaSKqaoldHmNeg0qG46 kipke@osb-alliance.com

  ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC2wE2xiuO+i3qmDvu8kCCKX7U7H1diOICbWmR2UrKIxqWgcfWMQsT3WclotJKuVJuKIWyFD6ZNwwLuvC3RxVSqhCiWjqxg3jzJBj7/C1O3IYyLGTUl/x7Cky530lf/aj4wrwt3Ketk/4QNwgget2nCvOy0S2NDCJ3rL6oIUjdJekvRrFf9IbWeX8fqYYCoh1cYJWto1XYPnhMDAB/lqtjN1ssurLSKoJg/bUT7q/KkIvvA/BOR2NMqS0aGx+bKhdkeB22V/t75Ct8ymoCYk9+MTC9i/QX20Fi7835/W7Gl18J8NiO9ebaWyYbsxZ5klWXQa5EiLLBDZ82OR88G+0FjXp1Z3VG6FcpdYpW7sxrT21HEvWOnQACZCdlzwyBJ31id/LjDRhJU6BmZm0Sa9EOJNL8XVOUUzuoa0XL1mIVTsmLpUwqLSfw6Ditb+q4afFi0iYMe3JKOt+JmftvBgeQCjNUsCzk+Ny2j6dZKv2aeF5LOQZGRM3HzG39Gkir3q1zdWmCl4lc3QQBfr5ZcdAp+wQMFSgJAudKffO9kdDVNoyjgih7rD3E+JjJdhY9//WQEEBm2vfEqm7qqEQUAELd0JBCivJmOhUVH0rGbTrnkTBtLR4Au40W5aYaNQJ7+U3hTRrvpycSC1pUU3Wq3OXJd2FRDgKQJljQcpBw4V9j8GQ== Operator

  '
admin_vm_ssh_keypair_name: my_ssh_public_key
cloud_init_extra_script: '#!/bin/bash

  echo "HELLO WORLD"; date > READY; whoami >> READY'
number_of_floating_ips_per_project: '1'
project_ipv4_subnet: 192.168.200.0/24
public_network: public
vm_flavor: SCS-1L-1
vm_image: Ubuntu 24.04
vm_volume_size_gb: 10
wait_for_server_timeout: '300'

<<<
2024-11-28 15:51:15 - INFO - domain.py:52 - Created domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:51:16 - INFO - user.py:23 - Assigned role 'manager' to user 'smoketest1-admin' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:51:16 - INFO - user.py:39 - Created user smoketest1-admin / 35caa86cc7ed467380e9755f12fd9115 with password yolobanana in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:51:17 - INFO - project.py:172 - Created project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:51:17 - INFO - project.py:149 - Compute quotas for project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e' not changed
2024-11-28 15:51:18 - INFO - project.py:149 - Volume quotas for project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e' not changed
2024-11-28 15:51:18 - INFO - project.py:149 - Network quotas for project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e' not changed
2024-11-28 15:51:18 - INFO - project.py:105 - Assigned manager to 35caa86cc7ed467380e9755f12fd9115 for project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:51:18 - INFO - project.py:105 - Assigned load-balancer_member to 35caa86cc7ed467380e9755f12fd9115 for project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:51:18 - INFO - project.py:105 - Assigned member to 35caa86cc7ed467380e9755f12fd9115 for project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:51:18 - INFO - project.py:51 - Establishing a connection for project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:51:21 - INFO - network.py:123 - Created network localnet-smoketest-project1/0676385f-bafd-48b5-bc33-e1162db46601 in smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff
2024-11-28 15:51:23 - INFO - network.py:147 - Created subnet localnet-smoketest-project1/72ffa9ac-2110-4d13-97dc-d80cb0a4cb4c in smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff
2024-11-28 15:51:24 - INFO - network.py:101 - Router 'localrouter-smoketest-project1' created with ID: f5394861-277b-4670-a93f-a8fc11bdd9bc
2024-11-28 15:51:27 - INFO - network.py:105 - Router 'localrouter-smoketest-project1' gateway set to external network: public
2024-11-28 15:51:31 - INFO - network.py:107 - Subnet 'localnet-smoketest-project1' added to router 'localrouter-smoketest-project1' as an interface
2024-11-28 15:51:31 - INFO - network.py:194 - Creating ingress security group ingress-ssh-smoketest-project1 for project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:51:32 - INFO - network.py:227 - Creating egress security group egress-any-smoketest-project1 for project smoketest-project1/c863af289ea04c35b9dabdd2f94d424e
2024-11-28 15:51:34 - INFO - project.py:280 - Create SSH keypair 'my_ssh_public_key in project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:51:34 - INFO - project.py:288 - Closing connection for project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:51:34 - INFO - project.py:51 - Establishing a connection for project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:51:39 - INFO - machine.py:88 - Created server smoketest-testvm1/0d688d7a-79b0-4206-9d99-fc191b425110 in project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:51:39 - INFO - machine.py:125 - Add floating ip smoketest-testvm1/0d688d7a-79b0-4206-9d99-fc191b425110 in project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:53:06 - INFO - project.py:288 - Closing connection for project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:53:06 - INFO - project.py:274 - Creating ansible_inventory_file /tmp/stresstest-inventory/smoketest1-smoketest-project1-smoketest-testvm1/data.yml for host smoketest-testvm1

$ cat /tmp/stresstest-inventory/smoketest1-smoketest-project1-smoketest-testvm1/data.yml
---
ansible_host: 10.80.2.35
hostname: smoketest-testvm1
internal_ip: 192.168.200.222
openstack:
  domain: smoketest1
  hypervisor: null
  machine_id: 0d688d7a-79b0-4206-9d99-fc191b425110
  machine_status: ACTIVE
  project: smoketest-project1

```

### Example of the cleanup process

```bash
$ ./openstack_workload_generator --delete_domains smoketest1  
2024-11-28 15:55:46 - INFO - helpers.py:76 - Reading /home/marc/src/github/osba/scs/openstack-workload-generator/profiles/default.yaml
2024-11-28 15:55:46 - INFO - helpers.py:99 - The effective configuration from /home/marc/src/github/osba/scs/openstack-workload-generator/profiles/default.yaml : 
>>>
---
admin_domain_password: yolobanana
admin_vm_password: yolobanana
admin_vm_ssh_key: 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIACLmNpHitBkZGVbWAFxZjUATNvLjSktAKwokFIQ9Z1k schoechlin@osb-alliance.com
  ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDyw2z/C+5YugYNXQXbeop0AcOjmWZCvcmci/vOAboO8 schoone@osb-alliance.com
  ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHsMKOr3TEolg4+4hny/zBe4kLcjzkm+vkc932498fVD kipke@osb-alliance.com
  ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILa+/eL5ZM3AWKgm1h4/EFU9hOaSKqaoldHmNeg0qG46 kipke@osb-alliance.com
  ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC2wE2xiuO+i3qmDvu8kCCKX7U7H1diOICbWmR2UrKIxqWgcfWMQsT3WclotJKuVJuKIWyFD6ZNwwLuvC3RxVSqhCiWjqxg3jzJBj7/C1O3IYyLGTUl/x7Cky530lf/aj4wrwt3Ketk/4QNwgget2nCvOy0S2NDCJ3rL6oIUjdJekvRrFf9IbWeX8fqYYCoh1cYJWto1XYPnhMDAB/lqtjN1ssurLSKoJg/bUT7q/KkIvvA/BOR2NMqS0aGx+bKhdkeB22V/t75Ct8ymoCYk9+MTC9i/QX20Fi7835/W7Gl18J8NiO9ebaWyYbsxZ5klWXQa5EiLLBDZ82OR88G+0FjXp1Z3VG6FcpdYpW7sxrT21HEvWOnQACZCdlzwyBJ31id/LjDRhJU6BmZm0Sa9EOJNL8XVOUUzuoa0XL1mIVTsmLpUwqLSfw6Ditb+q4afFi0iYMe3JKOt+JmftvBgeQCjNUsCzk+Ny2j6dZKv2aeF5LOQZGRM3HzG39Gkir3q1zdWmCl4lc3QQBfr5ZcdAp+wQMFSgJAudKffO9kdDVNoyjgih7rD3E+JjJdhY9//WQEEBm2vfEqm7qqEQUAELd0JBCivJmOhUVH0rGbTrnkTBtLR4Au40W5aYaNQJ7+U3hTRrvpycSC1pUU3Wq3OXJd2FRDgKQJljQcpBw4V9j8GQ== Operator
  '
admin_vm_ssh_keypair_name: my_ssh_public_key
cloud_init_extra_script: '#!/bin/bash
  echo "HELLO WORLD"; date > READY; whoami >> READY'
number_of_floating_ips_per_project: '1'
project_ipv4_subnet: 192.168.200.0/24
public_network: public
vm_flavor: SCS-1L-1
vm_image: Ubuntu 24.04
vm_volume_size_gb: 10
wait_for_server_timeout: '300'

<<<
2024-11-28 15:55:49 - WARNING - machine.py:49 - Deleting machine smoketest-testvm1 in project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:55:53 - WARNING - machine.py:54 - Machine smoketest-testvm1 in 7581b3ee38474353a9bcf09a2e2d6cff is deleted now
2024-11-28 15:55:58 - WARNING - network.py:160 - Removed interface from subnet: 72ffa9ac-2110-4d13-97dc-d80cb0a4cb4c
2024-11-28 15:56:00 - WARNING - network.py:162 - Removed gateway from router f5394861-277b-4670-a93f-a8fc11bdd9bc
2024-11-28 15:56:00 - WARNING - network.py:164 - Deleted router f5394861-277b-4670-a93f-a8fc11bdd9bc/localrouter-smoketest-project1
2024-11-28 15:56:01 - WARNING - network.py:175 - Delete port 501ec7d8-63c5-4f60-9eac-bfe0ea844b36
2024-11-28 15:56:01 - WARNING - network.py:181 - Delete subnet localnet-smoketest-project1 of project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:56:02 - WARNING - network.py:188 - Deleted network localnet-smoketest-project1 / 0676385f-bafd-48b5-bc33-e1162db46601
2024-11-28 15:56:02 - WARNING - project.py:197 - Cleanup of project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:56:02 - INFO - project.py:51 - Establishing a connection for project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:56:08 - WARNING - project.py:204 - Deleting project 'smoketest-project1/7581b3ee38474353a9bcf09a2e2d6cff' in domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'
2024-11-28 15:56:08 - WARNING - project.py:214 - Deleting security group: default (06bda9d7-a678-475f-bc30-bf005c53b437)
2024-11-28 15:56:10 - WARNING - user.py:47 - Deleted user: smoketest1-admin / 35caa86cc7ed467380e9755f12fd9115
2024-11-28 15:56:10 - WARNING - domain.py:82 - Deleted domain 'smoketest1/c863af289ea04c35b9dabdd2f94d424e'

```

## Example usage: A tiny scenario

* 2 domains with
  * one admin user
    * each with 2 projects
    * assigned roles
    * which then each contain 2 servers
      * block storage volume
      * first server has a floating ip
    * public SSH key
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


## Example usage: A huge stresstest scenario

### Scenario Details

* 10 domains, with 6 projects each , with 9 machines each.
  * 9 domains
  * 45 projects
  * 540 virtual machines
* 4GB RAM per machine, 2.1TB RAM in total
* 10GB Disk per machine, 5.5TB DISK in total
* [The configuration profile](profiles/stresstest.yaml)
  * Downloads a [shellscript](http://10.10.23.254:28080/stresstest.sh) from a server which is reachable by all virtual machines
  * Executes the script in a screen session
  * Prevents to execute multiple scripts in parallel by checking if there is already a screen named "execute"

### Testing procedure

1. Move stresstestfile out of the way at the central server
  ```
  ssh scs-manager1
  mv /srv/www/stresstest.sh /srv/www/stresstest.sh.disabled
  ```
2. Test the scenario creation
  ```
  ./openstack_workload_generator \
    --config stresstest.yaml \
    --create_domains stresstest1 \
    --create_projects stresstest-project1 \
    --create_machines stresstestvm1
  ```
3. Create the full scenario
  ```
  ./openstack_workload_generator \
    --config stresstest.yaml \
    --create_domains stresstest{1..10} \
    --create_projects stresstest-project{1..6} \
    --create_machines stresstestvm{1..9} \
    --ansible_inventory /tmp/stresstest-inventory
  ```
4. Check the created scenario
  ```
  openstack domain list
  openstack project list --long
  openstack server list --all-projects --long
  ```
5. Activate the stresstestfile
  ```
  ssh scs-manager1
  cat <<EOF
  #!/bin/bash
  stress-ng --vm 8 --vm-bytes 80% -t 1h
  EOF
  mv /srv/www/stresstest.sh.disabled /srv/www/stresstest.sh
  ```
6. Purge the scenario
  ```
  ./openstack_workload_generator --delete_domains stresstest{1..10}
  ```

