# AUTOGENERATED FROM: p2p_sync/app.ipynb

# Cell: 0
import os
import time
import json
import base64
from typing import Dict, Any, List
from functools import partial
from entangle.entanglement import Entanglement
from entangle.client import Client
from entangle.server import listen

from watchdog.observers import Observer  
from watchdog.events import FileSystemEventHandler, DirCreatedEvent, DirDeletedEvent, FileCreatedEvent, FileDeletedEvent, DirModifiedEvent, FileModifiedEvent, DirMovedEvent, FileMovedEvent


# Cell: 1
_EXCLUDE_PATTERNS = [".ipynb_checkpoints/", ".~", "__pycache__/"]
_HANDLER = None


# Cell: 2
import hashlib
def compute_md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


# Cell: 3
# Save the transaction database
def save_transactions(database_file: str, database: Dict):
    data = json.dumps(database)
    with open(database_file, "w") as f:
        f.write(data)


# Cell: 4
# Load the transaction database
def load_transactions(database_file) -> Dict:
    if not os.path.exists(database_file):
        print("No database found, creating a new one.")
        database = {}
        save_transactions(database_file, database)

    with open(database_file, "r") as f:
        database = json.loads(f.read())
    return database


# Cell: 5
class FileChangeHandler(FileSystemEventHandler):
    exclude_patterns = []
    mappings = {}
    database_path = "database.json"
    
    def get_sync_name(self, fname):
        for namespace, path in self.mappings.items():
            if not path.endswith("/"):
                path += "/"
            if fname.startswith(path):
                return fname.replace(path, namespace + ":")

    def on_moved(self, event):
        """
        event.is_directory
            True | False
        event.src_path
            path/to/observed/file
        """
        raw_name = event.src_path.replace("\\", "/")
        if event.src_path.endswith("Neues Textdokument.txt"):
            self.on_created(FileCreatedEvent(event.dest_path))
        else:
            if not isinstance(event, DirMovedEvent):
                self.on_deleted(FileDeletedEvent(raw_name))
                self.on_created(FileCreatedEvent(event.dest_path))
        
        #if self.is_excluded(event):
        #    return
        #
        #fname = self.get_sync_name(raw_name)
        #fname_moved = self.get_sync_name(event.dest_path)
        #
        #transactions = load_transactions(self.database_path)
        #transaction = {"timestamp": time.time(), "type": "moved", "new_location": fname_moved}
        #transactions[fname] = transaction
        #transaction = {"timestamp": time.time(), "type": "moved", "old_location": fname, "md5": compute_md5(event.dest_path)}
        #transactions[fname] = transaction
        #save_transactions(self.database_path, transactions)
        
        #if len(fname) > 128:
        #    fname = fname[:63] + "..." + fname[-62:]            
        #print("\rMoved: {:<128} (len watches: {})".format(fname, len(transactions)), end="")


    def on_created(self, event):
        if event.is_directory:
            return
        if self.is_excluded(event):
            return
        
        raw_name = event.src_path.replace("\\", "/")
        fname = self.get_sync_name(raw_name)
        
        transactions = load_transactions(self.database_path)
        md5 = compute_md5(raw_name)
        if fname not in transactions or transactions[fname]["md5"] != md5:
            transaction = {"timestamp": time.time(), "type": "created", "md5": md5}
            transactions[fname] = transaction
            save_transactions(self.database_path, transactions)
        
            if len(fname) > 128:
                fname = fname[:63] + "..." + fname[-62:]            
            print("\rCreated: {:<128} (len watches: {})".format(fname, len(transactions)), end="")

    def on_deleted(self, event):
        if self.is_excluded(event):
            return
        
        raw_name = event.src_path.replace("\\", "/")
        fname = self.get_sync_name(raw_name)
        
        transactions = load_transactions(self.database_path)
        if fname not in transactions or transactions[fname]["type"] != "deleted":
            transaction = {"timestamp": time.time(), "type": "deleted"}
            transactions[fname] = transaction
            save_transactions(self.database_path, transactions)
        
            if len(fname) > 128:
                fname = fname[:63] + "..." + fname[-62:]
            print("\rDeleted: {:<128} (len watches: {})".format(fname, len(transactions)), end="")

    def on_modified(self, event):
        if event.is_directory:
            return
        if self.is_excluded(event):
            return
        
        raw_name = event.src_path.replace("\\", "/")
        fname = self.get_sync_name(raw_name)
        
        transactions = load_transactions(self.database_path)
        md5 = compute_md5(raw_name)
        if fname not in transactions or transactions[fname]["md5"] != md5:
            transaction = {"timestamp": time.time(), "type": "modified", "md5": md5}
            transactions[fname] = transaction
            save_transactions(self.database_path, transactions)

            if len(fname) > 128:
                fname = fname[:63] + "..." + fname[-62:]
            print("\rModified: {:<128} (len watches: {})".format(fname, len(transactions)), end="")

    def is_excluded(self, event):
        raw_name = event.src_path.replace("\\", "/")
        if raw_name.endswith("Neues Textdokument.txt"):
            return True

        # Filter by exclude pattern.
        for pattern in self.exclude_patterns:
            pattern = pattern.replace("\\", "/")
            if pattern.endswith("/"):
                if pattern in raw_name:
                    return True
                if event.is_directory and raw_name.endswith(pattern[:-1]):
                    return True
            else:
                if raw_name.split(os.sep)[-1].startswith(pattern):
                    return True
                if raw_name.endswith(pattern):
                    return True

        return False


