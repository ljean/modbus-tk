# -*- coding: utf-8 -*-
"""
This script detects the modified files thanks to 'git status' command

"""
from __future__ import print_function

import imp
import os.path
import re
import subprocess
import sys


class CommandWrapper(object):
    """Base class to run command"""

    def _run_command(self, command_line):
        """run a command"""
        try:
            return subprocess.check_output(command_line.split(' ')), 0
        except subprocess.CalledProcessError, ex:
            return ex.output, ex.returncode


class Git(CommandWrapper):
    """Wrapper to git commands sent thanks to subprocess"""

    def __init__(self):
        self._root = self.get_root()

    def get_root(self):
        """get Git root directory"""
        output, error_code = self._run_command('git rev-parse --show-toplevel')
        if error_code:
            raise Exception("Git.get_root failed: Error {0}".format(error_code))
        return output.strip()


    def get_all_files(self):
        """
        returns a list of modified files by running a git status command
        """
        output, error_code = self._run_command('git ls-tree -r master --name-only')
        if error_code:
            raise Exception("Git.get_all_files failed: Error {0}".format(error_code))
        lines = [l.strip() for l in output.split("\n")]
        return [os.path.join(self._root, f) for f in sorted(lines)]

    def get_changes(self):
        """
        returns a list of modified files by running a git status command
        """
        output, error_code = self._run_command('git status')
        if error_code:
            raise Exception("Git.get_changes failed: Error {0}".format(error_code))

        lines = [l.strip() for l in output.split("\n")]

        files = set()

        for line in lines:

            prefixes = ("new file:", "modified:")

            for prefix in prefixes:
                regex = "{0}(?P<filename>.*)".format(prefix)
                filename_group = re.match(regex, line)
                if filename_group:
                    filename = filename_group.group("filename").strip()
                    files.add(filename)

        return [os.path.join(self._root, f) for f in sorted(files)]


class Pylint(CommandWrapper):
    """Wrapper to pylint commands sent thanks to subprocess"""

    def __init__(self, show_all_result=False, verbose=False):

        self.show_all_result = show_all_result
        self.verbose = verbose

        self.extra_commands = []

        try:
            imp.find_module('pylint')
            self.pylint_error = ""
        except ImportError:
            self.pylint_error = "pylint is not installed. Run 'pip install pylint'"

        try:
            imp.find_module('pylint_django')
            found = True
        except ImportError:
            found = False
        if found:
            self.extra_commands.append("--load-plugins pylint_django")

        try:
            imp.find_module('django')
            self.is_django = True
        except ImportError:
            self.is_django = False

        if os.path.exists(".pylintrc"):
            self.extra_commands.append("--rcfile={0}".format(".pylintrc"))

    def is_ready(self):
        """returns True if pylint is installed"""
        if self.pylint_error:
            print(self.pylint_error)
            return False
        else:
            return True

    def display_results(self, output):
        """show the results"""
        if self.verbose:
            print(output)
        else:
            lines = output.split("\n")
            for line in lines:
                if line.find("****") == 0:
                    print(line)
                else:
                    if re.match(r'\w:.*', line):
                        print(line)

    def is_file_to_analyze(self, filename):
        """Returns False if the file must be ignored"""
        if ".py" != os.path.splitext(filename)[1]:
            return False

        regexes_to_ignore = []
        if self.is_django:
            regexes_to_ignore.extend([
                '.*/migrations/.*',
                '.*/urls.py',
                '.*/tests.py',
            ])
        for regex_to_ignore in regexes_to_ignore:
            if re.match(regex_to_ignore, filename):
                return False
        return True


    def analyze_file(self, filename):
        """run pylint analyses"""

        if self.is_file_to_analyze(filename):

            command_line = "pylint {0}".format(filename)
            if self.extra_commands:
                command_line += " "+" ".join(self.extra_commands)

            output, error_code = self._run_command(command_line)
            if error_code:
                self.display_results(output)
            else:
                if self.show_all_result:
                    print('OK   >', filename)

        elif self.show_all_result:
            print('Skip >', filename)


def main():
    """main"""

    analyze_all = ("all" in sys.argv)
    show_all_result = ("show_all" in sys.argv)
    verbose = ("verbose" in sys.argv)

    pylint = Pylint(show_all_result=show_all_result, verbose=verbose)
    if pylint.is_ready():
        git = Git()
        if analyze_all:
            files = git.get_all_files()
        else:
            files = git.get_changes()

        for filename in files:
            pylint.analyze_file(filename)


if __name__ == "__main__":
    main()
