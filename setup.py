from setuptools import setup, find_packages

setup(
    name='docker-executor',
    version='0.1.8',
    author='Javier Cacheiro',
    author_email='bigdata-dev@listas.cesga.es',
    url='https://github.com/javicacheiro/docker-executor',
    license='MIT',
    description='Docker executor with pipework and consul support',
    long_description=open('README.rst').read(),
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',
        'consul-service-discovery',
        'configuration_registry',
        'kvstore',
    ],
    entry_points='''
        [console_scripts]
        docker-executor=executor.cli:cli
    ''',
    scripts=['utils/pipework'],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
