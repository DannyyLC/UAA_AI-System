import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class JobStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    JOB_STATUS_UNSPECIFIED: _ClassVar[JobStatus]
    JOB_STATUS_PENDING: _ClassVar[JobStatus]
    JOB_STATUS_PROCESSING: _ClassVar[JobStatus]
    JOB_STATUS_COMPLETED: _ClassVar[JobStatus]
    JOB_STATUS_FAILED: _ClassVar[JobStatus]
    JOB_STATUS_CANCELLED: _ClassVar[JobStatus]
JOB_STATUS_UNSPECIFIED: JobStatus
JOB_STATUS_PENDING: JobStatus
JOB_STATUS_PROCESSING: JobStatus
JOB_STATUS_COMPLETED: JobStatus
JOB_STATUS_FAILED: JobStatus
JOB_STATUS_CANCELLED: JobStatus

class SubmitDocumentRequest(_message.Message):
    __slots__ = ("user_id", "filename", "file_path", "mime_type", "topic", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    FILE_PATH_FIELD_NUMBER: _ClassVar[int]
    MIME_TYPE_FIELD_NUMBER: _ClassVar[int]
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    filename: str
    file_path: str
    mime_type: str
    topic: str
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, user_id: _Optional[str] = ..., filename: _Optional[str] = ..., file_path: _Optional[str] = ..., mime_type: _Optional[str] = ..., topic: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class SubmitDocumentResponse(_message.Message):
    __slots__ = ("success", "job_id", "status", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    job_id: str
    status: JobStatus
    error: _common_pb2.Error
    def __init__(self, success: bool = ..., job_id: _Optional[str] = ..., status: _Optional[_Union[JobStatus, str]] = ..., error: _Optional[_Union[_common_pb2.Error, _Mapping]] = ...) -> None: ...

class GetJobStatusRequest(_message.Message):
    __slots__ = ("job_id",)
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    def __init__(self, job_id: _Optional[str] = ...) -> None: ...

class GetJobStatusResponse(_message.Message):
    __slots__ = ("success", "job_id", "status", "filename", "topic", "chunks_created", "error_message", "created_at", "updated_at", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_CREATED_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    job_id: str
    status: JobStatus
    filename: str
    topic: str
    chunks_created: int
    error_message: str
    created_at: _common_pb2.Timestamp
    updated_at: _common_pb2.Timestamp
    error: _common_pb2.Error
    def __init__(self, success: bool = ..., job_id: _Optional[str] = ..., status: _Optional[_Union[JobStatus, str]] = ..., filename: _Optional[str] = ..., topic: _Optional[str] = ..., chunks_created: _Optional[int] = ..., error_message: _Optional[str] = ..., created_at: _Optional[_Union[_common_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[_common_pb2.Timestamp, _Mapping]] = ..., error: _Optional[_Union[_common_pb2.Error, _Mapping]] = ...) -> None: ...

class ListJobsRequest(_message.Message):
    __slots__ = ("user_id", "status", "pagination")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    status: JobStatus
    pagination: _common_pb2.PaginationRequest
    def __init__(self, user_id: _Optional[str] = ..., status: _Optional[_Union[JobStatus, str]] = ..., pagination: _Optional[_Union[_common_pb2.PaginationRequest, _Mapping]] = ...) -> None: ...

class JobSummary(_message.Message):
    __slots__ = ("job_id", "filename", "topic", "status", "chunks_created", "error_message", "created_at", "updated_at")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_CREATED_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    filename: str
    topic: str
    status: JobStatus
    chunks_created: int
    error_message: str
    created_at: _common_pb2.Timestamp
    updated_at: _common_pb2.Timestamp
    def __init__(self, job_id: _Optional[str] = ..., filename: _Optional[str] = ..., topic: _Optional[str] = ..., status: _Optional[_Union[JobStatus, str]] = ..., chunks_created: _Optional[int] = ..., error_message: _Optional[str] = ..., created_at: _Optional[_Union[_common_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[_common_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class ListJobsResponse(_message.Message):
    __slots__ = ("success", "jobs", "pagination", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    JOBS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    jobs: _containers.RepeatedCompositeFieldContainer[JobSummary]
    pagination: _common_pb2.PaginationResponse
    error: _common_pb2.Error
    def __init__(self, success: bool = ..., jobs: _Optional[_Iterable[_Union[JobSummary, _Mapping]]] = ..., pagination: _Optional[_Union[_common_pb2.PaginationResponse, _Mapping]] = ..., error: _Optional[_Union[_common_pb2.Error, _Mapping]] = ...) -> None: ...

class CancelJobRequest(_message.Message):
    __slots__ = ("job_id", "user_id")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    user_id: str
    def __init__(self, job_id: _Optional[str] = ..., user_id: _Optional[str] = ...) -> None: ...

class CancelJobResponse(_message.Message):
    __slots__ = ("success", "message", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    error: _common_pb2.Error
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., error: _Optional[_Union[_common_pb2.Error, _Mapping]] = ...) -> None: ...

class ListCollectionsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListCollectionsResponse(_message.Message):
    __slots__ = ("success", "collections", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    COLLECTIONS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    collections: _containers.RepeatedCompositeFieldContainer[CollectionInfo]
    error: _common_pb2.Error
    def __init__(self, success: bool = ..., collections: _Optional[_Iterable[_Union[CollectionInfo, _Mapping]]] = ..., error: _Optional[_Union[_common_pb2.Error, _Mapping]] = ...) -> None: ...

class CollectionInfo(_message.Message):
    __slots__ = ("name", "vectors_count", "topic")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VECTORS_COUNT_FIELD_NUMBER: _ClassVar[int]
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    name: str
    vectors_count: int
    topic: str
    def __init__(self, name: _Optional[str] = ..., vectors_count: _Optional[int] = ..., topic: _Optional[str] = ...) -> None: ...

class ListSourcesRequest(_message.Message):
    __slots__ = ("user_id", "topic")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    topic: str
    def __init__(self, user_id: _Optional[str] = ..., topic: _Optional[str] = ...) -> None: ...

class SourceInfo(_message.Message):
    __slots__ = ("source", "topic", "chunks_count", "indexed_at")
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_COUNT_FIELD_NUMBER: _ClassVar[int]
    INDEXED_AT_FIELD_NUMBER: _ClassVar[int]
    source: str
    topic: str
    chunks_count: int
    indexed_at: _common_pb2.Timestamp
    def __init__(self, source: _Optional[str] = ..., topic: _Optional[str] = ..., chunks_count: _Optional[int] = ..., indexed_at: _Optional[_Union[_common_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class ListSourcesResponse(_message.Message):
    __slots__ = ("success", "sources", "total", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    SOURCES_FIELD_NUMBER: _ClassVar[int]
    TOTAL_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    sources: _containers.RepeatedCompositeFieldContainer[SourceInfo]
    total: int
    error: _common_pb2.Error
    def __init__(self, success: bool = ..., sources: _Optional[_Iterable[_Union[SourceInfo, _Mapping]]] = ..., total: _Optional[int] = ..., error: _Optional[_Union[_common_pb2.Error, _Mapping]] = ...) -> None: ...

class DeleteSourceRequest(_message.Message):
    __slots__ = ("user_id", "source", "topic")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    source: str
    topic: str
    def __init__(self, user_id: _Optional[str] = ..., source: _Optional[str] = ..., topic: _Optional[str] = ...) -> None: ...

class DeleteSourceResponse(_message.Message):
    __slots__ = ("success", "chunks_deleted", "message", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_DELETED_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    chunks_deleted: int
    message: str
    error: _common_pb2.Error
    def __init__(self, success: bool = ..., chunks_deleted: _Optional[int] = ..., message: _Optional[str] = ..., error: _Optional[_Union[_common_pb2.Error, _Mapping]] = ...) -> None: ...
