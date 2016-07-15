import logging
import subprocess
import time

logger = logging.getLogger(__name__)

def run(cmd):
    """Execute cmd on the shell"""
    logger.info(cmd)
    return subprocess.call(cmd, shell=True)


def wait(container_name):
    """Wait until container is running"""
    logger.info('Verifying if container {} is running'.format(container_name))
    time.sleep(2)
    while is_not_running(container_name):
        logger.info('Waiting for container {} to start'.format(container_name))
        time.sleep(5)
    logger.info('Container {} is running'.format(container_name))


def is_not_running(container_name):
    """Check if a container is not running"""
    return not is_running(container_name)


def is_running(container_name):
    """Check if a container is running"""
    #show_cmd = ['docker', 'ps', '-q', '--filter', 'name={}'.format(container_name)]
    #found = subprocess.check_output(show_cmd)
    #if found == 0:
        #return True
    #return False

    # Alternative implementation: no need to parse output
    # docker top <name> exit status is 1 if the container is not running
    logger.info('Checking if container {} is running'.format(container_name))
    top_cmd = ['docker', 'top', container_name]
    exit_status = subprocess.call(top_cmd)
    if exit_status == 0:
        return True
    return False
