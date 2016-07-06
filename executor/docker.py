from __future__ import print_function
import os
import registry
from . import utils
from . import net
from . import servicediscovery
import Queue
import threading
from time import sleep
import socket
import subprocess

# Do not assign a local IP to the node
# DOCKER_FIX trick to avoid this issue:
# https://github.com/docker/docker/issues/14203
DOCKER_RUN_OPTS = ('--net="none" '
                   '-v /root/.ssh/authorized_keys:/root/.ssh/authorized_keys '
                   '-t -e DOCKER_FIX=""')
# https://docs.docker.com/engine/reference/run/#cpu-period-constraint
CPU_PERIOD = 50000


def run(nodedn, daemon=False):
    """Run a given container

    This command gets the info needed to launch the container from the registry.
    """
    # TODO: Move the properties to a config module so this part is independent from
    # what you use to retrieve the information
    node = registry.Node(nodedn)

    nodename = node.name
    instanceid = registry.id_from(str(node))
    container_name = '{0}-{1}'.format(instanceid, node.name)
    container_image = node.docker_image

    docker_opts = node.get('docker_opts', '')
    port = node.get('port')
    tags = node.get('tags')
    if tags:
        tags = tags.split(',')
    check_ports = node.get('check_ports')
    if check_ports:
        check_ports = check_ports.split(',')

    service = node.cluster.dnsname
    disks = node.disks
    networks = node.networks
    cpu = node.cpu
    mem = node.mem

    opts = generate_docker_opts(docker_opts, daemon)
    limits = generate_resource_limits(cpu, mem)
    volumes = generate_volume_opts(disks)

    docker_pull = 'docker pull {image}'.format(image=container_image)
    utils.run(docker_pull)

    docker_run = 'docker run {limits} {opts} {volumes} -h {hostname} --name {name} {image}'.format(
        hostname=nodename, name=container_name, opts=opts, limits=limits,
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
    net.configure(container_name, networks, instanceid)
    servicediscovery.register(container_name, service, networks[0].address,
                              tags=tags, port=port, check_ports=check_ports)

    node.id = container_name
    node.host = socket.gethostname()

    # We need to store the docker Name Space PID for later removal of the veth
    # pair created by pipework
    docker_nspid = subprocess.check_output(["docker", "inspect", "--format='{{ .State.Pid }}'", container_name])
    node.nspid = docker_nspid.strip()

    node.status = 'running'

    t.join()
    #output = q.get()
    #return output


def stop(nodedn):
    """Stop a running container"""
    # TODO: Move the properties to a config module
    node = registry.Node(nodedn)
    name = node.id
    networks = node.networks
    clean_pipework_devices(node)
    docker_stop = 'docker stop {}'.format(name)
    utils.run(docker_stop)
    node.status = 'stopped'
    net.release(networks)
    servicediscovery.deregister(name)


def clean_pipework_devices(node):
    """Remove the veth pair created by pipework"""
    print("==> Cleaning pipework network devices")
    # Get the docker process Name Space PID
    nspid = node.nspid
    # Add the NSPID of this docker to allow using it with ip netns
    utils.run('ln -s "/proc/{0}/ns/net" "/var/run/netns/{0}"'.format(nspid))
    for dev in node.networks:
        # Guest veth
        utils.run('ip netns exec {nspid} ip link del {dev}'
                  .format(nspid=nspid, dev=dev.name))
        #subprocess.call(["ip", "netns", "exec", nspid,
                         #"ip", "link", "del", dev.name])
        # Local veth
        local_ifname = 'v{}pl{}'.format(dev.name, nspid)
        utils.run('ip link del {}'.format(local_ifname))
        #subprocess.call(["ip", "link", "del", local_ifname])
    # Remove the traces of the namespace
    utils.run('rm -f "/var/run/netns/{}"'.format(nspid))


def destroy(nodedn):
    """Destroy a running container, ie. stop and remove the local image"""
    # First stop the container
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
        mode = volume.get('mode', 'rw')
        volume_opts += '-v {}:{}:{} '.format(volume.origin, volume.destination, mode)
    return volume_opts


def generate_docker_opts(extra_opts, daemon=False):
    opts = DOCKER_RUN_OPTS
    opts += ' ' + extra_opts + ' '
    if daemon:
        opts += '-d '
    return opts


def generate_resource_limits(cpu, mem):
    """Generate the limits options for cpu and memory

    mem should be given in MB
    cpu should be given in number of cores
    """
    # https://docs.docker.com/engine/reference/run/#cpu-quota-constraint
    opts = ' --cpu-quota={} --cpu-period={}'.format(int(cpu)*CPU_PERIOD, CPU_PERIOD)
    opts += ' --memory={}m'.format(mem)
    return opts
