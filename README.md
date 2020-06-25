# Peer to Peer Sync App

> A simple direct peer to peer synchronization app.


## Install

Make sure you have ssl and git installed.
```bash
sudo apt -y install libssl-dev git
```

Clone and install editable.

```bash
git clone ...
cd p2p_sync
pip install -e .
```

## Configuration

p2p sync is controlled by a config file, which needs to be created:

* Windows Config File: `%AppData%\backup_sync\config.json`
* Linux Config File: `~/.backup_sync/config.json`

The content of the file should be the following:

```json
{
    "host": "*",
    "port": 24455,
    "users": {
        "myname": "some_password",
        "othername": "other_password"
    },
    "known_hosts": [
        {
            "host": "other-pc",
            "port": 24455,
            "user": "myname",
            "password": "some_password"
        },
        {
            "host": "yet-other-pc",
            "port": 24455,
            "user": "myname",
            "password": "some_password"
        }
    ],
    "sync_to_local_folder": {
        "share_name": "/path/to/local/folder",
        "other_share_name": "/path/to/other/local/folder",
        "yet_another_share_name": "/path/to/yet/another/local/folder"
    }
}
```

The configuration consists out of a block defining how other devices can reach your device, a block "known_hosts" defining all other devices your device knows and tries to connect to and a block of what syncs exist on this device. It will try to sync those shares with other devices, if they have a sync in common.

## Run

```bash
p2p_sync
```
