import os
import subprocess
import re
import consul
import registry


def run(nodedn):
    """Run a given container

    This command gets the info needed to launch the container from the registry.
    Information retrieved from the registry:

        node.name
        node.docker_image
        node.docker_opts
        node.disks
        node.networks
        node.tags
    
        bridge = network.bridge
        device = network.device
        address = network.address
        netmask = network.netmask
        gateway = network.gateway

        /service REST endpoint should return:
        service.docker_image
        service.docker_opts
    """
    node = registry.Node(nodedn)

    container_name = '{0}-{1}'.format(node.clustername, node.name)
    container_image = node.docker_image
    docker_opts = node.docker_opts
    service = node.clustername
    tags = node.tags
    disks = node.disks
    networks = node.networks

    opts = generate_docker_opts(docker_opts)
    volumes = generate_volume_opts(disks)

    run('docker run {opts} {volumes} -h {name} --name {name} {image}'.format(
        name=container_name, opts=opts, volumes=volumes, image=container_image))
    add_network_connectivity(container_name, networks)
    register_in_consul(container_name, name=service,
                       address=networks['private']['address'],
                       tags=tags, check='SSH')


def generate_volume_opts(disks):
    volumes = ' '
    for disk in disks:
        if not os.path.exists(disk.origin):
            os.mkdir(disk.origin)
        volumes += '-v {}:{}:{}'.format(disk.origin, disk.destination, disk.mode)


def generate_docker_opts(extra_opts):
    # Do not assign a local IP to the node
    OPTS = '--net="none" '
    OPTS += extra_opts + ' '

    #OPTS += '--privileged '
    #OPTS += '-v /sys/fs/cgroup:/sys/fs/cgroup:ro '
    #OPTS += '-v /dev/log:/dev/log '
    OPTS += '-v /root/.ssh/authorized_keys:/root/.ssh/authorized_keys '
    OPTS += '-d '
    OPTS += '-ti '
    # DOCKER_FIX trick to avoid this issue:
    # https://github.com/docker/docker/issues/14203
    OPTS += "-e DOCKER_FIX='' "


def add_network_connectivity(container_name, networks):
    """Adds the public networks interfaces to the given container"""
    #put('files/bin/pipework', '/tmp/pipework')
    #run('chmod u+x /tmp/pipework')
    for network in networks:
        add_network_interface(container_name, network)


def add_network_interface(container_name, network):
    """Adds one network interface using pipework

    TODO: If not address is specified obtain one from the network service
    """
    device = network.device
    bridge = network.bridge
    address = network.address
    netmask = network.netmask
    gateway = network.gateway

    if re.search(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', gateway):
        subprocess.call(
            'pipework {bridge} -i {device} {name} {ip}/{mask}@{gateway}'
            .format(bridge=bridge, device=device, name=container_name,
                    ip=address,
                    mask=netmask,
                    gateway=gateway))
    else:
        subprocess.call(
            'pipework {bridge} -i {device} {name} {ip}/{mask}'
            .format(bridge=bridge, device=device, name=container_name,
                    ip=address,
                    mask=netmask))

    #subprocess.call('pipework virbrSTORAGE -i eth0 {name} {ip}/{mask}'
    #    .format(name=container_name, ip=networks['storage']['address'],
    #            mask=networks['storage']['netmask']))
    #subprocess.call('pipework virbrPRIVATE -i eth1 {name} {ip}/{mask}@{gateway}'
    #    .format(name=container_name, ip=networks['private']['address'],
    #            mask=networks['private']['netmask'],
    #            gateway=networks['gateway']))


def register_in_consul(container_name, service_name, address, tags=None, check=None):
    """Register the docker container in consul service discovery"""
    sd = consul.Client()
    if check == 'SSH':
        check = {'id': container_name,
                 'name': 'SSH', 'tcp': '{}:{}'.format(address, 22),
                 'Interval': '30s', 'timeout': '4s'}
    sd.register(container_name, service_name, address, tags=tags, check=check)
