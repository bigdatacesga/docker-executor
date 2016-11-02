import consul
import config
import logging

logger = logging.getLogger(__name__)


def register(container_name, service_name, address,
             tags=None, port=None, check_ports=None):
    """Register the docker container in consul service discovery"""
    sd = consul.Client(config.CONSUL_URL)
    if check_ports:
        checks = generate_checks(container_name, address, check_ports)
        #FIXME: It seems the API only accepts one check at service registration time
        # To register multiple checks register each one using /v1/agent/check/register
        checks = checks['checks'][0]
    else:
        checks = None
    logger.info("Registering the container in Consul Service Discovery")
    sd.register(container_name, service_name, address,
                tags=tags, port=port, check=checks)
    #sd.register(container_name, service_name, address,
    #            tags=tags, port=port, check=checks)


def deregister(container_name):
    """Deregister the docker container from consul service discovery"""
    sd = consul.Client(config.CONSUL_URL)
    logger.info("Deregistering the container from Consul Service Discovery")
    sd.deregister(container_name)


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
