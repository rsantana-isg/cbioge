import glob
import os
import pickle
import re

import numpy as np

from utils.image import *


def load_dataset(file_name):
    with open(file_name, 'rb') as f:
        data = pickle.load(f)
    return data


def get_natural_key(string):
    matches = re.findall('(\\d+)', string)
    if len(matches) > 0:
        return int(matches[-1])
    else:
        return 0


def load_predictions(folder):
    files = glob.glob(os.path.join(folder, '*.png'))
    files.sort(key=lambda x: get_natural_key(x))
    print(files)
    images = [load_image(f) for f in files]
    return np.array(images)


def apply_measures(labels, preds, name='plot.png'):
    measures = {
        'iou': [],
        'jac': [],
        'spc': [],
        'sen': [],
        'dic': [],
        'all': []
    }

    for l, p in zip(labels, preds):
        p = normalize(p)
        l = normalize(l)

        p = binarize(p)
        l = binarize(l)

        measures['iou'].append(iou_accuracy(l, p))
        measures['jac'].append(1-jaccard_distance(l, p))
        measures['spc'].append(specificity(l, p))
        measures['sen'].append(sensitivity(l, p))
        measures['dic'].append(dice_coef(l, p))
        measures['all'].append(weighted_measures(l, p))

    for key in measures:
        print(np.mean(measures[key]))
        plt.plot(measures[key], label=key)
        plt.scatter(range(len(labels)), measures[key], s=14, edgecolors='none', c='black')
    print('---')
    plt.xlabel('Image')
    plt.ylabel('Measure')
    plt.legend(loc="lower right")
    plt.savefig(f'{name}.png')
    #plt.show()
    plt.clf()


if __name__ == '__main__':

    dataset_name = 'membrane'
    preds_names = ['memb1', 'memb2']

    #dataset_name = 'textures_simple'
    #preds_names = ['texture1', 'texture2', 'texture3', 'texture4']
    
    dataset = load_dataset(f'datasets/{dataset_name}.pickle')
    
    labels = dataset['y_test']

    preds = []
    for i, pname in enumerate(preds_names):
        preds.append(load_predictions(f'analyze/{pname}'))
        apply_measures(labels, preds[i], pname)

    apply_measures(labels, labels, 'labellabel')