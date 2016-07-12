Credits
-------

Uses the wonderful pipework script of jpetazzo: https://github.com/jpetazzo/pipework

Installation
------------
::
    cd docker-executor
    virtualenv venv
    . venv/bin/activate
    pip install --editable .

Requires
--------
docker-executor reads the configuration from a K/V store.

Cluster object:

- dnsname: name to register the cluster in the service discovery's DNS

Node object:

- name: hostname of the docker container
- docker_image: URL of the docker image to use
- docker_opts: specific docker run options to use
- cpu: number of cores that can be used by this container
- mem: memory in MB that can be used by this container
- disks: Disk object list (see below)
- networks: Network object list (see below)
- port: main service port used for service discovery, e.g. 22
- tags: list of tags for service discovery separated by comma, eg. 'v1,testing,hdp'
- check_ports: list of ports to check that the container is alive, eg. '22,5000,8080'
- id: it will be set to the docker id of the running container
- host: it will be set docker engine where the container is running
- status: it will be set to the current status of the node

Network object (registry.Network object):

- type: 'static', 'dynamic'
- networkname: name of the network to use form the networks service
- address: for dynamic allocation use '_', 'dynamic' or ''

The name of the network device (eg. eth0) is taken automatically from the name of the
  directory in consul: eg. node/networks/eth0/address -> eth0

Volume object (registry.Disk object):

- origin
- destination
- mode (OPTIONAL): default 'rw'

Deployment
----------
Using clush and pip:

::
    python setup.py sdist upload -r pypi
    clush -bw @bigdata pip install --upgrade --no-cache-dir docker-executor
