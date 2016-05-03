from setuptools import setup, find_packages

setup(
    name='docker-executor',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',
        'consul-service-discovery',
        'configuration-registry',
    ],
    entry_points='''
        [console_scripts]
        docker-executor=executor.cli:cli
    '''
)
