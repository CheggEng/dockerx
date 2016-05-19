import os
import re
import subprocess
from sys import stdout
from uuid import uuid4

docker_connect = False


# Register new annotation for cusom docker commands from extras.py file
def createAnnotation():
    functions = {}

    def registrar(func):
        functions[func.__name__.upper()] = func
        return func

    registrar.all = functions
    return registrar


docker = createAnnotation()
retry = createAnnotation()


# Used to display log lines immediately by flushing STDOUT
def log(text):
    print text
    stdout.flush()


# Constants
class Constants:
    RUNTIME = "###RUNTIME###"

    class Shell:
        SCRIPT_HEAD = '#!/usr/bin/env bash\n\n'
        FAIL_ON_ERROR = 'set -e\n'

    class Docker:
        BASE_DOCKER_FILE_NAME = "Dockerfile"
        STATIC_DOCKER_FILE_NAME = "df.c"
        RUNTIME_DOCKER_FILE_NAME = "df.sh"

        BUILD = "docker build "
        CREATE = "docker create "
        RUN = "docker start -a {0}"
        COMMIT = "docker commit "
        EXPORT = "docker export {container_id} > {container_id}.tar.gz"
        IMPORT = "docker import "
        REMOVE_CONTAINER = "docker rm {0}"
        REMOVE_IMAGE = "docker rmi {0}"

        class Dockerfile:
            ADD_RUNTIME_SCRIPT_COMMAND = 'ADD df.sh /{0}.sh\nRUN chmod 777 /{0}.sh\n'

        class Inspect:
            COMMAND = 'docker inspect -f \'{{{{ .Config.{key} }}}}\' {image}'
            CMD = 'Cmd'
            ENTRYPOINT = 'Entrypoint'
            ENV = 'Env'
            LABEL = 'Labels'


class Commands:
    def __init__(self):
        self.list = docker.all

    def execute(self, command, context):
        if self.exists(command):
            instruction = self.get_instruction(command)
            params = self.get_params(command)
            log(command)
            self.list[instruction](params=params, context=context)
        else:
            log("Command {0} not found".format(command))

    def get_instruction(self, command):
        return command.split(' ', 1)[0].lstrip("#!")

    def get_params(self, command):
        command_line = command.split(' ', 1)
        if len(command_line) > 1:
            return command_line[1]
        else:
            return None

    def exists(self, command):
        return self.get_instruction(command) in self.list


# Simple key-value pair parser. Supports formats "key value" and "key=value"
class KeyValue:
    def __init__(self, string):
        key_value = string.split(' ', 1)
        if len(key_value) < 2:
            key_value = string.split('=', 1)
            if len(key_value) < 2:
                raise ValueError('Invalid command parameters: {0}'.format(string))
        self.key = key_value[0]
        self.value = key_value[1]


# Command line argument parser. Supports short option name, long option name and formats "option value", "option=value"
class Option:
    def reset(self):
        self.option_indexes = []
        self.waiting_for_value = False
        self.value = None

    def __init__(self, option_short=None, option_long=None, supports_equal=False, cleanup=False, single_instance=True):
        self.option_short = option_short
        self.option_long = option_long
        self.supports_equals = supports_equal
        self.cleanup = cleanup
        self.single_instance = single_instance
        self.values = []
        self.reset()

    def verify(self, option, index):
        if self.waiting_for_value:
            self.value = option
            if not self.single_instance:
                self.values.append(self.value)
            self.waiting_for_value = False
            self.option_indexes = [index - 1, index]
        elif (self.option_short != None and option == self.option_short) or (
                        self.option_long != None and option == self.option_long):
            self.waiting_for_value = True
        elif self.supports_equals and self.option_long != None and option.startswith("{0}=".format(self.option_long)):
            self.value = option.split("=", 1)[1]
            if not self.single_instance:
                self.values.append(self.value)
            self.waiting_for_value = False
            self.option_indexes = [index]

    def found(self):
        return self.value != None

class OptionSet:
    def __init__(self, options):
        self.options=options

    def find(self, lines, index):
        line = lines[index]
        for option in self.options:
            if not option.found():
                option.verify(line, index)
                if option.found():
                    if option.cleanup:
                        for i in option.option_indexes:
                            lines[i] = ''
                    if not option.single_instance:
                        option.reset()


