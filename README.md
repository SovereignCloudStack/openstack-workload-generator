# openstack-workload-generator

The openstack-workload-generator is a tool to generate test workloads on openstack clusters
for the following purposes:

- test new clusters to ensure that basic functionalities are working
- launch a certain workload for performance and reliability tests
- create test setups for openstack tools to test with larger amounts of domains, projects and servers

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
