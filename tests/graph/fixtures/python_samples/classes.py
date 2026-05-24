class TokenService:
	def rotate(self, token_id: int) -> bool:
		return True

	async def invalidate(self, user_id: int) -> None:
		pass

	def _private_method(self) -> str:
		return "private"


class DataProcessor:
	def __init__(self, config: dict) -> None:
		self.config = config

	def process(self, data: list) -> list:
		return [self._transform(item) for item in data]

	def _transform(self, item) -> str:
		return str(item).upper()


def helper_function(x, y) -> int:
	return x + y


async def async_helper() -> str:
	return "done"