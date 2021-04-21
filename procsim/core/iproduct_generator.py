'''
Copyright (C) 2021 S[&]T, The Netherlands.

Interface for procsim product generators
'''
import abc
from typing import Iterable, List

from .job_order import JobOrderInput


class IProductGenerator(abc.ABC):
    '''
    Interface for product generators
    '''
    @abc.abstractmethod
    def parse_inputs(self, inputs: Iterable[JobOrderInput]) -> bool:
        pass

    @abc.abstractmethod
    def list_scenario_parameters(self) -> List[str]:
        '''
        Returns lists with generator- and metadata parameters that can be used
        in the scenario.
        '''
        pass

    @abc.abstractmethod
    def read_scenario_parameters(self):
        pass

    @abc.abstractmethod
    def generate_output(self):
        pass
