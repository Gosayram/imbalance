interface User {
	id: number;
	email: string;
}

function createUser(email: string): User {
	return { id: 1, email };
}
