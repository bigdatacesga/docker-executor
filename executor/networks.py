"""Network Address Allocation Utils"""
import requests

BASE = 'http://networks.service.int.cesga.es:5000/resources/networks/v1/networks'


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
