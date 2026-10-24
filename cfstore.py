"""Cloudflare Workers KV storage with a pickledb-style API (get / set / remove / exists / all / save).

Why this for shapes:
  * The bot code keeps calling `db.get(key)` / `db.set(key, value)` like it did with pickledb.
  * Reads come from an in-memory cache that is loaded once at startup, so commands never wait on the network.
  * Writes are batched in the background. KV allows roughly one write per second per key, so rapid updates to the
    same key (a busy counting channel) are coalesced and only the latest value is written.
  * All databases share ONE KV namespace; each database gets its own key prefix ("counting:", "embed:", ...).
  * If the Cloudflare env vars are missing, it falls back to local JSON files so you can still test the bot.

Env vars:
  CLOUDFLARE_API_TOKEN          API token with "Workers KV Storage: Edit"
  CLOUDFLARE_ACCOUNT_ID         your account id
  CLOUDFLARE_KV_NAMESPACE_ID    the KV namespace id (create one in Workers & Pages -> KV)
"""
import atexit
import json
import os
import threading
import time

FLUSH_INTERVAL = 1.5   # seconds between background write batches

_client = None
_client_lock = threading.Lock()
_stores = []


def _cf():
    """The shared Cloudflare client, or None when the env vars are not set."""
    global _client
    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    namespace = os.environ.get("CLOUDFLARE_KV_NAMESPACE_ID")
    if not (token and account and namespace):
        return None
    with _client_lock:
        if _client is None:
            from cloudflare import Cloudflare
            _client = Cloudflare(api_token=token)
    return _client


def _flush_all():
    for s in list(_stores):
        try:
            s.save()
        except Exception as e:
            print(f"[cfstore] final save failed for {s.name}: {e}")


atexit.register(_flush_all)


class CloudflareKV:
    def __init__(self, name):
        self.name = name
        self.prefix = f"{name}:"
        self._data = {}
        self._dirty = set()
        self._deleted = set()
        self._lock = threading.RLock()
        self._client = _cf()
        self._account = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        self._namespace = os.environ.get("CLOUDFLARE_KV_NAMESPACE_ID")
        self._path = f"{name}.json"
        self.backend = "cloudflare-kv" if self._client else "local-json"
        self._load()
        _stores.append(self)
        threading.Thread(target=self._flusher, name=f"cfstore-{name}", daemon=True).start()

    # ---- loading ----

    def _load(self):
        if not self._client:
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except FileNotFoundError:
                self._data = {}
            except Exception as e:
                print(f"[cfstore] could not read {self._path}: {e}")
            return
        try:
            names = []
            for key in self._client.kv.namespaces.keys.list(self._namespace, account_id=self._account, prefix=self.prefix):
                names.append(key.name)
            for full in names:
                raw = self._read(full)
                if raw is not None:
                    self._data[full[len(self.prefix):]] = raw
        except Exception as e:
            print(f"[cfstore] could not load '{self.name}' from Cloudflare KV: {e}")

    def _read(self, full_key):
        resp = self._client.kv.namespaces.values.get(full_key, account_id=self._account, namespace_id=self._namespace)
        text = resp.read().decode("utf-8")
        try:
            return json.loads(text)
        except ValueError:
            return text

    # ---- pickledb-style API ----

    def get(self, key, default=None):
        with self._lock:
            return self._data.get(str(key), default)

    def set(self, key, value):
        key = str(key)
        with self._lock:
            self._data[key] = value
            self._dirty.add(key)
            self._deleted.discard(key)
        return True

    def exists(self, key):
        with self._lock:
            return str(key) in self._data

    def remove(self, key):
        key = str(key)
        with self._lock:
            existed = self._data.pop(key, None) is not None
            self._dirty.discard(key)
            if existed:
                self._deleted.add(key)
        return existed

    def all(self):
        with self._lock:
            return list(self._data.keys())

    getall = all

    def items(self):
        with self._lock:
            return dict(self._data)

    def save(self):
        """Write everything that changed. Safe to call as often as you like."""
        with self._lock:
            dirty = {k: self._data[k] for k in self._dirty if k in self._data}
            deleted = set(self._deleted)
            self._dirty.clear()
            self._deleted.clear()
        if not dirty and not deleted and self._client:
            return True
        ok = True
        if not self._client:
            with self._lock:
                snapshot = dict(self._data)
            tmp = self._path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(snapshot, f)
            os.replace(tmp, self._path)
            return True
        for k, v in dirty.items():
            try:
                self._client.kv.namespaces.values.update(
                    self.prefix + k, account_id=self._account, namespace_id=self._namespace, value=json.dumps(v))
            except Exception as e:
                ok = False
                print(f"[cfstore] write failed for {self.name}:{k}: {e}")
                with self._lock:
                    if k in self._data:      # try again next round
                        self._dirty.add(k)
        for k in deleted:
            try:
                self._client.kv.namespaces.values.delete(self.prefix + k, account_id=self._account, namespace_id=self._namespace)
            except Exception as e:
                ok = False
                print(f"[cfstore] delete failed for {self.name}:{k}: {e}")
        return ok

    def _flusher(self):
        while True:
            time.sleep(FLUSH_INTERVAL)
            try:
                if self._dirty or self._deleted or not self._client:
                    # local-json mode only rewrites the file when something changed
                    if self._client or self._dirty or self._deleted:
                        self.save()
            except Exception as e:
                print(f"[cfstore] background save error in {self.name}: {e}")


def backend_summary():
    return ", ".join(f"{s.name}={s.backend}" for s in _stores) or "no stores"
