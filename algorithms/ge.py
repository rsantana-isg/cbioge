import os, sys
sys.path.append('..')

from multiprocessing import Pool, Manager
from utils import checkpoint

import glob
import numpy as np
import random
import re
import time

from .solutions import GESolution
from .ea import BaseEvolutionaryAlgorithm


class GrammaticalEvolution(BaseEvolutionaryAlgorithm):

	RAND = np.random

	DEBUG = False

	def __init__(self, problem):
		super(GrammaticalEvolution, self).__init__(problem)

		self.SEED = None
		
		self.POP_SIZE = 5
		self.MAX_EVALS = 10

		self.MIN_GENES = 1
		self.MAX_GENES = 10
		self.MIN_VALUE = 0
		self.MAX_VALUE = 255

		self.CROSS_RATE = 0.8
		self.MUT_RATE = 0.1
		self.PRUN_RATE = 0.1
		self.DUPL_RATE = 0.1

		self.selection = None

		self.population = None
		self.evals = None


	def create_solution(self, min_size, max_size, min_value, max_value):
		if not max_size:
			max_size = min_size
			min_size = 0
		
		if min_size >= max_size:
			raise ValueError('[create solution] min >= max')

		genes = self.RAND.randint(min_value, max_value, self.RAND.randint(
			min_size, max_size))

		return GESolution(genes)


	def create_population(self, size):
		population = []
		for _ in range(size):
			solution = self.create_solution(self.MIN_GENES, self.MAX_GENES, 
					self.MIN_VALUE, self.MAX_VALUE)
			population.append(solution)
		return population


	def evaluate_solution(self, solution):
		if self.DEBUG: print('<{}> [evaluate] started: {}'.format(
			time.strftime('%x %X'), solution))

		if not solution.evaluated:
			if self.problem is None:
				if self.DEBUG:
					print('[evaluation] Problem is None, bypassing')
					solution.fitness = -1
				else:
					raise ValueError('Problem is None')
			else:
				fitness, model = self.problem.evaluate(solution, 1)
		
		if self.DEBUG: print('<{}> [evaluate] ended: {}'.format(
			time.strftime('%x %X'), solution))
		
		return fitness, model


	def evaluate_population(self, population):

		pool = Pool(processes=self.MAX_PROCESSES)

		result = pool.map_async(self.evaluate_solution, population)
		
		pool.close()
		pool.join()

		for sol, res in zip(population, result.get()):
			fit, model = res
			sol.fitness = fit
			sol.phenotype = model
			sol.evaluated = True


	# def selection(self, population):
	# 	if len(population) < 2:
	# 		raise ValueError('[selection] population size is less than minimum (2)')
		
	# 	p1 = None
	# 	p2 = None
	# 	p1 = self.RAND.choice(population)
	# 	while not p2 or p1 is p2:
	# 		p2 = self.RAND.choice(population)
	# 	return [p1, p2]


	def crossover(self, parents, prob):
		off1 = parents[0].copy()
		off2 = parents[1].copy()

		if self.RAND.rand() < prob:
			p1 = off1.genotype[:]
			p2 = off2.genotype[:]
			min_ = min(len(p1), len(p2))
			cut = self.RAND.randint(0, min_)
			off1.genotype = np.concatenate((p1[:cut], p2[cut:]))
		return [off1]


	def mutate(self, offspring, prob):
		if self.RAND.rand() < prob:
			for off in offspring:
				index = self.RAND.randint(0, len(off.genotype))
				off.genotype[index] = self.RAND.randint(0, 255)


	def prune(self, offspring, prob):
		if self.RAND.rand() < prob:
			for off in offspring:
				if len(off.genotype) <= 1:
					if self.DEBUG: print('[prune] one gene, not applying:', off.genotype)
					continue
				cut = self.RAND.randint(1, len(off.genotype))
				off.genotype = off.genotype[:cut]


	def duplicate(self, offspring, prob):
		if self.RAND.rand() < prob:
			for off in offspring:
				if len(off.genotype) > 1:
					cut = self.RAND.randint(0, len(off.genotype))
				else:
					if self.DEBUG: print('[duplication] one gene, setting cut to 1:', off)
					cut = 1
				genes = off.genotype
				off.genotype = np.concatenate((genes, genes[:cut]))


	def replace(self, population, offspring):
		
		population += offspring
		population.sort(key=lambda x: x.fitness, reverse=self.MAXIMIZE)

		for _ in range(len(offspring)):
			population.pop()


	def execute(self, checkpoint=False):

		#population = None
		#evals = None
		#if checkpoint:
		#	print('starting from checkpoint')
		#	population, evals = load_state()
		
		#if not population and not evals:
		#	print('starting from zero')
		self.population = self.create_population(self.POP_SIZE)
		self.evaluate_population(self.population)
		self.population.sort(key=lambda x: x.fitness, reverse=self.MAXIMIZE)

		self.evals = len(self.population)

		if self.DEBUG:
			for i, p in enumerate(self.population):
				print(i, p.fitness, p)

		print('<{}> evals: {}/{} \tbest so far: {}\tfitness: {}'.format(
			time.strftime('%x %X'), 
			self.evals, self.MAX_EVALS, 
			self.population[0].genotype, 
			self.population[0].fitness)
		)

		#	save_state(evals, population)

		while self.evals < self.MAX_EVALS:
			parents = self.selection.execute(self.population)
			offspring_pop = []

			for _ in self.population:
				offspring = self.crossover(parents, self.CROSS_RATE)
				self.mutate(offspring, self.MUT_RATE)
				self.prune(offspring, self.PRUN_RATE)
				self.duplicate(offspring, self.DUPL_RATE)
				offspring_pop += offspring

			self.evaluate_population(offspring_pop)
			self.replace(self.population, offspring_pop)

			self.evals += len(offspring_pop)

			if self.DEBUG:
				for i, p in enumerate(self.population):
					print(i, p.fitness, p)

			print('<{}> evals: {}/{} \tbest so far: {}\tfitness: {}'.format(
				time.strftime('%x %X'), 
				self.evals, self.MAX_EVALS, 
				self.population[0].genotype, 
				self.population[0].fitness)
			)
			
			#save_state(evals, population)

		return self.population[0]


