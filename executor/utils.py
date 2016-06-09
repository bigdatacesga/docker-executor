import subprocess


def run(cmd):
    """Execute cmd on the shell"""
    print('==> {}'.format(cmd))
    return subprocess.call(cmd, shell=True)
