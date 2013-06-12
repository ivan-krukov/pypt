from setuptools import setup
setup(name='pypt',
	version='0.1',
	description="A simple tool to manage your data workflow",
	author="Ivan Kryukov",
	license="WTFUW",
	scripts = {"pypt=py-make:main"},
	py_modules=['pypt'],
)