def save_state(evals, population):

	args = {
		'POP_SIZE': POP_SIZE, 
		'MIN_GENES': MIN_GENES, 
		'MAX_GENES': MAX_GENES, 
		'MAX_EVALS': MAX_EVALS, 

		'MAX_PROCESSES': MAX_PROCESSES, 

		'CROSS_RATE': CROSS_RATE, 
		'MUT_RATE': MUT_RATE, 
		'PRUN_RATE': PRUN_RATE, 
		'DUPL_RATE': DUPL_RATE, 

		'MINIMIZE': MINIMIZE, 

		'evals': evals
	}

	folder = checkpoint.ckpt_folder
	if not os.path.exists(folder): os.mkdir(folder)
	checkpoint.save_args(args, os.path.join(folder, 'args_{}.ckpt'.format(evals)))
	checkpoint.save_population(population, os.path.join(folder, 'pop_{}.ckpt'.format(evals)))


def load_state(args_file=None, pop_file=None):
	''' loads the state stored in both args file and pop file
		if one is None, the default behavior is to try to load the 
		most recent one
	'''
	global MAX_EVALS, CROSS_RATE, MUT_RATE, PRUN_RATE, DUPL_RATE, MINIMIZE

	folder = checkpoint.ckpt_folder

	pop_files = glob.glob(os.path.join(folder, 'pop_*'))
	for i, file in enumerate(pop_files):
		m = re.match('\\S+_([\\d]+).ckpt', file)
		id = int(m.group(1)) if m else 0
		pop_files[i] = {'id': id, 'file': file}

	arg_files = glob.glob(os.path.join(folder, 'args_*'))
	for i, file in enumerate(arg_files):
		m = re.match('\\S+_([\\d]+).ckpt', file)
		id = int(m.group(1)) if m else 0
		arg_files[i] = {'id': id, 'file': file}

	if pop_files == [] or arg_files == []:
		return None, None

	pop_files.sort(key=lambda x: x['id'], reverse=True)
	pop_file = pop_files[0]['file']
	population = checkpoint.load_population(pop_file)

	arg_files.sort(key=lambda x: x['id'], reverse=True)
	args_file = arg_files[0]['file']
	args = checkpoint.load_args(args_file)

	#POP_SIZE = args['POP_SIZE'] 
	#args['MIN_GENES']
	#args['MAX_GENES']
	#args['MAX_PROCESSES']
	
	print('CROSS_RATE set to', CROSS_RATE)
	CROSS_RATE = args['CROSS_RATE']
	
	print('MUT_RATE set to', MUT_RATE)
	MUT_RATE = args['MUT_RATE']

	print('PRUN_RATE set to', PRUN_RATE)
	PRUN_RATE = args['PRUN_RATE'] 

	print('DUPL_RATE set to', DUPL_RATE)
	DUPL_RATE = args['DUPL_RATE']

	print('MINIZE set to', MINIMIZE)
	MINIMIZE = args['MINIMIZE']

	evals = args['evals']
	print('evals set to', evals)

	MAX_EVALS = int(args['MAX_EVALS']) #temp
	print('MAX_EVALS set to', MAX_EVALS)

	return population, evals
