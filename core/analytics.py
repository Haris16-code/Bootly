import os
import uuid
import threading
import urllib.parse
import urllib.request
import time
import json

GA4_MEASUREMENT_ID = "G-34X5FX8JKQ"
GA4_ENDPOINT = "https://www.google-analytics.com/g/collect"

class AnalyticsManager:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        return cls._instance

    @classmethod
    def init(cls, base_path):
        if cls._instance is None:
            cls._instance = cls(base_path)
        return cls._instance

    def __init__(self, base_path):
        self.base_path = base_path
        self.config_file = os.path.join(self.base_path, '.bootly_id')
        self.config = self._load_config()
        self.client_id = self.config.get("client_id")
        self.session_id = str(int(time.time()))
        
    def _load_config(self):
        """Loads or initializes the configuration dictionary."""
        config = {
            "client_id": str(uuid.uuid4()), 
            "accepted_warning": False,
            "root_warning_accepted": False
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        try:
                            # Try parsing as JSON
                            loaded = json.loads(content)
                            if isinstance(loaded, dict):
                                config.update(loaded)
                                return config
                        except json.JSONDecodeError:
                            # Legacy plain string UUID support
                            if len(content) > 30: # Likely a UUID
                                config["client_id"] = content
                                self._save_config(config) # Migrate to JSON
                                return config
        except Exception:
            pass
            
        self._save_config(config)
        return config

    def _save_config(self, config):
        """Saves the configuration dictionary to disk."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
        except Exception:
            pass

    def is_warning_accepted(self):
        """Returns True if the user has accepted the startup warning."""
        return self.config.get("accepted_warning", False)

    def accept_warning(self):
        """Marks the startup warning as accepted and saves to disk."""
        self.config["accepted_warning"] = True
        self._save_config(self.config)

    def is_root_warning_accepted(self):
        """Returns True if the user has accepted the rooting warning."""
        return self.config.get("root_warning_accepted", False)

    def accept_root_warning(self):
        """Marks the rooting warning as accepted and saves to disk."""
        self.config["root_warning_accepted"] = True
        self._save_config(self.config)

    def log_event(self, event_name, params=None):
        def _send():
            try:
                # v=2 for GA4 protocol
                data = {
                    "v": "2",
                    "tid": GA4_MEASUREMENT_ID,
                    "cid": self.client_id,
                    "en": event_name,
                    "sid": self.session_id,
                    "seg": "1",
                    "_s": "1"
                }
                
                if params and isinstance(params, dict):
                    for k, v in params.items():
                        # Clean param names to ensure compliance
                        data[f"ep.{k}"] = str(v)
                        
                query_string = urllib.parse.urlencode(data)
                url = f"{GA4_ENDPOINT}?{query_string}"
                
                req = urllib.request.Request(url, method="POST", headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                with urllib.request.urlopen(req, timeout=5) as response:
                    pass  # We don't care about the response, just that it didn't crash
            except Exception as e:
                # Fail completely silently so users never see an error if they are offline
                pass
                
        # Detach the HTTP request natively into a background thread
        thread = threading.Thread(target=_send)
        thread.daemon = True
        thread.start()

def log_ga_event(event_name, params=None):
    am = AnalyticsManager.get_instance()
    if am:
        am.log_event(event_name, params)
