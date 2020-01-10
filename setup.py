from setuptools import setup, find_packages
import os

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()


def get_debian_version(basedir):
    version = '0.1'
    with open(os.path.join(basedir, 'debian', 'changelog'), 'r') as f:
        for line in f.readlines():
            if line[:27] == 'prometheus-swagger-exporter':
                version = line.split('(')[1].split(')')[0].split('-')[0]
                break
    return version


install_requires = [
    'bottle>=0.12',
    'gevent>=1.1',
    'prometheus_client>=0.0.18',
    'servicechecker>=0.2.0'
]
dependency_links = [
    'git+https://gerrit.wikimedia.org/r/operations/software/service-checker@tags/upstream/0.2.0#egg=servicechecker-0.2.0'
]

description = "A Prometheus exporter that renders metrics from requests"
"executed by service-checker."

setup(
    name='prometheus-swagger-exporter',
    version=get_debian_version(here),
    description=description,
    long_description=README,
    author='Cole White',
    author_email='cwhite@wikimedia.org',
    url='https://gerrit.wikimedia.org/r/plugins/gitiles/operations/debs/prometheus-swagger-exporter/',
    license='GPL',
    packages=find_packages(),
    install_requires=install_requires,
    dependency_links=dependency_links,
    entry_points={
        'console_scripts': [
            'prometheus-swagger-exporter = prometheus_swagger_exporter:main'
        ]
    },
)
