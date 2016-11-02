from __future__ import print_function
import logging
import os
import registry
import yaml

logger = logging.getLogger(__name__)

# Do not assign a local IP to the node
# DOCKER_FIX trick to avoid this issue:
# https://github.com/docker/docker/issues/14203
DOCKER_RUN_OPTS = ('--net="none" '
                   '-v /root/.ssh/authorized_keys:/root/.ssh/authorized_keys '
                   '-t -e DOCKER_FIX=""')
# https://docs.docker.com/engine/reference/run/#cpu-period-constraint
CPU_PERIOD = 50000

CONSUL_URL = 'http://127.0.0.1:8500'
KVSTORE_URL = 'http://127.0.0.1:8500/v1/kv'


def load(source):
    if source.endswith('.yaml'):
        load_from_yaml(source)
    else:
        load_from_registry(source)

def load_from_registry(nodedn):
    """Load container configuration from a kvstore configuration registry"""
    return Container(nodedn=nodedn)


def load_from_yaml(yamlfile):
    """Load container configuration from a YAML configuration file"""
    return Container(yamlfile=yamlfile)


class Container(object):
    """Container configuration information"""

    def __init__(self, nodedn=None, yamlfile=None):
        """Create a new container configuration from DN or from a YAML file"""
        if nodedn:
            self.from_registry(nodedn)
        elif yamlfile:
            self.from_json(yamlfile)
        else:
            self.nodename = None
            self.instanceid = None
            self.container_name = None
            self.container_image = None

            self.docker_opts = None
            self.port = None
            self.tags = None
            self.check_ports = None

            self.service = None
            self.disks = None
            self.networks = None
            self.cpu = None
            self.mem = None

    @property
    def container_name(self):
        return '{0}-{1}'.format(self.instanceid, self.nodename)

    def from_registry(self, nodedn):
        """Load container configuration from a kvstore configuration registry"""
        node = registry.Node(nodedn)

        self.nodename = node.name
        self.instanceid = registry.id_from(str(node))
        self.container_image = node.docker_image

        self.docker_opts = node.get('docker_opts', '')
        self.port = node.get('port')
        self.tags = node.get('tags')
        if self.tags:
            self.tags = self.tags.split(',')
        self.check_ports = node.get('check_ports')
        if self.check_ports:
            self.check_ports = self.check_ports.split(',')

        self.service = node.cluster.dnsname
        self.disks = [{'origin': disk.origin, 'destination': disk.destination,
            'mode': disk.get('mode', 'rw')} for disk in node.disks]
        self.networks = [{'device': network.name,
                          'address': network.get('address'),
                          'type': network.type,
                          'networkname': network.networkname,
                          # optional properties for type static
                          'bridge': network.get('bridge'),
                          'netmask': network.get('netmask'),
                          'gateway': network.get('gateway')}
                         for network in node.networks]
        self.cpu = node.cpu
        self.mem = node.mem

        # Properties to set after the container is launched
        self.id = node.id
        self.host = node.host
        self.nspid = node.nspid
        self.status = node.status

    def from_yaml(self, nodeyaml):
        """Load container configuration from a yaml file"""
        node = yaml.load(nodeyaml)

        for prop in ('nodename', 'instanceid', 'container_image', 'docker_opts',
                         'port', 'tags', 'check_ports', 'service', 'disks',
                         'networks', 'cpu', 'mem'):
            setattr(self, prop, node[prop])

        # Properties to set after the container is launched
        self.id = None
        self.host = None
        self.nspid = None
        self.status = None
