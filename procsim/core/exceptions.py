'''
Copyright (C) 2021 S[&]T, The Netherlands.

Exceptions
'''


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
