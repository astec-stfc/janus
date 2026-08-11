# watcher.py
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from app.services.sync import import_file, full_scan

WATCH_PATH = "/data/filestore"


class HDFHandler(FileSystemEventHandler):

    def on_created(self, event):

        if event.is_directory:
            return

        path = Path(event.src_path)

        if path.suffix in [".h5", ".hdf5", ".openpmd.hdf5"]:
            import_file(path)


def start_watcher():
    if not Path(WATCH_PATH).exists():
        print(f"Watch path {WATCH_PATH} does not exist. Creating it.")
        Path(WATCH_PATH).mkdir(parents=True, exist_ok=True)
    observer = Observer()
    observer.schedule(
        HDFHandler(),
        WATCH_PATH,
        recursive=True
    )
    print("Starting full scan..")
    full_scan()
    print("Full scan completed.")
    observer.start()
    try:
        observer.join()
    except KeyboardInterrupt:
        observer.stop()
        print("Observer stopped.")