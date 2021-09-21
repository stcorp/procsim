'''
Copyright (C) 2021 S[&]T, The Netherlands.

Exceptions
'''


from typing import Any


class ProcsimException(Exception):
    '''
    Base for all procsim exceptions
    '''
    pass


class TerminateError(ProcsimException):
    '''
    Program terminated externally (CTRL-C or SIGTERM)
    '''
    pass


class ScenarioError(ProcsimException):
    '''
    Error in scenario configuration
    '''
    pass


class GeneratorError(ProcsimException):
    '''
    Error in generator
    '''
    pass


class ParseError(ProcsimException):
    '''
    Error parsing XML
    '''
    def __init__(self, value: Any, message: str = 'Error parsing XML. Received invalid value') -> None:
        super().__init__(value)
        print(message, value)
