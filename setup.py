import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name = "tcp_client_server_raidix",
    version = "0.0.1",
    author = "Elnur Guliev",
    author_email = "gulievelnur@gmail.com",
    description = ("Working TCP server and client with logging"),
    packages=['server', 'client'],
    install_requires=required,
)
