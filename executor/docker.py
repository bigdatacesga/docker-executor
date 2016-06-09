from __future__ import print_function
import os
import registry
from . import utils
from . import networks
from . import servicediscovery
import Queue
import threading
from time import sleep
import socket

# Do not assign a local IP to the node
# DOCKER_FIX trick to avoid this issue:
# https://github.com/docker/docker/issues/14203
DOCKER_RUN_OPTS = ('--net="none" '
                   '-v /root/.ssh/authorized_keys:/root/.ssh/authorized_keys '
                   '-t -e DOCKER_FIX=""')


class Volume(object):
    """Represents a Docker Volume"""
    def __init__(self, origin=None, destination=None, mode=None):
        self.origin = origin
        self.destination = destination
        self.mode = mode


class Network(object):
    """Represents a Docker Network Device"""
    def __init__(self, device=None, address=None,
                 bridge=None, netmask=None, gateway=None,
                 networkname=None, network_type=None):
        self.device = device
        self.address = address
        self.bridge = bridge
        self.netmask = netmask
        self.gateway = gateway
        self.networkname = networkname
        self.type = network_type


def run(nodedn, daemon=False):
    """Run a given container

    This command gets the info needed to launch the container from the registry.
    Information retrieved from the registry:

    Node object:

    - name: hostname of the docker container
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
    - type: 'static', 'dynamic'

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
    utils.run(docker_pull)

    docker_run = 'docker run {opts} {volumes} -h {hostname} --name {name} {image}'.format(
        hostname=nodename, name=container_name, opts=opts,
        volumes=volumes, image=container_image)
    #utils.run(docker_run)
    #q = Queue.Queue()
    #t = threading.Thread(target=utils.run, args=(docker_run, q))
    t = threading.Thread(target=utils.run, args=(docker_run,))
    t.daemon = True
    t.start()

    # Allow container to start
    # TODO: Communicate with the thread and read info from the queue
    sleep(2)
    networks.configure(container_name, networks, clustername)
    servicediscovery.register(container_name, service, networks[0].address,
                              tags=tags, port=port, check_ports=check_ports)

    node.id = container_name
    node.host = socket.gethostname()
    node.status = 'running'

    t.join()
    #output = q.get()
    #return output


def stop(nodedn):
    """Stop a running container"""
    # TODO: Move the properties to a config module
    node = registry.Node(nodedn)
    name = node.id
    clustername = node.clustername
    docker_stop = 'docker stop {}'.format(name)
    utils.run(docker_stop)
    node.status = 'stopped'
    networks.release(name, networks, clustername)
    servicediscovery.deregister(name)


def destroy(nodedn):
    """Destroy a running container, ie. stop and remove the local image"""
    stop(nodedn)
    # TODO: Move the properties to a config module
    node = registry.Node(nodedn)
    name = node.id
    docker_rm = 'docker rm {}'.format(name)
    utils.run(docker_rm)
    node.host = '_'
    node.status = 'destroyed'


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
