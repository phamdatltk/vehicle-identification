from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Image(_message.Message):
    __slots__ = ("data", "metadata")
    DATA_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    data: bytes
    metadata: bytes
    def __init__(self, data: _Optional[bytes] = ..., metadata: _Optional[bytes] = ...) -> None: ...

class Box(_message.Message):
    __slots__ = ("x0", "y0", "x1", "y1", "id")
    X0_FIELD_NUMBER: _ClassVar[int]
    Y0_FIELD_NUMBER: _ClassVar[int]
    X1_FIELD_NUMBER: _ClassVar[int]
    Y1_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    x0: float
    y0: float
    x1: float
    y1: float
    id: str
    def __init__(self, x0: _Optional[float] = ..., y0: _Optional[float] = ..., x1: _Optional[float] = ..., y1: _Optional[float] = ..., id: _Optional[str] = ...) -> None: ...

class DetectResult(_message.Message):
    __slots__ = ("boxes",)
    BOXES_FIELD_NUMBER: _ClassVar[int]
    boxes: _containers.RepeatedCompositeFieldContainer[Box]
    def __init__(self, boxes: _Optional[_Iterable[_Union[Box, _Mapping]]] = ...) -> None: ...

class OcrResult(_message.Message):
    __slots__ = ("text",)
    TEXT_FIELD_NUMBER: _ClassVar[int]
    text: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, text: _Optional[_Iterable[str]] = ...) -> None: ...

class ImgColorsResult(_message.Message):
    __slots__ = ("text",)
    TEXT_FIELD_NUMBER: _ClassVar[int]
    text: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, text: _Optional[_Iterable[str]] = ...) -> None: ...

class VehicleIdentifyResult(_message.Message):
    __slots__ = ("vehicles",)
    VEHICLES_FIELD_NUMBER: _ClassVar[int]
    vehicles: _containers.RepeatedCompositeFieldContainer[Box]
    def __init__(self, vehicles: _Optional[_Iterable[_Union[Box, _Mapping]]] = ...) -> None: ...
