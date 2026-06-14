from __future__ import annotations

import importlib
from typing import Any

from api_operator.adapters.base import Adapter
from api_operator.adapters.mock import MockAdapter
from api_operator.adapters.yaml_adapter import YamlAdapter

_BUILTIN: dict[str, type[Adapter]] = {
    "mock": MockAdapter,
    "yaml": YamlAdapter,
}

_REGISTERED: dict[str, type[Adapter]] = {}


def register_adapter(name: str, adapter_cls: type[Adapter]) -> None:
    """Register a custom adapter at runtime (e.g. from your project bootstrap)."""
    _REGISTERED[name] = adapter_cls


def import_adapter_class(reference: str) -> type[Adapter]:
    """
    Import adapter class from 'module.path:ClassName'.
    Used for adapters that live outside the core package.
    """
    if ":" not in reference:
        raise ValueError("adapter_class must be 'module.path:ClassName'")
    module_path, class_name = reference.split(":", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    if not isinstance(cls, type) or not issubclass(cls, Adapter):
        raise TypeError(f"{reference} is not an Adapter subclass")
    return cls


def available_adapters() -> list[str]:
    return sorted({*_BUILTIN.keys(), *_REGISTERED.keys()})


def load_adapter(
    name: str | None = None,
    *,
    adapter_class: str | None = None,
    config_path: str | None = None,
    **kwargs: Any,
) -> Adapter:
    if adapter_class:
        cls = import_adapter_class(adapter_class)
        return cls(**kwargs)

    if name is None:
        name = "mock"

    if name == "mock":
        return MockAdapter()

    if name == "yaml":
        if not config_path:
            raise ValueError("yaml adapter requires config_path (adapter.yaml).")
        return YamlAdapter(config_path=config_path, **kwargs)

    cls = _REGISTERED.get(name) or _BUILTIN.get(name)
    if cls is None:
        available = ", ".join(available_adapters())
        raise ValueError(
            f"Unknown adapter '{name}'. Built-in: {available}. "
            "Use --adapter yaml --config adapter.yaml or adapter_class='module:Class'."
        )
    return cls(**kwargs)  # type: ignore[call-arg]