# Temporary image name generator. Stores the original image name
class DockerImageName:
    def __init__(self, image_name):
        tag = str(uuid4())
        if image_name == None:
            self.original_image_name = ""
        else:
            self.original_image_name = image_name
        self.tmp_image_name = tag


# Shell script generator. Replaces --build-arg values. Supports running commands in behalf of another user.
class DockerScript:
    def __init__(self, build_args):
        self.script = []
        self.user = None
        self.build_args = build_args

    def su(self, user):
        self.user = user

    def root(self):
        self.user = None

    def add(self, command):
        if self.user != None:
            line = "su -c '{cmd}' {usr}"
        else:
            line = "{cmd}"
        for i in range(0, len(self.build_args)):
            if self.user != None:
                replace_string = "'\"${0}\"'".format(i + 1)
            else:
                replace_string = "${0}".format(i + 1)
            command = command.replace("${{{0}}}".format(self.build_args[i].key), replace_string)
        command = line.format(cmd=command, usr=self.user)
        self.script.append(command + "\n")

    def lines(self):
        return self.script


# Common method to add new line symbol at the end of the string
def newline(text):
    return text + "\n"


# Executes OS command using os.system() in given working directory, logs the command and verifies the exit code
def sh(command, directory=None, command_line=None):
    if directory == None:
        log(command)
    else:
        log("{0}/{1}".format(directory, command))
    currentPath = ''
    if directory != None:
        currentPath = os.getcwd()
        os.chdir(directory)
    if command_line is not None:
        command = command_line.format(command)
    exitCode = os.system(command)
    if exitCode != 0:
        raise OSError(exitCode)
    if directory != None:
        os.chdir(currentPath)


def inspectImage(descriptor, key, list, command):
    cmd = descriptor[0]["Config"][key]
    if cmd is not None:
        value = "["
        first = True
        for element in cmd:
            if not first:
                value += ", "
            else:
                first = False
            value += "\"" + element.replace('"', '\\"') + "\""
        value += "]"
        list.append("{cmd} {value}".format(cmd=command, value=value))


class DictPathAccess:
    def __init__(self, descriptor):
        self.descriptor = descriptor

    def get(self, path):
        element = self.descriptor
        levels = path.split('/')
        for level in levels:
            if level in element:
                element = element[level]
            else:
                return None
        return element

    def set(self, path, value, create=False):
        element = self.descriptor
        levels = path.split('/')
        if len(levels) > 0:
            for i in range(0, len(levels) - 1):
                if levels[i] not in element:
                    if create:
                        element[levels[i]] = dict()
                    else:
                        raise ValueError("Element {0} does not exist!".format(levels[i]))
                element = element[levels[i]]
            lastLevel = levels[len(levels) - 1]
            element[lastLevel] = value

    def exists(self, path):
        return self.get(path) != None


def dockerExec(command, connect=False):
    if connect:
        command_line = "(eval \"$(docker-machine env --shell=bash default)\";{0})"
    else:
        command_line = None
    sh(command, command_line=command_line)


def dockerRead(command, connect=False):
    log(command)
    if connect:
        command = "(eval \"$(docker-machine env --shell=bash default)\";{cmd})".format(cmd=command)
    res = subprocess.check_output(command, shell=True)
    log(res)
    return res


def checkOptsFile(options):
    optionPropertiesFile = Option(option_short=None, option_long="--opts-file", supports_equal=True)

    for i in range(0, len(options)):
        option = options[i]
        if not optionPropertiesFile.found():
            optionPropertiesFile.verify(option, i)
            if optionPropertiesFile.found():
                for idx in optionPropertiesFile.option_indexes:
                    options[idx] = ""
                break

    if optionPropertiesFile.found():
        propsPath = os.path.abspath(os.path.join(os.getcwd(), optionPropertiesFile.value))
        if os.path.exists(propsPath):
            props = open(propsPath, 'r')
            opts = props.readlines()
            props.close()
            for opt in opts:
                options = re.split('\s', opt.rstrip('\n')) + options
    return options
