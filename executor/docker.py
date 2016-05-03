import consul
import registry


def run(nodedn):
    """Run a given container

    This command gets the info needed to launch the container from the registry
    """
    node = registry.Node(nodedn)
    container_name = node.name
    container_image = node.image
    # Do not assign a local IP to the node
    OPTS = '--net="none" '
    # Privileged option is needed by gluster to create volumes
    # in other case you get the following error:
    # "Setting extended attributes failed, reason: Operation not permitted."
    OPTS += '--privileged '

    for n in range(1, 13):
        if not exists('/data/{}/{}'.format(n, SERVICE)):
            run('mkdir -p /data/{}/{}'.format(n, SERVICE))
        OPTS += '-v /data/{0}/{1}:/data/brick{0} '.format(n, SERVICE)

    #OPTS += '-v /dev/log:/dev/log '
    OPTS += '-v /sys/fs/cgroup:/sys/fs/cgroup:ro '
    OPTS += '-v /root/.ssh/authorized_keys:/root/.ssh/authorized_keys '
    OPTS += '-d '
    OPTS += '-ti '
    # DOCKER_FIX trick to avoid this issue:
    # https://github.com/docker/docker/issues/14203
    OPTS += "-e DOCKER_FIX='' "
    run('docker run {opts} -h {name} --name {name} {image}'.format(
        name=container_name, opts=OPTS, image=container_image))
    networks = node.networks
    add_network_connectivity(container_name, networks)
    register_in_consul(id=container_name, name=SERVICE,
                       address=networks['private']['address'], check='SSH')


def add_network_connectivity(container_name, networks):
    """Adds the public networks interfaces to the given container"""
    put('files/bin/pipework', '/tmp/pipework')
    run('chmod u+x /tmp/pipework')
    run('/tmp/pipework virbrSTORAGE -i eth0 {name} {ip}/{mask}'
        .format(name=container_name, ip=networks['storage']['address'],
                mask=networks['storage']['netmask']))
    run('/tmp/pipework virbrPRIVATE -i eth1 {name} {ip}/{mask}@{gateway}'
        .format(name=container_name, ip=networks['private']['address'],
                mask=networks['private']['netmask'],
                gateway=networks['gateway']))


def register_in_consul(id, name, address, check=None):
    """Register the docker container in consul service discovery"""
    sd = consul.Client()
    if check == 'SSH':
        check = {'id': id, 'name': 'SSH', 'tcp': '{}:{}'.format(address, 22),
                 'Interval': '30s', 'timeout': '4s'}
    sd.register(id, name, address, check=check)