# Cell: 6
def initial_scan(handler):
    tracked_files = []
    paths = list(handler.mappings.values())
    
    # check filelist for deletions or modifications
    print("\n\rScanning Tracked Files")
    transactions = load_transactions(handler.database_path)
    for fname, v in transactions.items():
        namespace, name = fname.split(":")
        disk_name = os.path.join(handler.mappings[namespace], name)
        if len(fname) > 128:
            fname = fname[:63] + "..." + fname[-62:]
        print("\rScanning: {:<128} (len queue: {})".format(fname, len(transactions)), end="")
        
        if os.path.exists(disk_name):
            tracked_files.append(disk_name)
            if compute_md5(disk_name) != v["md5"]:
                handler.on_modified(FileModifiedEvent(disk_name))
        elif not v["type"] == "deleted":
            handler.on_deleted(FileDeletedEvent(disk_name))
    print("\n\rScanning Completed")

    for path in paths:
        print("n\rScanning: {}".format(path))
        print("(no changes)", end="")
        # check if a file was created that is not yet in filelist
        for f in [os.path.join(root, name) for root, dirs, files in os.walk(path) for name in files]:
            f = f.replace("/", os.sep)
            if f not in tracked_files:
                handler.on_created(FileCreatedEvent(f))
        print("\n\rScanning Completed")


# Cell: 7
def on_retrieve_file(state, entanglement, data: Dict):
    namespace, name = data["fname"].split(":")
    disk_name = os.path.join(state["handler"].mappings[namespace], name).replace("/", os.sep)
    transactions = load_transactions(state["handler"].database_path)
    transactions[data["fname"]] = data["transaction"]
    save_transactions(state["handler"].database_path, transactions)
    
    if not data["transaction"]["type"] == "deleted":
        print("Writing: {}".format(disk_name))
        if not os.path.exists(os.path.dirname(disk_name)):
            os.makedirs(os.path.dirname(disk_name))
        with open(disk_name, "wb") as f:
            f.write(base64.decodestring(data["data"].encode("ascii")))
    else:
        print("Deleting: {}".format(disk_name))
        if os.path.exists(disk_name):
            os.remove(disk_name)

    state["open_tasks"] -= 1

def retrieve_file(state, entanglement, fname):
    data = {}
    
    namespace, name = fname.split(":")
    disk_name = os.path.join(state["handler"].mappings[namespace], name).replace("/", os.sep)
    
    transactions = load_transactions(state["handler"].database_path)
    data["transaction"] = transactions[fname]
    data["fname"] = fname
    
    if not data["transaction"]["type"] == "deleted":
        with open(disk_name, "rb") as f:
            data["data"] = base64.encodestring(f.read()).decode("ascii")
    entanglement.remote_fun("on_sync_retrieve_file")(data)

