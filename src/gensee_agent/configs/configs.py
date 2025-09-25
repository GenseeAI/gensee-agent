from dataclasses import dataclass, MISSING
from typing import Self, dataclass_transform

_REGISTRY: dict[str, type] = {}

class BaseConfig:
    config_key: str  # This will be set by the decorator.

    @classmethod
    def from_dict(cls, config: dict) -> Self:
        raise NotImplementedError("This method is defined in the @dataclass_transform decorator and BaseConfig should not be used without the decorator.")

    def pretty_print(self):
        """
        Print the parsed value, also print if the values are different from the default values.
        """
        print(f"Configuration for {self.config_key}:")
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

        @classmethod
        def from_dict(cls, config: dict):
            # TODO: Need potential customization here, for example, to ignore unknown fields.
            # fields = {f.name for f in c.__dataclass_fields__.values()}  # type: ignore[attr-defined]
            # return c(**{k: d[k] for k in d if k in fields})
            selected_config = config.get(config_key, {})
            return cls(**selected_config)
        cls.from_dict = from_dict
        cls.config_key = config_key

        assert config_key is not None and config_key != "", "config_key should not be empty."
        assert config_key not in _REGISTRY, f"config_key {config_key} already registered."
        return cls
    return decorator
