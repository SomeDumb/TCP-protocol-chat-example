# Raidix
TCP client-server chat example.

# Install


## Install with pip
```bash
pip install tcp-client-server-raidix
```
## Run server
```python

from server import server
s = server.Server('localhost', 2120)
```
## Run client
```python
from client import client

ip = input('ip: ')
cl = client.Client(ip)
```
