"""Reload local development settings without overriding host-provided secrets."""
import os
from pathlib import Path
from threading import Lock


# PSEUDOCODE: CONFIGURATION OWNERSHIP
# TRACK the local file signature and values this loader owns.
# ALLOW only recognized configuration variable names.
class LocalConfig:
    allowed = {'OPENAI_API_KEY', 'OPENAI_MODEL', 'HOST', 'PORT', 'APP_PASSWORD'}

    def __init__(self, path, environ=None):
        self.path = Path(path)
        self.environ = os.environ if environ is None else environ
        self.signature = None
        self.owned = {}
        self.lock = Lock()

    # PSEUDOCODE: CONFIGURATION REFRESH
    # LOCK updates and skip unchanged files.
    # PARSE supported assignments, quotes and comments.
    # PRESERVE nonempty settings owned by the deployment environment.
    # UPDATE or remove values previously owned by this loader.
    # REMEMBER the new file signature for the next request.
    def refresh(self):
        with self.lock:
            try:
                info = self.path.stat()
                signature = (info.st_mtime_ns, info.st_size)
            except FileNotFoundError:
                signature = None
            if signature == self.signature:
                return
            # Read first so a partially saved file can be retried on the next request.
            contents = self.path.read_text(encoding='utf-8-sig') if signature else ''
            values = {}
            for line in contents.splitlines():
                line = line.strip()
                if line.startswith('export '):
                    line = line[7:].lstrip()
                if '=' not in line or line.startswith('#'):
                    continue
                name, value = line.split('=', 1)
                name, value = name.strip(), value.strip()
                if name not in self.allowed:
                    continue
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                else:
                    value = value.split(' #', 1)[0].rstrip()
                values[name] = value
            for name in set(values) | set(self.owned):
                current = self.environ.get(name)
                if name in self.owned:
                    # A caller or deployment that changed the variable takes ownership.
                    if current != self.owned[name]:
                        del self.owned[name]
                        continue
                elif current and current.strip():
                    continue
                if name in values:
                    self.environ[name] = values[name]
                    self.owned[name] = values[name]
                else:
                    self.environ.pop(name, None)
                    self.owned.pop(name, None)
            self.signature = signature
