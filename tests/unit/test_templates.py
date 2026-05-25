import pytest
from imbalance.core.templates import generate_claude_md, generate_agents_md


def test_generate_claude_md_python_backend():
	result = generate_claude_md('python-backend', 'TestProject')
	assert 'TestProject' in result
	assert 'Python' in result


def test_generate_claude_md_frontend():
	result = generate_claude_md('frontend-react', 'MyApp')
	assert 'MyApp' in result
	assert 'React' in result


def test_generate_claude_md_devops():
	result = generate_claude_md('devops', 'InfraProject')
	assert 'InfraProject' in result
	assert 'Terraform' in result


def test_generate_claude_md_data_science():
	result = generate_claude_md('data-science', 'DataProject')
	assert 'DataProject' in result


def test_generate_claude_md_invalid():
	with pytest.raises(ValueError):
		generate_claude_md('invalid-template', 'Test')


def test_generate_agents_md():
	result = generate_agents_md('TestAgentProject')
	assert 'TestAgentProject' in result
	assert 'Memory Protocol' in result