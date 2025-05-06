"""
test_messaging.py

Purpose of this file is to test 
"""


import pytest 
from src.agents.messaging import Messaging


# 

def test_init():
    messaging = Messaging()
    assert isinstance(messaging, Messaging)

def test_send_message():
    messaging = Messaging()
    message = "Hello, World!"
    result = messaging.send_message(message)
    assert isinstance(result, dict)
    assert 'message' in result and result['message'] == message

def test_receive_message():
    # This would depend on how you're implementing the receive end
    # For example:
    class MockReceiver:
        def __init__(self):
            self.messages = []

        def receive(self, message):
            self.messages.append(message)
            return True

    receiver = MockReceiver()
    messaging = Messaging()
    result = messaging.receive_message(receiver)
    assert isinstance(result, bool)  # Returns True if message 

    assert len(receiver.messages) == 1 





if __name__ == "__main__":
    pytest.main()