def on_get_database(state, entanglement, transactions: Dict):
    transactions_local = load_transactions(state["handler"].database_path)
    
    for key in transactions:
        namespace, name = key.split(":")
        if namespace not in state["handler"].mappings:
            continue
        if key not in transactions_local:
            state["open_tasks"] += 1
            entanglement.remote_fun("sync_retrieve_file")(key)
        elif key in transactions:
            local_time = transactions_local[key]["timestamp"]
            remote_time = transactions[key]["timestamp"]
            if remote_time > local_time:
                state["open_tasks"] += 1
                entanglement.remote_fun("sync_retrieve_file")(key)
    
    state["open_tasks"] -= 1

def get_database(state, entanglement):
    #print("get_database")
    transactions = load_transactions(state["handler"].database_path)
    entanglement.remote_fun("on_sync_get_database")(transactions)
    
    
def format_len(size):
    if size > 1e12:
        return "{:.1f} TB".format(size/1e12)
    elif size > 1e9:
        return "{:.1f} GB".format(size/1e9)
    elif size > 1e6:
        return "{:.1f} MB".format(size/1e6)
    elif size > 1e3:
        return "{:.1f} KB".format(size/1e3)
    else:
        return "{:.1f} B".format(size)

def on_entangle(entanglement):
    state = {}
    state["handler"] = _HANDLER
    entanglement.on_sync_retrieve_file = partial(on_retrieve_file, state, entanglement)
    entanglement.on_sync_get_database = partial(on_get_database, state, entanglement)
    entanglement.sync_get_database = partial(get_database, state, entanglement)
    entanglement.sync_retrieve_file = partial(retrieve_file, state, entanglement)
    print("Waiting 5 seconds for readiness.")
    time.sleep(5)
    print("Connected. Syncing...")
    while True:
        #print("Issuing update of local database...")
        state["open_tasks"] = 1
        entanglement.remote_fun("sync_get_database")()
        while state["open_tasks"] > 0:
            time.sleep(1)

        #print("Waiting 5 seconds before next sync round.")
        time.sleep(5)


# Cell: 8
def run_sync():
    global _HANDLER
    # Load user_data
    if "AppData" in os.environ: # Windows
        config_file = os.path.join(os.environ["AppData"], "p2p_sync", "config.json")
        syncignore_path = os.path.join(os.environ["AppData"], "p2p_sync", ".syncignore")
        database_path = os.path.join(os.environ["AppData"], "p2p_sync", "database.json")
    else: # Linux
        config_file = os.path.join("/home", os.environ["USER"], ".p2p_sync", "config.json")
        syncignore_path = os.path.join("/home", os.environ["USER"], ".p2p_sync", ".syncignore")
        database_path = os.path.join("/home", os.environ["USER"], ".p2p_sync", "database.json")
    if not os.path.exists(config_file):
        raise RuntimeError("Config does not exist: {}".format(config_file))
    with open(config_file, "r") as f:
        config = json.loads(f.read())

    # Load exclude patterns
    exclude_patterns=_EXCLUDE_PATTERNS
    if os.path.exists(syncignore_path):
        with open(syncignore_path, "r") as f:
            exclude_patterns = f.readlines()
        exclude_patterns = [pattern.replace("\n", "") for pattern in exclude_patterns]
        exclude_patterns = [pattern for pattern in exclude_patterns if pattern != "" and not pattern.startswith("#")]
        print("Ignore Patterns: {}".format(exclude_patterns))
    observer = Observer()
    handler = FileChangeHandler()
    handler.exclude_patterns = exclude_patterns
    handler.database_path = database_path
    handler.mappings = config["sync_to_local_folder"]
    initial_scan(handler)
    _HANDLER = handler
    for path in handler.mappings.values():
        observer.schedule(handler, path=path, recursive=True)
    observer.start()

    print("Connecting...")
    # 1. Try connecting to all known hosts
    clients = []
    for hosts in config["known_hosts"]:
        clients.append(Client(host=hosts["host"], port=hosts["port"], password=hosts["password"], user=hosts["user"], callback=on_entangle, blocking=False, run_reactor=False))
    # 2. Start own server
    listen(host=config["host"], port=config["port"], callback=on_entangle, users=config["users"])
    
    observer.stop()

    observer.join()


# Cell: 9
if __name__ == "__main__":
    run_sync()
