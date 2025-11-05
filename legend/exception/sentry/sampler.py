import random

from idp.framework.core.config import exception_settings
from idp.framework.exception.metadata import ExceptionCategory


class ExceptionSampler:
    def __init__(self):
        self.settings = exception_settings

    def get_exception_sample_rate(self, category: ExceptionCategory) -> float:
        return getattr(self.settings, f"EXCEPTION_SAMPLE_RATE_{category.name}")

    def should_report(self, category: ExceptionCategory) -> bool:
        rate = self.get_exception_sample_rate(category)
        return random.random() <= rate
