from abc import ABC, abstractmethod

from meridian.application.dto.update_info import ReleaseInfo


class ReleaseSource(ABC):
    @abstractmethod
    def latest_release(self) -> ReleaseInfo | None: ...
