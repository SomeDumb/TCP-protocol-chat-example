# TCP client-server chat example.

# Install


## Install via pip
```bash
pip install tcp-client-server-raidix
```

# Install via github

```sh
git clone git@github.com:SomeDumb/TCP-protocol-chat-example.git
pip install -r requirements.txt
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
