
# --- User profiles ---
import json as _pjson
import os as _pos2

class ProfileManager:
    """Simple user profile management for barn-appar."""

    def __init__(self, app_name):
        self._app_name = app_name
        self._dir = _pos2.path.join(_pos2.path.expanduser('~'), '.config', app_name, 'profiles')
        _pos2.makedirs(self._dir, exist_ok=True)
        self._current = self._load_current()

    def _load_current(self):
        try:
            with open(_pos2.path.join(self._dir, '.current')) as f:
                return f.read().strip()
        except (FileNotFoundError, OSError):
            return 'default'

    @property
    def current(self):
        return self._current

    def switch(self, name):
        self._current = name
        with open(_pos2.path.join(self._dir, '.current'), 'w') as f:
            f.write(name)

    def list_profiles(self):
        profiles = ['default']
        for f in sorted(_pos2.listdir(self._dir)):
            if f.endswith('.json') and f != '.current':
                profiles.append(f[:-5])
        return list(set(profiles))

    def save_data(self, data):
        with open(_pos2.path.join(self._dir, f'{self._current}.json'), 'w') as f:
            _pjson.dump(data, f, ensure_ascii=False, indent=2)

    def load_data(self):
        try:
            with open(_pos2.path.join(self._dir, f'{self._current}.json')) as f:
                return _pjson.load(f)
        except (FileNotFoundError, _pjson.JSONDecodeError):
            return {}
