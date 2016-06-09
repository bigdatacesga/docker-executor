"""Network Address Allocation Utils"""
import re
import requests
from . import utils


BASE = 'http://networks.service.int.cesga.es:5000/resources/networks/v1/networks'


def configure(container_name, networks, clustername=''):
    """Configure the networks interfaces to the given container"""
    for network in networks:
        configure_interface(container_name, network, clustername)


def configure_interface(container_name, network, clustername=''):
    """Adds one network interface using pipework"""
    device = network.device
    bridge = network.bridge
    address = network.address
    netmask = network.netmask
    gateway = network.gateway
    networkname = network.networkname

    if not address or address == '_' or address == 'dynamic':
        address = allocate(networkname, container_name, clustername)
        # Update registry info
        network.address = address

    if gateway and re.search(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', gateway):
        return utils.run(
            'pipework {bridge} -i {device} {name} {ip}/{mask}@{gateway}'
            .format(bridge=bridge, device=device, name=container_name,
                    ip=address,
                    mask=netmask,
                    gateway=gateway))
    else:
        return utils.run(
            'pipework {bridge} -i {device} {name} {ip}/{mask}'
            .format(bridge=bridge, device=device, name=container_name,
                    ip=address,
                    mask=netmask))


def release(networks):
    """Release the network addresses used by a given container"""
    for network in networks:
        release_interface(network)


def release_interface(network):
    """Release the network address of a given interface"""
    if network.type == 'dynamic':
        deallocate(network.networkname, network.address)
        network.address = '_'


def allocate(network, node, cluster='_'):
    """Allocate a new network address to a given node that can belong to a cluster"""
    r = requests.get('{}/{}/addresses?free'.format(BASE, network))
    data = r.json()
    free = data['addresses']
    address = sorted(free, reverse=True).pop()
    assigned = {'status': 'used', 'clustername': cluster, 'node': node}
    requests.put('{}/{}/addresses/{}'.format(BASE, network, address), json=assigned)
    return address


def deallocate(network, address):
    """Deallocate a given network address"""
    free = {'status': 'free', 'clustername': '_', 'node': '_'}
    r = requests.put('{}/{}/addresses/{}'.format(BASE, network, address), json=free)
    return r
