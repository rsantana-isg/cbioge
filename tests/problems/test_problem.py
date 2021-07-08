import pytest

from cbioge.grammars import Grammar
from cbioge.problems import BaseProblem, DNNProblem

def get_mockup_parser():
    return Grammar('tests/data/test_grammar.json')

def get_mockup_data_dict():

    return {
        'x_train': [], 
        'y_train': [], 
        'x_valid': [], 
        'y_valid': [], 
        'x_test': [], 
        'y_test': [], 
        'input_shape': (None,)
    }

def test_isinstance_of_dnnproblem():
    parser = get_mockup_parser()
    dataset = get_mockup_data_dict()
    problem = DNNProblem(parser, dataset)
    assert isinstance(problem, DNNProblem)

def test_is_dnnproblem_subclass_of_problem():
    assert issubclass(DNNProblem, BaseProblem) == True

def test_baseproblem_has_functions():
    problem = BaseProblem(get_mockup_parser())
    assert hasattr(problem, 'map_genotype_to_phenotype')
    assert hasattr(problem, 'evaluate')

def test_dnnproblem_none_parser():
    with pytest.raises(AttributeError):
        DNNProblem(None, get_mockup_data_dict())