import sys, os
sys.path.append('..')

from algorithms import ge
from grammars import grammar
from problems import problem

problem.DEBUG = False
ge.DEBUG = False

# dataset and grammar
pickle_file = '../datasets/mnist/mnist.pickle'
grammar_file = '../grammars/cnn.bnf'

# read grammar and setup parser
grammar.load_grammar(grammar_file)

# reading dataset
my_problem = problem.CnnProblem()
my_problem.load_dataset_from_pickle(pickle_file)
ge.problem = my_problem

# problem parameters
my_problem.batch_size = 128
my_problem.epochs = 5

# changing GE default parameters
#ge.SEED = 42
ge.POP_SIZE = 20
ge.MAX_EVALS = 400

print('--config--')
print('DATASET', pickle_file)
print('GRAMMAR', grammar_file)

print('SEED', ge.SEED)
print('POP', ge.POP_SIZE)
print('EVALS', ge.MAX_EVALS)
print('CROSS', ge.CROSS_RATE)
print('MUT', ge.MUT_RATE)
print('PRUN', ge.PRUN_RATE)
print('DUPL', ge.DUPL_RATE)

print('--running--')
best = ge.execute()

print('--best solution--')
print(best.fitness, best)
best.phenotype.summary()

print('--testing--')
score = best.phenotype.evaluate(
	my_problem.x_test, 
	my_problem.y_test, 
	verbose=0)
print('loss: {}\taccuracy: {}'.format(score[0], score[1]))