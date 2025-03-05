from typing import TypedDict, Annotated
from langchain_core.messages import AnyMessage 
import operator

class State(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    investigation: bool # Bandera la cual indicara si el usuarrio esta dispuesto a hacer una investigacion