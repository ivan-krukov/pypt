"""
Forked from PYNT - Lightweight Python Build Tool

"""

import inspect
import argparse
import logging
import os
from os import path
import re
import imp
import sys

_LOGGING_FORMAT = ">>[py-make] %(name)s : %(message)s"
#_TASK_PATTERN = re.compile("^([^\[]+)(\[([^\]]*)\])?$")
#"^([^\[]+)(\[([^\],=]*(,[^\],=]+)*(,[^\],=]+=[^\],=]+)*)\])?$"
def build(args,module=None):
	"""
	Build the specified module with specified arguments.
	
	@type module: module
	@type args: list of arguments
	"""
	# Build the command line.
	parser = _create_parser()

	#No args passed. 
	if not args: #todo: execute default task.
		parser.print_help()
		exit
	# Parse arguments.
	args = parser.parse_args(args)

	#load build file as a module
	if not module:
		if not path.isfile(args.file):
			raise Exception("Build file '%s' does not exist" % args.file) 
		module = imp.load_source(
				path.splitext(
					path.basename(args.file))[0],args.file)
	
	# Run task and all it's dependencies.
	if args.list_tasks:
		_print_tasks(module)
		#TODO: rename all calls to singular
	elif not args.tasks:
		parser.print_help()
		print("\n")
		_print_tasks(module)
	else:
		_run_by_task_name(module,args.tasks)

def _tasks_description(module):
	# Get all tasks.
	tasks = _get_tasks(module)
	task_list = []
	# Build task_list to describe the tasks.
	name_width = _get_max_name_length(module)+4
	param_width = _get_max_param_length(module)+4
	task_help_format = "\n  {0:<%s} {1:<%s} {2}" %(name_width,param_width)
	for task in tasks:
		task_list.append(task_help_format.format(task.name, task.params, task.doc))
	return ("".join(task_list))

def _run_by_task_name(module,task_name):
	"""
	@type module: module
	@type task_name: string
	@param task_name: Task name, exactly corresponds to function name.
	"""

	# Create logger.
	logger = _get_logger(module)

	completed_tasks = set([])
	#for task_name in task_names:
	task, args, kwargs= _get_task(module,task_name)
	_run(module, logger, task, completed_tasks, True, args, kwargs)

def _get_task(module, name):
	# Get all tasks.
	#match = _TASK_PATTERN.match(name)
	#if not match:
	#	raise Exception("Invalid task argument %s" % name)
	#task_name, _, args_str = match.groups()
	task_name = name[0]
	args = name[1:]
	tasks = _get_tasks(module)
	args, kwargs= _parse_args(args)

	if hasattr(module, task_name):
		return getattr(module, task_name), args, kwargs
	matching_tasks = [task for task in tasks if task.name.startswith(task_name)]
		
	if not matching_tasks:
		raise Exception("Invalid task '%s'. Task should be one of %s" %
						(name, 
						 ', '.join([task.name for task in tasks])))
	if len(matching_tasks) == 1:
		return matching_tasks[0], args, kwargs
	raise Exception("Conflicting matches %s for task %s " % (
		', '.join([task.name for task in matching_tasks]), task_name
	))

def _parse_args(arg_parts):
	args = []
	kwargs = {}
	if not arg_parts:
		return args, kwargs

	for i, part in enumerate(arg_parts):
		if "=" in part:
			key, value = [_str.strip() for _str in part.split("=")]
			if key in kwargs:
				raise Exception("duplicate keyword argument %s" % part)
			kwargs[key] = value
		else:
			if len(kwargs) > 0:
				raise Exception("Non keyword arg %s cannot follows a keyword arg %s"
								% (part, arg_parts[i - 1]))
			args.append(part.strip())
	return args, kwargs
	
def _run(module, logger, task, completed_tasks, from_command_line = False, args = None, kwargs = None):
	"""
	@type module: module
	@type logging: Logger
	@type task: Task
	@type completed_tasts: set Task
	@rtype: set Task
	@return: Updated set of completed tasks after satisfying all dependancies.
	"""

	# Satsify dependancies recursively. Maintain set of completed tasks so each
	# task is only performed once.
	for dependancy in task.dependancies:
		completed_tasks = _run(module,logger,dependancy,completed_tasks)

	# Perform current task, if need to.
	if from_command_line or task not in completed_tasks:

		logger.info("Starting task \"%s\"" % task.name)

		try:
			# Run task.
			task(*(args or []),**(kwargs or {}))
		except:
			logger.critical("Error in task \"%s\"" % task.name)
			logger.critical("Aborting build")
			raise
		
		logger.info("Completed task \"%s\"" % task.name)
		
		completed_tasks.add(task)
	
	return completed_tasks

		
def task(*dependencies, **options):
	#validate the dependency list
	for i, dependency in enumerate(dependencies):
		if not Task.is_task(dependency):
				if inspect.isfunction(dependency):
					# Throw error specific to the most likely form of misuse.
					if i == 0:
						raise Exception("Replace use of @task with @task().")
					else:
						raise Exception("%s is not a task. Each dependancy should be a task." % dependency)
				else:
					raise Exception("%s is not a task." % dependency)

	def decorator(fn):
		return Task(fn, dependencies, options)
	return decorator

class Task(object):
	
	def __init__(self, func, dependancies, options):
		"""
		@type func: 0-ary function
		@type dependancies: list of Task objects
		"""
		self.func = func
		self.name = func.__name__
		self.doc = inspect.getdoc(func) or ''
		self.params = inspect.formatargspec(*inspect.getfullargspec(func))
		self.dependancies = dependancies
		
	def __call__(self,*args,**kwargs):
		self.func.__call__(*args,**kwargs)
	
	@classmethod
	def is_task(cls,obj):
		"""
		Returns true is an object is a build task.
		"""
		return isinstance(obj,cls)

def _get_tasks(module):
	"""
	Returns all functions marked as tasks.
	
	@type module: module
	"""
	# Get all functions that are marked as task and pull out the task object
	# from each (name,value) pair.
	return [member[1] for member in inspect.getmembers(module,Task.is_task)]
	
def _get_max_name_length(module):
	"""
	Returns the length of the longest task name.
	
	@type module: module
	"""
	return max([len(task.name) for task in _get_tasks(module)])

def _get_max_param_length(module):
	"""
	Returns the length of the longest task parameter string.
	
	@type module: module
	"""
	return max([len(task.params) for task in _get_tasks(module)])
	
def _get_logger(module):
	"""
	@type module: module
	@rtype: logging.Logger
	"""

	# Create Logger
	logger = logging.getLogger(os.path.basename(module.__file__))
	logger.setLevel(logging.DEBUG)

	# Create console handler and set level to debug
	ch = logging.StreamHandler()
	ch.setLevel(logging.DEBUG)

	# Create formatter
	formatter = logging.Formatter(_LOGGING_FORMAT)

	# Add formatter to ch
	ch.setFormatter(formatter)

	# Add ch to logger
	logger.addHandler(ch)

	return logger
