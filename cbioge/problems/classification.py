import keras.layers
from keras.models import Model

from .dnns import layers as clayers
from cbioge.datasets import Dataset
from cbioge.grammars import Grammar
from cbioge.problems import DNNProblem
from cbioge.algorithms import GESolution


class CNNProblem(DNNProblem):
    ''' Problem class for problems related to classification tasks for DNNs.
        This class includes methods focused on the design of CNNs.
    '''
    def __init__(self, parser: Grammar, dataset: Dataset,
        batch_size=32, 
        epochs=1, 
        opt='adam', 
        loss='categorical_crossentropy', 
        metrics=['accuracy'], 
        test_eval=False, 
        verbose=False, 
        train_args={}, 
        test_args={}):

        super().__init__(parser, dataset, batch_size, epochs, opt, loss, 
            metrics, test_eval, verbose, train_args, test_args)

    def _sequential_build(self, mapping: list) -> Model:

        layers = []

        # input layer
        layers.append(keras.layers.Input(shape=self.dataset.input_shape))
        for block in mapping:
            b_name, values = block[0], block[1:]
            l = clayers._get_layer(self.parser.blocks[b_name][0],
                [keras.layers, clayers.layers])
            config = {param: value for param, value in zip(self.parser.blocks[b_name][1:], values)}
            layers.append(l.from_config(config))

        # classifier layers
        layers.append(keras.layers.Flatten())
        layers.append(keras.layers.Dense(self.dataset.num_classes, activation='softmax'))

        try:
            # connecting the layers (functional API)
            in_layer = layers[0]
            out_layer = layers[0]
            for l in (layers[1:]):
                out_layer = l(out_layer)

            return Model(inputs=in_layer, outputs=out_layer)
        except Exception as e:
            self.logger.exception('Invalid model')
            return None

    def map_genotype_to_phenotype(self, solution: GESolution) -> Model:

        # try using existing mapping to build
        if 'mapping' in solution.data: mapping = solution.data['mapping']

        # creates mapping using the grammar
        else: mapping = self.parser.dsge_recursive_parse(solution.genotype)

        # creates the model
        model = self._sequential_build(mapping)

        if model is not None:
            solution.phenotype = model.to_json()
            solution.data['params'] = model.count_params()
        else:
            solution.phenotype = None
            solution.data['params'] = 0
        solution.data['mapping'] = mapping

        return model