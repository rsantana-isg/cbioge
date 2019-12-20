import os
import re
import copy
import json
import pickle
import itertools

import keras
from keras.models import model_from_json
from keras.preprocessing.image import ImageDataGenerator
from keras.optimizers import *
from keras.callbacks import *

from utils.image import *
from utils.model import TimedStopping

from problems import BaseProblem
from datasets.dataset import DataGenerator


class UNetProblem(BaseProblem):

    def __init__(self, parser):
        self.batch_size = 1
        self.epochs = 1

        self.loss = 'binary_crossentropy'
        self.opt = Adam(lr = 1e-4)
        self.metrics = ['accuracy']

        self.parser = parser     

        self.workers = 1
        self.multiprocessing = False

        self.verbose = False

        self._initialize_blocks()
        #self._generate_configurations()

    def read_dataset_from_pickle(self, pickle_file):
        with open(pickle_file, 'rb') as f:
            temp = pickle.load(f)

            self.x_train = temp['x_train']
            self.y_train = temp['y_train']

            self.x_valid = temp['x_valid']
            self.y_valid = temp['y_valid']

            self.x_test = temp['x_test']
            self.y_test = temp['y_test']

            self.input_shape = temp['input_shape']

            self.train_size = len(self.x_train)
            self.valid_size = len(self.x_valid)
            self.test_size = len(self.x_test)
            del temp

    def read_dataset_from_generator(self, dataset, train_gen, test_gen):
        self.dataset = dataset
        self.train_generator = train_gen
        self.test_generator = test_gen
        self.input_shape = tuple(dataset['input_shape'])

    def _initialize_blocks(self):
        self.blocks = {
            'input': ['InputLayer', 'batch_input_shape'],
            'conv': ['Conv2D', 'filters', 'kernel_size', 'strides', 'padding', 'activation'],
            'avgpool': ['AveragePooling', 'pool_size', 'strides', 'padding'],
            'maxpool': ['MaxPooling2D', 'pool_size', 'strides', 'padding'],
            'dropout': ['Dropout', 'rate'],
            'upsamp': ['UpSampling2D', 'size'],
            'concat': ['Concatenate', 'axis'],
            'crop': ['Cropping2D', 'cropping'],

            'bridge': ['bridge'], #check
        }

    def _generate_configurations(self):
        if self.parser:
            kernels = [i[0] for i in self.parser.GRAMMAR['<kernel_size>']]
            strides = [i[0] for i in self.parser.GRAMMAR['<strides>']]
            padding = [i[0] for i in self.parser.GRAMMAR['<padding>']]
            conv_configs = list(itertools.product(kernels, strides, padding))
            max_img_size = self.input_shape[1]
            self.conv_valid_configs = {}
            for img_size in range(0, max_img_size+1):
                key = str(img_size)
                self.conv_valid_configs[key] = conv_configs[:]
                for config in conv_configs:
                    output_shape = calculate_output_size((img_size, img_size), *config)
                    if (0, 0) > output_shape > (img_size, img_size):
                        self.conv_valid_configs[key].remove(config)

    def _reshape_mapping(self, phenotype):

        new_mapping = []

        index = 0
        while index < len(phenotype):
            block = phenotype[index]
            if block == 'conv':
                end = index+6
            elif block in ['avgpool', 'maxpool']:
                end = index+4
            elif block == 'bridge':
                end = index+1
            else:
                end = index+2

            new_mapping.append(phenotype[index:end])
            phenotype = phenotype[end:]

        return new_mapping

    def _parse_value(self, value):
        if type(value) is str:
            m = re.match('\\[(\\d+[.\\d+]*),\\s*(\\d+[.\\d+]*)\\]', value)
            if m:
                min_ = eval(m.group(1))
                max_ = eval(m.group(2))
                if type(min_) == int and type(max_) == int:
                    return np.random.randint(min_, max_)
                elif type(min_) == float and type(max_) == float:
                    return np.random.uniform(min_, max_)
                else:
                    raise TypeError('type mismatch')
            else:
                return value
        else:
            return value

    def _build_block(self, block_name, params):

        base_block = {'class_name': None, 'name': None, 'config': {}, 'inbound_nodes': []}

        if block_name in self.naming:
            self.naming[block_name] += 1
        else:
            self.naming[block_name] = 0
        name = f'{block_name}_{self.naming[block_name]}'

        base_block['class_name'] = self.blocks[block_name][0]
        base_block['name'] = name
        for key, value in zip(self.blocks[block_name][1:], params):
            base_block['config'][key] = self._parse_value(value)

        #print(base_block)
        return base_block

    def _wrap_up_model(self, model):
        layers = model['config']['layers']
        stack = []
        for i, layer in enumerate(model['config']['layers']):
            if layer['class_name'] in ['push', 'bridge']: #CHECK
                stack.append(layers[i-1]) #layer before (conv)
                model['config']['layers'].remove(layers[i])

        for i, layer in enumerate(layers[1:]):

            last = model['config']['layers'][i]
            layer['inbound_nodes'].append([[last['name'], 0, 0]])

            if layer['class_name'] == 'Concatenate':
                other = stack.pop()
                # print('CONCATENATE', layer['name'], other['name'])
                layer['inbound_nodes'][0].insert(0, [other['name'], 0, 0])

        input_layer = model['config']['layers'][0]['name']
        output_layer = model['config']['layers'][-1]['name']
        model['config']['input_layers'].append([input_layer, 0, 0])
        model['config']['output_layers'].append([output_layer, 0, 0])

        # for l in layers:
        #     print(l)

    def _repair_genotype(self, genotype, phenotype):
        print(genotype)
        values = {}
        model = json.loads(phenotype)
        layers = model['config']['layers']
        for layer in layers:
            #print(layer)
            name = layer['name'].split('_')[0]
            if not name in ['conv', 'maxpool', 'avgpool', 'upsamp']:
                continue
            for key in layer['config']:
                vkey = 'kernel_size' if key in ['pool_size', 'size'] else key
                if vkey in values:
                    values[vkey].append(layer['config'][key])
                else:
                    values[vkey] = [layer['config'][key]]

        for key in values:
            rule_index = self.parser.NT.index(f'<{key}>')

            grm_options = self.parser.GRAMMAR[f'<{key}>']
            gen_indexes = genotype[rule_index]
            fen_indexes = [grm_options.index([val]) for val in values[key]]
            print(key, values[key])
            print(gen_indexes)
            print(fen_indexes)

            genotype[rule_index] = fen_indexes[:len(gen_indexes)]

        print(genotype)
        return genotype

    def _build_right_side(self, mapping):

        blocks = None
        for block in reversed(mapping):
            name, params = block[0], block[1:]
            if name == 'maxpool':
                if blocks != None:
                    mapping.append(['upsamp', 2])
                    mapping.append(['conv', 0, 2, 1, 'same', 'relu'])
                    if ['bridge'] in blocks:
                        mapping.append(['concat', 3])
                        blocks.remove(['bridge'])
                    mapping.extend(blocks)
                blocks = []
            elif blocks != None:
                blocks.append(block)
        if blocks != None:
            if blocks != None:
                mapping.append(['upsamp', 2])
                mapping.append(['conv', 0, 2, 1, 'same', 'relu'])
                if ['bridge'] in blocks:
                    mapping.append(['concat', 3])
                    blocks.remove(['bridge'])
                mapping.extend(blocks)
        
        mapping.insert(0, ['input', (None,)+self.input_shape]) #input layer
        mapping.append(['conv', 2, 3, 1, 'same', 'relu']) #classification layer
        mapping.append(['conv', 1, 1, 1, 'same', 'sigmoid']) #output layer

        return mapping
                
    def _get_layer_outputs(self, mapping):
        outputs = []
        depth = 0
        for i, block in enumerate(mapping):
            name, params = block[0], block[1:]
            if name == 'input':
                output_shape = self.input_shape
            elif name == 'conv':
                output_shape = calculate_output_size(output_shape, *params[1:4])
                output_shape += (params[0],)
            elif name in ['maxpool', 'avgpool']:
                depth += 1
                temp = calculate_output_size(output_shape, *params[:3])
                output_shape = temp + (output_shape[2],)
            elif name == 'upsamp':
                depth -= 1
                factor = params[0]
                output_shape = (output_shape[0] * factor, output_shape[1] * factor, output_shape[2])
            elif name == 'concat':
                output_shape = (output_shape[0], output_shape[1], output_shape[2]*2)
            # print('\t'*depth, i, output_shape, block)
            outputs.append(output_shape)
        return outputs

    def _non_recursive_repair(self, mapping):
        outputs = self._get_layer_outputs(mapping)
        stack = []
        for i, layer in enumerate(mapping):
            name, params = layer[0], layer[1:]
            if name == 'maxpool':
                stack.append(outputs[i-1])
            elif name == 'upsamp' and stack != []:
                aux_output = stack.pop()
                if aux_output[:-1] == (1, 1):
                    mapping[i][1] = 1
                    #print(i, 'changing upsamp to 1x')
                #print(i, 'adjusting number of filters in layer', aux_output)
                mapping[i+1][1] = aux_output[2]

    def map_genotype_to_phenotype(self, genotype):
        
        self.naming = {}
        self.stack = []

        mapping = self.parser.dsge_recursive_parse(genotype)
        mapping = self._reshape_mapping(mapping)
        mapping = self._build_right_side(mapping)
        self._non_recursive_repair(mapping)

        model = {'class_name': 'Model', 
            'config': {'layers': [], 'input_layers': [], 'output_layers': []}}

        for i, layer in enumerate(mapping):
            block_name, params = layer[0], layer[1:]
            block = self._build_block(block_name, params)
            model['config']['layers'].append(block)

        self._wrap_up_model(model)

        return json.dumps(model)

    def _predict_model(self, model):
        predictions = model.predict_generator(
            self.test_generator, 
            steps=self.dataset['test_steps'], 
            workers=self.workers, 
            use_multiprocessing=self.multiprocessing, 
            verbose=self.verbose)

        for i, img in enumerate(predictions):
            write_image(os.path.join(self.dataset['path'], f'test/pred/{i}.png'), img)

    def evaluate_generator(self, phenotype, predict=False):
        try:
            model = model_from_json(phenotype)

            model.compile(optimizer=self.opt, loss=self.loss, metrics=self.metrics)

            model = self._train_model(model)

            loss, acc = self._evaluate_model(model)           

            if predict:
                self._predict_model(model)                

            return loss, acc
        except Exception as e:
            print('[evaluation]', e)
            return -1, None

    def evaluate(self, phenotype, train=True, predict=False):
        try:
            model = model_from_json(phenotype)

            model.compile(optimizer=self.opt, loss=self.loss, metrics=self.metrics)

            x_train = self.x_train[:self.train_size]
            y_train = self.y_train[:self.train_size]
            x_valid = self.x_valid[:self.valid_size]
            y_valid = self.y_valid[:self.valid_size]
            x_test = self.x_test[:self.test_size]
            y_test = self.y_test[:self.test_size]

            ts = TimedStopping(seconds=3600, verbose=True) #1h

            callb_list = [ts]

            if train:
                model.fit(x_train, y_train, validation_data=(x_valid, y_valid), batch_size=self.batch_size, epochs=self.epochs, verbose=self.verbose, callbacks=callb_list)
            loss, acc = model.evaluate(x_test, y_test, batch_size=self.batch_size, verbose=self.verbose)

            if self.verbose:
                print('loss', loss, 'acc', acc)

            if predict:
                predictions = model.predict(x_test, batch_size=self.batch_size, verbose=self.verbose)
                if not os.path.exists('preds'):
                    os.mkdir('preds')
                
                for i, img in enumerate(predictions):
                    write_image(os.path.join('preds', f'{i}.png'), img)

            return loss, acc
        except Exception as e:
            print('[evaluation]', e)
            return -1, None
