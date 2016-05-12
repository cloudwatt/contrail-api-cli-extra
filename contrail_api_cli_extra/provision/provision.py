# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import copy
import argparse
import json
import inspect
from six import text_type
import logging
from collections import OrderedDict

from contrail_api_cli.command import Command, Arg
from contrail_api_cli.manager import CommandManager
from contrail_api_cli.exceptions import CommandNotFound, CommandError
from contrail_api_cli.utils import printo, continue_prompt


logger = logging.getLogger(__name__)


class Actions:
    SET = 'set'
    GET = 'get'
    ADD = 'add'
    DEL = 'del'
    LIST = 'list'
    APPLY = ('del', 'add', 'set')


class Provision(Command):
    description = 'Provision contrail environment'
    env_file = Arg(help='JSON file of environment to provision',
                   type=argparse.FileType('r'))
    force = Arg('-f', '--force',
                help="Don't ask for confirmation",
                default=False,
                action="store_true")

    def _get_current_env(self, keys):
        """Build the current environment of the given resources (keys).

        For each resource we run "get-resource" or "list-resource" and
        populate the env.
        """
        env = OrderedDict()
        for key in keys:
            if self._is_property(key):
                cmd = self._get_command(key, Actions.GET)
            else:
                cmd = self._get_command(key, Actions.LIST)
            try:
                env[key] = json.loads(self._call_command(cmd,
                                                         defaults=self._provision_defaults.get(key, {})))
            except CommandError as e:
                raise CommandError('Failed to get current values for %s: %s' % (key, e))
        return env

    def _is_property(self, string):
        try:
            self.mgr.get('set-%s' % string)
            return True
        except CommandNotFound:
            return False

    def _get_add_command(self, key):
        if self._is_property(key):
            action = Actions.SET
        else:
            action = Actions.ADD
        return self._get_command(key, action)

    def _get_command(self, key, action):
        try:
            return self.mgr.get('%s-%s' % (action, key))
        except CommandNotFound:
            raise CommandError("No command to %s %s" % (action, key))

    def _get_command_args(self, cmd):
        argspec = inspect.getargspec(cmd.__call__)
        if len(argspec.args) > 1:
            return [arg for arg in argspec.args[1:]]
        return []

    def _call_command(self, cmd, defaults={}):
        """Call a command.

        If the command needs arguments they have to be passed
        as a dict in the defaults kwarg.
        """
        kwargs = {}
        for arg in self._get_command_args(cmd):
            kwargs[arg] = defaults.get(arg)
        logger.debug('Calling %s with %s' % (cmd, kwargs))
        return cmd(**kwargs)

    def _normalize_env(self, env):
        """Normalize an input environement.

        Replace '-' by '_' in provisionning arg names.
        Make sure calls definitions are in lists.
        """
        for key, value in env.items():
            if type(value) == OrderedDict:
                value = dict(value.items())
            if type(value) == dict:
                env[key] = [value]
            elif type(value) != list:
                raise CommandError('Unsupported provisioning data type in %s: %s' % (key, value))
            for idx, call in enumerate(env[key]):
                env[key][idx] = self._normalize_keys(call)
        return env

    def _setup_defaults_values(self, env):
        for key, values in env.items():
            for idx, kwargs in enumerate(values):
                defaults = copy.deepcopy(self._provision_defaults.get(key, {}))
                defaults.update(kwargs)
                env[key][idx] = defaults
        return env

    def _normalize_keys(self, values):
        new_values = {}
        for key, value in values.items():
            new_values[key.replace('-', '_')] = value
        return new_values

    def _validate_env(self, env):
        """Given an env, validate that all arguments
        are consistent.
        """
        for key, values in env.items():
            for idx, call in enumerate(values):
                env[key][idx] = self._validate_call(key, call)
        return env

    def _validate_call(self, key, values):
        """Validate call parameters. The wanted env is globally structured
        as follow:

        {
            "provision": {
                "resource": [
                    {
                        "arg": "value",
                        "arg2": 34
                    }
                ],
                ...
            }
        }

        We try to get the provisioning method for "resource", which is
        "add-resource" or "set-resource". Then, given the arguments we
        validate them using the command parser and set default values
        where needed.
        """
        cmd = self._get_add_command(key)

        # default args values from argparse parser
        for action in cmd.parser._actions:
            if action.dest == 'help':
                continue
            if isinstance(action, argparse._StoreConstAction):
                values[action.dest] = values.get(action.dest, action.default)
            else:
                arg_strings = values.get(action.dest, [])
                if type(arg_strings) != list:
                    arg_strings = [arg_strings]
                try:
                    values[action.dest] = cmd.parser._get_values(action, arg_strings)
                    if not values[action.dest] and action.default:
                        values[action.dest] = action.default
                except argparse.ArgumentError as e:
                    raise CommandError('Error in %s: %s' % (key, text_type(e)))

        # remove unknown args from call
        for arg, value in copy.deepcopy(values.items()):
            if arg not in self._get_command_args(cmd):
                logger.debug('Unknown arg %s for %s. Ignored' % (arg, cmd.__call__))
                del values[arg]
        return values

    def _diff_envs(self, current, wanted):
        """Make a diff of the current env and the wanted env.

        Compare only common resources between the envs. This
        allows to partially provision the env.

        If the wanted env has a bgp-router list we try
        to converge the current env bgp-router list. Removing
        bgp-routers not in the wanted list, adding bgp-routers
        not in the current list.
        """

        diff_env = {
            Actions.SET: OrderedDict(),
            Actions.ADD: OrderedDict(),
            Actions.DEL: OrderedDict(),
        }
        for key, values in wanted.items():
            add_values = [v for v in values if v not in current.get(key, [])]
            if add_values:
                if self._is_property(key):
                    diff_env[Actions.SET][key] = add_values
                else:
                    diff_env[Actions.ADD][key] = add_values
        for key, values in current.items():
            if key not in wanted:
                continue
            if self._is_property(key):
                continue
            del_values = [v for v in values if v not in wanted[key]]
            if del_values:
                diff_env[Actions.DEL][key] = del_values
        return diff_env

    def _confirm_diff(self, diff, force=False):
        """Show actions to be made and ask for confirmation
        unless force is True.
        """
        if not any([True if diff[action] else False for action in Actions.APPLY]):
            printo('Nothing to do')
            return False

        for action in Actions.APPLY:
            if not diff[action]:
                continue
            printo("\n%s the resources :\n" % action.capitalize())
            for key, values in diff[action].items():
                printo('%s : %s\n' % (key, json.dumps(values, indent=2)))
        if force or continue_prompt():
            return True
        else:
            return False

    def _apply_diff(self, diff):
        """Takes the generated diff and call methods to
        converge to the wanted env.

        First delete unwanted resources, then set wanted
        properties, finally add wanted resources.
        """
        for action in Actions.APPLY:
            for key, values in diff.get(action, {}).items():
                cmd = self._get_command(key, action)
                for kwargs in values:
                    try:
                        self._call_command(cmd, defaults=kwargs)
                    except CommandError as e:
                        raise CommandError('Call to %s %s failed: %s' % (action, key, e))

    def __call__(self, env_file=None, force=False):
        env = json.load(env_file, object_pairs_hook=OrderedDict)

        self._provision_defaults = {}
        for key, defaults in env.get('defaults', {}).items():
            self._provision_defaults[key] = self._normalize_keys(defaults)

        self.mgr = CommandManager()
        if env.get('namespace'):
            self.mgr.load_namespace(env.get('namespace'))
            logger.debug('Namespace %s loaded' % env['namespace'])

        wanted_env = env['provision']
        wanted_env = self._normalize_env(wanted_env)
        wanted_env = self._setup_defaults_values(wanted_env)
        wanted_env = self._validate_env(wanted_env)

        current_env = self._get_current_env(wanted_env.keys())
        current_env = self._normalize_env(current_env)
        current_env = self._setup_defaults_values(current_env)
        current_env = self._validate_env(current_env)

        diff_env = self._diff_envs(current_env, wanted_env)

        if self._confirm_diff(diff_env, force=force):
            self._apply_diff(diff_env)
