from __future__ import print_function
import os
import subprocess
import re
import consul
import registry
from . import networks
import Queue
import threading
from time import sleep
import socket

# Do not assign a local IP to the node
# DOCKER_FIX trick to avoid this issue:
# https://github.com/docker/docker/issues/14203
DOCKER_RUN_OPTS = ('--net="none" '
                   '-v /root/.ssh/authorized_keys:/root/.ssh/authorized_keys '
                  # '-ti -e DOCKER_FIX=""') # 0.1.9
                   '-t -e DOCKER_FIX=""') # 0.1.10 0.1.12
                  # '-i -e DOCKER_FIX=""') # 0.1.11


class Volume(object):
    """Represents a Docker Volume"""
    def __init__(self, origin=None, destination=None, mode=None):
        self.origin = origin
        self.destination = destination
        self.mode = mode


class Network(object):
    """Represents a Docker Network Device"""
    def __init__(self, device=None, address=None,
                 bridge=None, netmask=None, gateway=None):
        self.device = device
        self.address = address
        self.bridge = bridge
        self.netmask = netmask
        self.gateway = gateway


def run(nodedn, daemon=False):
    """Run a given container

    This command gets the info needed to launch the container from the registry.
    Information retrieved from the registry:

    Node object:

    - name: name to give to the docker container
    - clustername: name of the cluster/service to which this docker belongs
    - docker_image
    - docker_opts
    - id: docker id
    - disks: Disk object list (see below)
    - networks: Network object list (see below)
    - tags: ('master', 'yarn')
    - status: pending, running, failed, stopped
    - host: docker engine where the container is running
    - port: main service port, e.g. 22
    - check_ports: list of ports to check that the container is alive

    Network object (registry.Network object):

    - device
    - address: for dynamic allocation use '_', 'dynamic' or ''
    - bridge
    - netmask
    - gateway
    - networkname: name of the network

    Volume object (registry.Disk object):

    - origin
    - destination
    - mode
    """
    # TODO: Move the properties to a config module so this part is independent from
    # what you use to retrieve the information
    node = registry.Node(nodedn)

    nodename = node.name
    clustername = node.clustername
    container_name = '{0}-{1}'.format(node.clustername, node.name)
    container_image = node.docker_image
    docker_opts = node.docker_opts
    service = node.clustername
    tags = node.tags
    disks = node.disks
    networks = node.networks
    check_ports = node.check_ports
    port = node.port

    opts = generate_docker_opts(docker_opts, daemon)
    volumes = generate_volume_opts(disks)

    docker_pull = 'docker pull {image}'.format(image=container_image)
    _cmd(docker_pull)

    docker_run = 'docker run {opts} {volumes} -h {name} --name {name} {image}'.format(
        name=container_name, opts=opts, volumes=volumes, image=container_image)
    #_cmd(docker_run)
    #q = Queue.Queue()
    #t = threading.Thread(target=_cmd, args=(docker_run, q))
    t = threading.Thread(target=_cmd, args=(docker_run,))
    t.daemon = True
    t.start()

    # Allow container to start
    # TODO: Communicate with the thread and read info from the queue
    sleep(2)
    add_network_connectivity(container_name, networks, clustername)
    register_in_consul(container_name, service, networks[0].address,
                       tags=tags, port=port, check_ports=check_ports)

    node.id = container_name
    node.host = socket.gethostname()
    node.status = 'running'

    t.join()
    #output = q.get()
    #return output


def generate_volume_opts(volumes):
    volume_opts = ''
    for volume in volumes:
        if not os.path.exists(volume.origin):
            os.mkdir(volume.origin)
        volume_opts += '-v {}:{}:{} '.format(volume.origin, volume.destination, volume.mode)
    return volume_opts


def generate_docker_opts(extra_opts, daemon=False):
    opts = DOCKER_RUN_OPTS
    opts += ' ' + extra_opts + ' '
    if daemon:
        opts += '-d '
    return opts


def add_network_connectivity(container_name, networks, clustername=''):
    """Adds the public networks interfaces to the given container"""
    for network in networks:
        add_network_interface(container_name, network, clustername)


def add_network_interface(container_name, network, clustername=''):
    """Adds one network interface using pipework"""
    device = network.device
    bridge = network.bridge
    address = network.address
    netmask = network.netmask
    gateway = network.gateway
    networkname = network.networkname

    if not address or address == '_' or address == 'dynamic':
        address = networks.allocate(networkname, container_name, clustername)
        # Update registry info
        network.address = address

    if gateway and re.search(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', gateway):
        return _cmd(
            'pipework {bridge} -i {device} {name} {ip}/{mask}@{gateway}'
            .format(bridge=bridge, device=device, name=container_name,
                    ip=address,
                    mask=netmask,
                    gateway=gateway))
    else:
        return _cmd(
            'pipework {bridge} -i {device} {name} {ip}/{mask}'
            .format(bridge=bridge, device=device, name=container_name,
                    ip=address,
                    mask=netmask))


def register_in_consul(container_name, service_name, address,
                       tags=None, port=None, check_ports=None):
    """Register the docker container in consul service discovery"""
    sd = consul.Client()
    if check_ports:
        checks = generate_checks(container_name, address, check_ports)
    print("==> Registering the container in Consul Service Discovery")
    #FIXME: It seems the API only accepts one check at service registration time
    # To register multiple services register each one using /v1/agent/check/register
    sd.register(container_name, service_name, address,
                tags=tags, port=port, check=checks['checks'][0])
    #sd.register(container_name, service_name, address,
    #            tags=tags, port=port, check=checks)


def generate_checks(container, address, check_ports):
    """Generates the check dictionary to pass to consul of the form {'checks': []}"""
    checks = {}
    checks['checks'] = []
    for p in check_ports:
        checks['checks'].append(
            {'id': '{}-port{}'.format(container, p),
             'name': 'Check TCP port {}'.format(p),
             'tcp': '{}:{}'.format(address, p),
             'Interval': '30s',
             'timeout': '4s'})
    return checks


def _cmd(cmd):
    """Execute cmd on the shell"""
    print('==> {}'.format(cmd))
    return subprocess.call(cmd, shell=True)
