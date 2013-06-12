#!/usr/bin/env python

from string import Template
from pynt import task
import os
import inspect

def render(string,variables=None):
	"""Wrapper method for String Template:
		name="Jeff"
		render("Hello, $name")
		>>Hello, Jeff
	You can also pass a dictionary of values to be applied instead of defining them in the namespace"""
	t = Template(string)
	if not variables:
		frame = inspect.currentframe()
		if frame == None:
			raise Exception ("Looks like the current python interpreter does not have stack frame support. Maybe it's a good thing. Try invoking render(\"STRING\",vars()) to reference caller namespace")
		try:
			variables = frame.f_back.f_locals
		finally:
			del frame
	return t.substitute(variables)
