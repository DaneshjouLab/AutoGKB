"""messaging.py

    This module contains the messaging datatype for sending informationn to llms, will need to rename when I add more types of messages
    

    # TODO: Define the messaging protocol
    - describe the scenarios in which you send messages. 
    - you also have the ability to send the information directly to dspy, and let that handle it, 
    - 
    structure of the message should be a json message repsonse 


 """



from typing import Protocol

class messageHandler(Protocol):
    """

    Ok so walk me through how this will work, this is something that shouldn,t 
    so we have some content which is a message, then we have the actual content, 
    for dspy we have signatures and handlers, which are actually compose

    Args:
        Protocol (_type_): _description_
    """

class Message(Protocol):
    """
    this class is supposed to create the messaging protocol and then communicate form ti, 

    Messages should be component that r
    """
    def __init__(self, content: str) -> None:
        self.content = content
    def send(arg1:dict)-> dict:
        "something"

