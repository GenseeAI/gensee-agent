from dataclasses import dataclass, MISSING
import inspect
import os
import re
from typing import Any, Self, dataclass_transform

from .logging import configure_logger

logger = configure_logger(__name__)

_REGISTRY: dict[str, type] = {}

class BaseConfig:
    _config_key: str  # This will be set by the decorator.

    @classmethod
    def from_dict(cls, config: dict) -> Self:
        raise NotImplementedError("This method is defined in the @dataclass_transform decorator and BaseConfig should not be used without the decorator.")

    def to_dict(self) -> dict:
        return {
            self._config_key: {
                field: getattr(self, field) for field in self.__dataclass_fields__  # type: ignore[attr-defined]
            }
        }

    def pretty_print(self):
        """
        Print the parsed value, also print if the values are different from the default values.
        """
        print(f"Configuration for {self._config_key}:")
        for field_name, field in self.__dataclass_fields__.items():  # type: ignore[attr-defined]
            default_value = field.default
            if default_value is MISSING:
                default_value = "No default value"
            current_value = getattr(self, field_name)
            if default_value != current_value:
                print(f"  {field_name}: {current_value} (default: {default_value})")
            else:
                print(f"  {field_name}: {current_value}")


@dataclass_transform()
def register_configs(config_key: str):
    def decorator(cls):
        cls = dataclass(cls)
        # cls._class_dir = os.path.dirname(os.path.abspath(inspect.getfile(cls)))
        cls._placeholder_re = re.compile(r"(?<!\$)\$\{([^}]+)\}")  # supports escaping with $${...}

        @classmethod
        def from_dict(cls, config: dict):
            # TODO: Need potential customization here, for example, to ignore unknown fields.
            # fields = {f.name for f in c.__dataclass_fields__.values()}  # type: ignore[attr-defined]
            # return c(**{k: d[k] for k in d if k in fields})
            selected_config = config.get(config_key, {})
            parsed_config = cls._parse_placeholders(selected_config, root=config)
            logger.info(f"Parsed config for {config_key}: {parsed_config}")
            return cls(**parsed_config)

        @classmethod
        def _parse_placeholders(cls, config: str | dict, root: Any) -> dict:
            parsed_config = {}
            if isinstance(config, str):
                def _sub(m):
                    return str(cls._resolve_token(m.group(1).strip(), root=root) or "")
                return cls._placeholder_re.sub(_sub, config).replace("$${", "${")
            elif isinstance(config, dict):
                for k, v in config.items():
                    if isinstance(v, str):
                        def _sub(m):
                            return str(cls._resolve_token(m.group(1).strip(), root=root) or "")
                        new_v = cls._placeholder_re.sub(_sub, v).replace("$${", "${")
                        parsed_config[k] = new_v
                    elif isinstance(v, dict):
                        parsed_config[k] = cls._parse_placeholders(v, root=root)
                    elif isinstance(v, list):
                        parsed_config[k] = [cls._parse_placeholders(item, root=root) for item in v]
                    else:
                        parsed_config[k] = v
                return parsed_config
            else:
                raise ValueError("Config must be a string or a dictionary.")

        @classmethod
        def _resolve_token(cls, token: str, root: Any) -> Any:
            """
            Examples:
            ${env:HOME}         -> from environment
            ${relpath:./path}   -> relative to the config class file
            ${ref:/path/to/key} -> from root JSON via JSON-pointer-like path
            ${secret:name}      -> from secret manager
            ${secret:name.key}  -> from secret manager, parse as JSON and get key
            ${secret:name-with-[env].key} -> from secret manager, will replace [env] with value from environment variable 'env'
            """
            # default syntax: NAME or NAME:-default
            if ":" in token:
                kind, value = token.split(":", 1)
                kind = kind.strip().lower()
                if kind == "env":
                    return os.environ.get(value, None)
                if kind == "relpath":
                    class_dir = os.path.dirname(os.path.abspath(inspect.getfile(cls)))
                    return os.path.abspath(os.path.join(class_dir, value))
                if kind == "secret":
                    from .secret import Secret  # This is used internally.  # pyright: ignore[reportMissingImports]
                    project_id = os.environ.get("PROJECT_ID", "undefined")
                    if project_id == "undefined":
                        raise ValueError("PROJECT_ID environment variable not set for secret resolution.")
                    if not cls._secret_manager:
                        cls._secret_manager = Secret(project_id)
                    result = cls._secret_manager.get_secret(value)
                    if result.is_failure():
                        raise ValueError(f"Failed to retrieve secret '{value}': {result.get_error_message()}")
                    return result.value()
                if kind == "ref":
                    # simple JSON-pointer-ish (/a/b -> root["a"]["b"])
                    cur = root
                    for part in filter(None, value.split("/")):
                        if isinstance(cur, dict):
                            cur = cur.get(part)
                        elif isinstance(cur, list) and part.isdigit():
                            cur = cur[int(part)]
                        else:
                            return None
                    return cur
            # unknown kind falls back
            raise ValueError(f"Unknown token kind in '{token}'")

        cls.from_dict = from_dict
        cls._parse_placeholders = _parse_placeholders
        cls._resolve_token = _resolve_token
        cls._config_key = config_key

        assert config_key is not None and config_key != "", "config_key should not be empty."
        assert config_key not in _REGISTRY, f"config_key {config_key} already registered."
        return cls
    return decorator