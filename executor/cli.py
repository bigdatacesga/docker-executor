# -*- coding: utf-8 -*-
"""CLI
   Implements the CLI interface using click
"""
from __future__ import print_function
import logging
import click
import registry
from . import docker
# we need the config module to load the logging configuration

logger = logging.getLogger(__name__)

# For debugging use global endpoint instead of localhost connection
registry.connect('http://10.112.0.101:8500/v1/kv')


@click.group(chain=True)
def cli():
    """Run docker containers

    Example:

        docker-executor run instances/jlopez/cdh/5.7.0/9/nodes/slave1
    """
    pass


@cli.command('run')
@click.option('--pipework/--no-pipework', default=True, help="Add network connectivity")
@click.option('--consul/--no-consul', default=True, help="Register in consul service discovery")
@click.option('--daemon/--no-daemon', default=False, help="Enable daemon mode")
@click.argument('nodedn')
def launch_cmd(pipework, consul, daemon, nodedn):
    docker.run(nodedn, daemon)


@cli.command('show')
@click.argument('nodedn')
def show_cmd(nodedn):
    node = registry.Node(nodedn)
    print('name: {}\nstatus: {}'.format(node.name, node.status))
