function identity<T>(value: T): T {
	return value;
}

class Box<T> {
	constructor(private value: T) {}
	getValue(): T {
		return this.value;
	}
}
