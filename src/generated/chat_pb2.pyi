import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class MessageRole(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MESSAGE_ROLE_UNSPECIFIED: _ClassVar[MessageRole]
    MESSAGE_ROLE_USER: _ClassVar[MessageRole]
    MESSAGE_ROLE_ASSISTANT: _ClassVar[MessageRole]
    MESSAGE_ROLE_SYSTEM: _ClassVar[MessageRole]
    MESSAGE_ROLE_TOOL: _ClassVar[MessageRole]
MESSAGE_ROLE_UNSPECIFIED: MessageRole
MESSAGE_ROLE_USER: MessageRole
MESSAGE_ROLE_ASSISTANT: MessageRole
MESSAGE_ROLE_SYSTEM: MessageRole
MESSAGE_ROLE_TOOL: MessageRole

class Message(_message.Message):
    __slots__ = ("id", "conversation_id", "role", "content", "used_rag", "sources", "created_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    CONVERSATION_ID_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    USED_RAG_FIELD_NUMBER: _ClassVar[int]
    SOURCES_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    used_rag: bool
    sources: _containers.RepeatedScalarFieldContainer[str]
    created_at: _common_pb2.Timestamp
    def __init__(self, id: _Optional[str] = ..., conversation_id: _Optional[str] = ..., role: _Optional[_Union[MessageRole, str]] = ..., content: _Optional[str] = ..., used_rag: bool = ..., sources: _Optional[_Iterable[str]] = ..., created_at: _Optional[_Union[_common_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class Conversation(_message.Message):
    __slots__ = ("id", "user_id", "title", "created_at", "updated_at", "last_message")
    ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    LAST_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    id: str
    user_id: str
    title: str
    created_at: _common_pb2.Timestamp
    updated_at: _common_pb2.Timestamp
    last_message: Message
    def __init__(self, id: _Optional[str] = ..., user_id: _Optional[str] = ..., title: _Optional[str] = ..., created_at: _Optional[_Union[_common_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[_common_pb2.Timestamp, _Mapping]] = ..., last_message: _Optional[_Union[Message, _Mapping]] = ...) -> None: ...

class CreateConversationRequest(_message.Message):
    __slots__ = ("user_id", "title")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    title: str
    def __init__(self, user_id: _Optional[str] = ..., title: _Optional[str] = ...) -> None: ...

class CreateConversationResponse(_message.Message):
    __slots__ = ("success", "conversation", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    CONVERSATION_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    conversation: Conversation
    error: _common_pb2.Error
    def __init__(self, success: bool = ..., conversation: _Optional[_Union[Conversation, _Mapping]] = ..., error: _Optional[_Union[_common_pb2.Error, _Mapping]] = ...) -> None: ...

class ListConversationsRequest(_message.Message):
    __slots__ = ("user_id", "pagination")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    pagination: _common_pb2.PaginationRequest
    def __init__(self, user_id: _Optional[str] = ..., pagination: _Optional[_Union[_common_pb2.PaginationRequest, _Mapping]] = ...) -> None: ...

class ListConversationsResponse(_message.Message):
    __slots__ = ("success", "conversations", "pagination", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    CONVERSATIONS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    conversations: _containers.RepeatedCompositeFieldContainer[Conversation]
    pagination: _common_pb2.PaginationResponse
    error: _common_pb2.Error
    def __init__(self, success: bool = ..., conversations: _Optional[_Iterable[_Union[Conversation, _Mapping]]] = ..., pagination: _Optional[_Union[_common_pb2.PaginationResponse, _Mapping]] = ..., error: _Optional[_Union[_common_pb2.Error, _Mapping]] = ...) -> None: ...

class GetConversationRequest(_message.Message):
    __slots__ = ("conversation_id", "user_id")
    CONVERSATION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    conversation_id: str
    user_id: str
    def __init__(self, conversation_id: _Optional[str] = ..., user_id: _Optional[str] = ...) -> None: ...

class GetConversationResponse(_message.Message):
    __slots__ = ("success", "conversation", "messages", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    CONVERSATION_FIELD_NUMBER: _ClassVar[int]
    MESSAGES_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    conversation: Conversation
    messages: _containers.RepeatedCompositeFieldContainer[Message]
    error: _common_pb2.Error
    def __init__(self, success: bool = ..., conversation: _Optional[_Union[Conversation, _Mapping]] = ..., messages: _Optional[_Iterable[_Union[Message, _Mapping]]] = ..., error: _Optional[_Union[_common_pb2.Error, _Mapping]] = ...) -> None: ...

class DeleteConversationRequest(_message.Message):
    __slots__ = ("conversation_id", "user_id")
    CONVERSATION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    conversation_id: str
    user_id: str
    def __init__(self, conversation_id: _Optional[str] = ..., user_id: _Optional[str] = ...) -> None: ...

class DeleteConversationResponse(_message.Message):
    __slots__ = ("success", "message", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    error: _common_pb2.Error
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., error: _Optional[_Union[_common_pb2.Error, _Mapping]] = ...) -> None: ...

class SendMessageRequest(_message.Message):
    __slots__ = ("conversation_id", "user_id", "content")
    CONVERSATION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    conversation_id: str
    user_id: str
    content: str
    def __init__(self, conversation_id: _Optional[str] = ..., user_id: _Optional[str] = ..., content: _Optional[str] = ...) -> None: ...

class SendMessageResponse(_message.Message):
    __slots__ = ("chunk_type", "token", "message", "used_rag", "error")
    class ChunkType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        CHUNK_TYPE_UNSPECIFIED: _ClassVar[SendMessageResponse.ChunkType]
        CHUNK_TYPE_TOKEN: _ClassVar[SendMessageResponse.ChunkType]
        CHUNK_TYPE_RAG_START: _ClassVar[SendMessageResponse.ChunkType]
        CHUNK_TYPE_RAG_DONE: _ClassVar[SendMessageResponse.ChunkType]
        CHUNK_TYPE_DONE: _ClassVar[SendMessageResponse.ChunkType]
        CHUNK_TYPE_ERROR: _ClassVar[SendMessageResponse.ChunkType]
    CHUNK_TYPE_UNSPECIFIED: SendMessageResponse.ChunkType
    CHUNK_TYPE_TOKEN: SendMessageResponse.ChunkType
    CHUNK_TYPE_RAG_START: SendMessageResponse.ChunkType
    CHUNK_TYPE_RAG_DONE: SendMessageResponse.ChunkType
    CHUNK_TYPE_DONE: SendMessageResponse.ChunkType
    CHUNK_TYPE_ERROR: SendMessageResponse.ChunkType
    CHUNK_TYPE_FIELD_NUMBER: _ClassVar[int]
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    USED_RAG_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    chunk_type: SendMessageResponse.ChunkType
    token: str
    message: Message
    used_rag: bool
    error: _common_pb2.Error
    def __init__(self, chunk_type: _Optional[_Union[SendMessageResponse.ChunkType, str]] = ..., token: _Optional[str] = ..., message: _Optional[_Union[Message, _Mapping]] = ..., used_rag: bool = ..., error: _Optional[_Union[_common_pb2.Error, _Mapping]] = ...) -> None: ...

class GetMessagesRequest(_message.Message):
    __slots__ = ("conversation_id", "user_id", "pagination")
    CONVERSATION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    conversation_id: str
    user_id: str
    pagination: _common_pb2.PaginationRequest
    def __init__(self, conversation_id: _Optional[str] = ..., user_id: _Optional[str] = ..., pagination: _Optional[_Union[_common_pb2.PaginationRequest, _Mapping]] = ...) -> None: ...

class GetMessagesResponse(_message.Message):
    __slots__ = ("success", "messages", "pagination", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGES_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    messages: _containers.RepeatedCompositeFieldContainer[Message]
    pagination: _common_pb2.PaginationResponse
    error: _common_pb2.Error
    def __init__(self, success: bool = ..., messages: _Optional[_Iterable[_Union[Message, _Mapping]]] = ..., pagination: _Optional[_Union[_common_pb2.PaginationResponse, _Mapping]] = ..., error: _Optional[_Union[_common_pb2.Error, _Mapping]] = ...) -> None: ...
