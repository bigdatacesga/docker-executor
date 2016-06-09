"""Tests for docker-executor"""
import unittest
import kvstore
from executor import docker
from executor.docker import Volume, Network
from executor import net
from executor import servicediscovery
from executor import utils


ENDPOINT = 'http://10.112.0.101:8500/v1/kv'


class DockerTestCase(unittest.TestCase):

    def setUp(self):
        self.kv = kvstore.Client(ENDPOINT)

        # Mock utils.run()
        def _cmd(command):
            return command
        utils.run = _cmd

    def tearDown(self):
        self.kv.delete('__testingdockerexecutor__', recursive=True)

    def test_generate_volume_opts(self):
        v1 = Volume('/tmp/origin1', '/data/1', 'rw')
        v2 = Volume('/tmp/origin2', '/data/2', 'ro')
        volumes = [v1, v2]
        returned = docker.generate_volume_opts(volumes)
        expected = '-v /tmp/origin1:/data/1:rw -v /tmp/origin2:/data/2:ro '
        self.assertEqual(returned, expected)

    def test_generate_docker_opts(self):
        common_opts = docker.DOCKER_RUN_OPTS
        extra_opts = '--privileged -v /sys/fs/cgroup:/sys/fs/cgroup:ro -v /dev/log:/dev/log'
        returned = docker.generate_docker_opts(extra_opts)
        expected = '{} {} '.format(common_opts, extra_opts)
        self.assertEqual(returned, expected)

    def test_generate_docker_opts_daemon_mode(self):
        common_opts = docker.DOCKER_RUN_OPTS
        extra_opts = '--privileged -v /sys/fs/cgroup:/sys/fs/cgroup:ro -v /dev/log:/dev/log'
        returned = docker.generate_docker_opts(extra_opts, daemon=True)
        expected = '{} {} -d '.format(common_opts, extra_opts)
        self.assertEqual(returned, expected)

    def test_register_in_consul(self):
        raise NotImplementedError
        
    #def test_set_new_key_starting_with_slash(self):
        #key = '/__testing__/testsetnew'
        #value = '123456'
        #self.kv.set(key, value)
        #returned = self.kv.get(key)
        #self.assertEqual(returned, value)


class NetTestCase(unittest.TestCase):

    def setUp(self):
        self.kv = kvstore.Client(ENDPOINT)

        # Mock utils.run()
        def _cmd(command):
            return command
        utils.run = _cmd

    def test_configure_network_interface_with_gateway(self):
        container = 'test1'
        n = Network('eth0', '10.112.200.123', 'virbrPRIVATE', '16', '10.112.0.1',
                    'admin', 'dynamic')
        cmd = net.configure_interface(container, n)
        expected = 'pipework {bridge} -i {device} {name} {ip}/{mask}@{gateway}'.format(
            bridge=n.bridge, device=n.device, name=container, ip=n.address,
            mask=n.netmask, gateway=n.gateway)
        self.assertEqual(cmd, expected)

    def test_configure_network_interface_without_gateway(self):
        container = 'test1'
        n = Network('eth0', '10.112.200.123', 'virbrSTORAGE', '16', None, 'admin', 'dynamic')
        cmd = net.configure_interface(container, n)
        expected = 'pipework {bridge} -i {device} {name} {ip}/{mask}'.format(
            bridge=n.bridge, device=n.device, name=container, ip=n.address,
            mask=n.netmask)
        self.assertEqual(cmd, expected)


class ServiceDiscoveryTestCase(unittest.TestCase):

    def setUp(self):
        self.kv = kvstore.Client(ENDPOINT)

        # Mock utils.run()
        def _cmd(command):
            return command
        utils.run = _cmd

    def test_generate_checks(self):
        check_ports = ('22', '5000')
        container = 'test'
        address = '10.1.2.3'
        checks = servicediscovery.generate_checks(container, address, check_ports)
        expected = {
            'checks': [
                {'id': '{}-port22'.format(container),
                 'name': 'Check TCP port 22',
                 'tcp': '{}:{}'.format(address, 22),
                 'Interval': '30s',
                 'timeout': '4s'},
                {'id': '{}-port5000'.format(container),
                 'name': 'Check TCP port 5000',
                 'tcp': '{}:{}'.format(address, 5000),
                 'Interval': '30s',
                 'timeout': '4s'},
            ]
        }
        self.assertEqual(checks, expected)


if __name__ == '__main__':
    unittest.main()
