from typing import Protocol


class OllamaInterface(Protocol):
    """
    OllamaInterface is a protocol that defines the methods for interacting with the Ollama API.
    This interface is used to send messages to the Ollama API and receive responses.
    """

    def send_message(self, message: str) -> dict:
        """
        Send a message to the Ollama API and return the response.

        Args:
            message (str): The message to send to the Ollama API.

        Returns:
            dict: The response from the Ollama API.
        """
        pass



class DSPYInterface(Protocol):
    """
    DSPYInterface is a protocol that defines the methods for interacting with the DSPY API.
    This interface is used to send messages to the DSPY API and receive responses.
    """

    def send_message(self, message: str) -> dict:
        """
        Send a message to the DSPY API and return the response.

        Args:
            message (str): The message to send to the DSPY API.

        Returns:
            dict: The response from the DSPY API.
        """
        pass


# tonight you neeed to set up the following things, you have to set up the capacity to test the following 


