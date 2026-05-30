import functools


def log_calls(func):
	@functools.wraps(func)
	def wrapper(*args, **kwargs):
		return func(*args, **kwargs)
	return wrapper


@log_calls
def compute(x: int) -> int:
	return x * 2


class Service:
	@staticmethod
	def static_helper() -> None:
		pass

	@classmethod
	def create(cls) -> "Service":
		return cls()
