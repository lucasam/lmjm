import dataclasses
import decimal
import json
from collections import deque
from collections.abc import Mapping, Sequence
from typing import Any, Callable, Optional, TypeVar, Union

import desert
from marshmallow import EXCLUDE, Schema, fields, post_dump, post_load
from marshmallow.types import UnknownOption

_T = TypeVar("_T")

_SchemaArg = Optional[Union[Schema, type[Schema]]]

_SKIP_NONE_VALUES = "_pu_skip_none_values"


def _resolve_serialization_schema(obj: Any, schema: _SchemaArg) -> Schema:
    if schema:
        if isinstance(schema, type):
            return schema()
        return schema
    if dataclasses.is_dataclass(obj):
        return desert.schema(type(obj))
    else:
        raise ValueError(f"Cannot serialize object {obj} with schema {schema}")


class _DecimalEncoder(json.JSONEncoder):
    def default(self, o: object) -> object:
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super().default(o)


def serialize_to_dict_list(objs: Sequence[object], schema: _SchemaArg = None) -> list[dict[str, Any]]:
    return [serialize_to_dict(obj=obj, schema=schema) for obj in objs]


def serialize_to_dict(obj: object, schema: _SchemaArg = None) -> dict[str, Any]:
    final_schema = _resolve_serialization_schema(obj, schema)
    result: dict[str, Any] = final_schema.dump(obj)
    return result


def serialize_to_json(obj: object, schema: _SchemaArg = None) -> str:
    final_schema = _resolve_serialization_schema(obj, schema)
    result: str = final_schema.dumps(obj, cls=_DecimalEncoder)
    return result


def load_from_json(json_str: str, schema: _SchemaArg = None, parse_float: Optional[Callable[[str], Any]] = None) -> Any:
    """
    Deserialize a json based on marshmallow schema

    :param json_str:
    :param schema:
    :param parse_float:
    :return: Return type depend on Schema. Most common scenario is dict and list
    """
    if schema:
        final_schema = schema() if isinstance(schema, type) else schema
        return final_schema.loads(json_str, unknown=EXCLUDE)
    return json.loads(json_str, parse_float=parse_float)


def load_data_class_from_json(json_str: str, data_class: type[_T]) -> _T:
    final_schema = _generate_deserialization_schema(data_class)
    result: _T = final_schema.loads(json_str, unknown=EXCLUDE)
    return result


def load_data_class_from_dict(dict_object: Mapping[str, Any], data_class: type[_T]) -> _T:
    final_schema = _generate_deserialization_schema(data_class)
    result: _T = final_schema.load(dict_object, unknown=EXCLUDE)
    return result


def load_data_class_from_dict_list(dict_list: Sequence[Mapping[str, Any]], data_class: type[_T]) -> list[_T]:
    final_schema = _generate_deserialization_schema(data_class)
    result: list[_T] = final_schema.load(dict_list, many=True, unknown=EXCLUDE)
    return result


def _generate_deserialization_schema(data_class: type) -> Schema:
    schema = desert.schema(data_class)
    _set_unknown_all(schema=schema, unknown=EXCLUDE)
    return schema


def _set_unknown_all(schema: Schema, unknown: UnknownOption) -> None:
    schema.unknown = unknown

    queue = deque(schema.fields.values())
    while queue:
        field = queue.pop()
        if isinstance(field, fields.Nested):
            field.schema.unknown = unknown
            queue.extend(field.schema.fields.values())
        if isinstance(field, fields.List):
            queue.append(field.inner)
        elif isinstance(field, fields.Mapping) and field.value_field:
            queue.append(field.value_field)


def serialization_config(*, skip_none_values: bool) -> Callable[[type[_T]], type[_T]]:
    """Decorator that can be used to customize the serialization of data classes.

    To skip None values when serializing a data class, apply it like this:

        @dataclass
        @serialization_config(skip_none_values=True)
        class MyDataClass:
            ...
    """

    def wrap(cls: type[_T]) -> type[_T]:
        setattr(cls, _SKIP_NONE_VALUES, skip_none_values)
        return cls

    return wrap


def _create_base_schema(data_class: type) -> type[Schema]:
    class BaseSchema(Schema):
        @post_load
        def create_data_class_instance(self, data: Mapping[str, object], **kwargs: object) -> object:
            return data_class(**data)

        @post_dump
        def skip_none_values(self, data: Mapping[str, object], **kwargs: object) -> Mapping[str, object]:
            result: Mapping[str, object]

            # See: https://github.com/marshmallow-code/marshmallow/issues/229
            if not hasattr(data_class, _SKIP_NONE_VALUES) or getattr(data_class, _SKIP_NONE_VALUES):
                result = {key: value for key, value in data.items() if value is not None}
            else:
                result = data

            none_value_keys = [key for key, value in result.items() if value is None]
            if none_value_keys:
                none_value_keys_str = ",".join(sorted(none_value_keys))

            return result

    return BaseSchema


def _monkey_patch_desert() -> None:
    """Apply a patch that allows us to skip None values when serializing data classes.

    Right now (Apr-2023) the simplest way to add this behavior is with a monkey patch. A solution that relies only on
    public APIs is possible, but much more complex due to the way desert handles nested data classes. Accessing the
    schemas of nested data classes requires navigating schema graphs, and dealing with multiple corner cases.
    """
    import desert._make as desert_make

    base_schema_function = "_base_schema"

    if not hasattr(desert_make, base_schema_function):
        raise RuntimeError(
            f"Function {base_schema_function} not found in the {desert_make.__name__} module."
            f" Review the patch in the {__name__} module."
        )

    setattr(desert_make, base_schema_function, _create_base_schema)


_monkey_patch_desert()
