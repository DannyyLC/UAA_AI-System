import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SearchRequest(_message.Message):
    __slots__ = ("query", "user_id", "topic", "top_k", "threshold", "metadata")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    TOP_K_FIELD_NUMBER: _ClassVar[int]
    THRESHOLD_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    query: str
    user_id: str
    topic: str
    top_k: int
    threshold: float
    metadata: _common_pb2.RequestMetadata
    def __init__(self, query: _Optional[str] = ..., user_id: _Optional[str] = ..., topic: _Optional[str] = ..., top_k: _Optional[int] = ..., threshold: _Optional[float] = ..., metadata: _Optional[_Union[_common_pb2.RequestMetadata, _Mapping]] = ...) -> None: ...

class SearchResult(_message.Message):
    __slots__ = ("document_id", "chunk_id", "content", "score", "source", "topic", "page", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    CHUNK_ID_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    PAGE_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    chunk_id: str
    content: str
    score: float
    source: str
    topic: str
    page: int
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, document_id: _Optional[str] = ..., chunk_id: _Optional[str] = ..., content: _Optional[str] = ..., score: _Optional[float] = ..., source: _Optional[str] = ..., topic: _Optional[str] = ..., page: _Optional[int] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class SearchResponse(_message.Message):
    __slots__ = ("success", "results", "context", "total", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    TOTAL_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    results: _containers.RepeatedCompositeFieldContainer[SearchResult]
    context: str
    total: int
    error: _common_pb2.Error
    def __init__(self, success: bool = ..., results: _Optional[_Iterable[_Union[SearchResult, _Mapping]]] = ..., context: _Optional[str] = ..., total: _Optional[int] = ..., error: _Optional[_Union[_common_pb2.Error, _Mapping]] = ...) -> None: ...

class ClassifyRequest(_message.Message):
    __slots__ = ("query",)
    QUERY_FIELD_NUMBER: _ClassVar[int]
    query: str
    def __init__(self, query: _Optional[str] = ...) -> None: ...

class ClassifyResponse(_message.Message):
    __slots__ = ("success", "topic", "topics", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    TOPICS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    topic: str
    topics: _containers.RepeatedCompositeFieldContainer[TopicScore]
    error: _common_pb2.Error
    def __init__(self, success: bool = ..., topic: _Optional[str] = ..., topics: _Optional[_Iterable[_Union[TopicScore, _Mapping]]] = ..., error: _Optional[_Union[_common_pb2.Error, _Mapping]] = ...) -> None: ...

class TopicScore(_message.Message):
    __slots__ = ("topic", "score")
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    topic: str
    score: float
    def __init__(self, topic: _Optional[str] = ..., score: _Optional[float] = ...) -> None: ...

class HealthCheckRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class HealthCheckResponse(_message.Message):
    __slots__ = ("healthy", "qdrant_connected", "collections_count", "collections")
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    QDRANT_CONNECTED_FIELD_NUMBER: _ClassVar[int]
    COLLECTIONS_COUNT_FIELD_NUMBER: _ClassVar[int]
    COLLECTIONS_FIELD_NUMBER: _ClassVar[int]
    healthy: bool
    qdrant_connected: bool
    collections_count: int
    collections: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, healthy: bool = ..., qdrant_connected: bool = ..., collections_count: _Optional[int] = ..., collections: _Optional[_Iterable[str]] = ...) -> None: ...
