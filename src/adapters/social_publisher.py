from abc import ABC, abstractmethod

class SocialPublisher(ABC):
    @abstractmethod
    def publish(self, variant: dict) -> dict:
        raise NotImplementedError