import os
import argparse
import platform

from . import checkpoint as ckpt
from . import logging as cbio_logging

MAX_GPU_MEMORY=0.8


def _limit_gpu_memory(fraction=MAX_GPU_MEMORY):
    # limits GPU memory to use tensorflow-gpu
    import tensorflow as tf
    from keras.backend.tensorflow_backend import set_session
    config = tf.ConfigProto()
    config.gpu_options.per_process_gpu_memory_fraction = fraction
    set_session(tf.Session(config=config))


def check_os():
    # check if Windows to limit GPU memory and avoid errors
    if platform.system() == 'Windows':
        _limit_gpu_memory()


def str2bool(value):
    if value.lower() in ('true', 't', '1'):
        return True
    elif value.lower() in ('false', 'f', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def basic_setup(default_folder='checkpoints', log=False):
    args = argparse.ArgumentParser(prog='simple_args')
    args.add_argument('-c', '--checkpoint', type=str, default=default_folder)
    args.add_argument('-o', '--output', type=str, default='out.log')
    args.add_argument('-e', '--error', type=str, default='err.log')

    parser = args.parse_args()

    ckpt.ckpt_folder = parser.checkpoint

    if not os.path.exists(ckpt.ckpt_folder):
        os.makedirs(ckpt.ckpt_folder)

    cbio_logging.setup(log_lvl='DEBUG', 
        out_file=os.path.join(ckpt.ckpt_folder, parser.output), 
        err_file=os.path.join(ckpt.ckpt_folder, parser.error))


def args_evolution_exp():

    ''' default parameters used in a experiment that runs
        an evolutionary algorithm to design neural networks
    '''

    parser = argparse.ArgumentParser(prog='script.py')

    # checkpoint
    parser.add_argument('-f', '--folder', default='checkpoints')
    parser.add_argument('-c', '--checkpoint', default=True, type=str2bool)

    # problem
    parser.add_argument('-g', '--grammar', type=str, default=None)
    parser.add_argument('-d', '--dataset', type=str, default=None)
    parser.add_argument('-t', '--training', type=int, default=True)
    parser.add_argument('-tr', '--train', type=int, default=None)
    parser.add_argument('-va', '--valid', type=int, default=None)
    parser.add_argument('-te', '--test', type=int, default=None)
    parser.add_argument('-sd', '--seed', default=None, type=int)
    parser.add_argument('-ep', '--epochs', default=1, type=int)
    parser.add_argument('-b', '--batch', default=32, type=int)
    parser.add_argument('-tl', '--timelimit', type=int, default=3600) #(in seconds) 1h
    parser.add_argument('-s', '--shuffle', type=int, default=0)

    # algorithm
    parser.add_argument('-p', '--pop', type=int, default=5)
    parser.add_argument('-e', '--evals', type=int, default=10)
    parser.add_argument('-cr', '--crossover', type=float, default=0.8)
    parser.add_argument('-mt', '--mutation', type=float, default=0.1)

    # multiprocessing
    parser.add_argument('-w', '--workers', type=int, default=1) #workers    
    parser.add_argument('-mp', '--multip', type=int, default=0) #multiprocessing

    # generic
    # 0 - no messages
    # 1 - search messages
    # 2 - problem messages
    parser.add_argument('-v', '--verbose', default=0, type=int)

    return parser.parse_args()