'''
Copyright (C) 2021 S[&]T, The Netherlands.

Exceptions
'''


class TerminateError(Exception):
    '''
    Program terminated externally (CTRL-C or SIGTERM)
    '''
    pass


class ScenarioError(Exception):
    '''
    Error in scenario configuration
    '''
    pass
