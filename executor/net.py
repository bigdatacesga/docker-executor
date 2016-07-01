"""Network Address Allocation Utils"""
import re
import requests
from . import utils


BASE = 'http://networks.service.int.cesga.es:5000/resources/networks/v1/networks'


def configure(containername, networks, clustername=''):
    """Configure the networks interfaces to the given container"""
    for network in networks:
        configure_interface(containername, network, clustername)


def configure_interface(containername, network, clustername=''):
    """Adds one network interface using pipework"""
    device = network.name
    address = network.get('address')
    type = network.type
    networkname = network.networkname

    info = basic_network_info(network)
    bridge = info['bridge']
    netmask = info['netmask']
    gateway = info['gateway']

    if not address or address == '_' or type == 'dynamic':
        address = allocate(networkname, containername, clustername)
        # Update registry info
        network.address = address

    if gateway and re.search(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', gateway):
        return utils.run(
            'pipework {bridge} -i {device} {name} {ip}/{mask}@{gateway}'
            .format(bridge=bridge, device=device, name=containername,
                    ip=address,
                    mask=netmask,
                    gateway=gateway))
    else:
        return utils.run(
            'pipework {bridge} -i {device} {name} {ip}/{mask}'
            .format(bridge=bridge, device=device, name=containername,
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


def allocate(networkname, nodename, clustername='_'):
    """Allocate a new network address to a given node that can belong to a cluster"""

    # TODO: Clean if not needed
    # # USING GET AND PUT
    # r = requests.get('{}/{}/addresses?free'.format(BASE, networkname))
    # data = r.json()
    # free = data['addresses']
    # address = sorted(free, reverse=True).pop()
    # assigned = {'status': 'used', 'cluster': clustername, 'node': nodename}
    # requests.put('{}/{}/addresses/{}'.format(BASE, networkname, address), json=assigned)

    # USING (atomic) POST
    data = {'cluster': clustername, 'node': nodename}
    r = requests.post('{}/{}/allocate'.format(BASE, networkname), json=data)
    if r.status_code != 200:
        raise Exception("Can't allocate address")
    address = r.content
    return address


def deallocate(network, address):
    """Deallocate a given network address"""
    free = {'status': 'free', 'cluster': '_', 'node': '_'}
    r = requests.put('{}/{}/addresses/{}'.format(BASE, network, address), json=free)
    return r


def basic_network_info(network):
    """Return basic network info from the networks service"""
    r = requests.get('{}/{}'.format(BASE, network.networkname))
    data = r.json()
    return {'bridge': data['bridge'], 'netmask': data['netmask'],
            'gateway': data['gateway']}

