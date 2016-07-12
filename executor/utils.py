import subprocess
import time


def run(cmd):
    """Execute cmd on the shell"""
    print('==> {}'.format(cmd))
    return subprocess.call(cmd, shell=True)


def wait(container_name):
    """Wait until container is running"""
    while is_not_running(container_name):
        print 'Waiting for container {}'.format(container_name)
        time.sleep(2)


def is_not_running(container_name):
    """Check if a container is not running"""
    return not is_running(container_name)


def is_running(container_name):
    """Check if a container is running"""
    show_cmd = ['docker', 'ps', '-q', '--filter', 'name={}'.format(container_name)]
    found = subprocess.check_output(show_cmd)
    if found:
        return True
    return False


