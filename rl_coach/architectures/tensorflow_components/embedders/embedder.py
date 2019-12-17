#
# Copyright (c) 2019 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from typing import List, Union
import numpy as np
import tensorflow as tf
from tensorflow import keras, Tensor
from rl_coach.base_parameters import EmbedderScheme
from rl_coach.core_types import InputEmbedding
from rl_coach.architectures.tensorflow_components.layers import convert_layer


class InputEmbedder(keras.layers.Layer):
    """
    An input embedder is the first part of the network, which takes the input from the state and produces a vector
    embedding by passing it through a neural network. The embedder will mostly be input type dependent, and there
    can be multiple embedders in a single network
    """
    def __init__(self,
                 input_size: List[int],
                 activation_function=tf.nn.relu,
                 scheme: EmbedderScheme = None,
                 batchnorm: bool = False,
                 dropout_rate: float = 0.0,
                 name: str = "embedder",
                 input_rescaling=1.0,
                 input_offset=0.0,
                 input_clipping=None,
                 is_training=False,
                 **kwargs):

        super(InputEmbedder, self).__init__(name=name)#, trainable=is_training)
        self.input_size = input_size
        self.return_type = InputEmbedding
        #self.input_rescaling = tf.cast(input_rescaling, tf.float32)
        self.input_rescaling = input_rescaling
        self.input_offset = input_offset
        self.input_clipping = input_clipping
        self.embbeder_layers = []

        if isinstance(scheme, EmbedderScheme):
            layers = self.schemes[scheme]
        else:
            layers = scheme
        # Convert layer to TensorFlow layer
        layers = [convert_layer(l) for l in layers]

        for layer in layers:
            self.embbeder_layers.extend([layer])
            if batchnorm:
                self.embbeder_layers.extend([keras.layers.BatchNormalization()])
            if activation_function:
                self.embbeder_layers.extend([keras.activations.get(activation_function)])
            if dropout_rate:
                self.embbeder_layers.extend([keras.layers.Dropout(rate=dropout_rate)])

    def call(self, inputs) -> Tensor:
        """
        Used for forward pass through embedder network.
        :param inputs: environment state, where first dimension is batch_size, then dimensions are data type dependent.
        :return: embedding of environment state, where shape is (batch_size, channels).
        """
        #self.input_rescaling = tf.cast(self.input_rescaling, inputs.dtype)
        inputs = tf.cast(inputs, tf.float32)
        x = tf.math.divide(inputs, self.input_rescaling)
        x = x - self.input_offset
        if self.input_clipping is not None:
            x = tf.clip_by_value(x, self.input_clipping[0], self.input_clipping[1])

        for layer in self.embbeder_layers:
            x = layer(x)

        # For convolution layer
        x = keras.layers.Flatten()(x)
        return x

    @property
    def input_size(self) -> List[int]:
        return self._input_size

    @input_size.setter
    def input_size(self, value: Union[int, List[int]]):
        if isinstance(value, np.ndarray) or isinstance(value, tuple):
            value = list(value)
        elif isinstance(value, int):
            value = [value]
        if not isinstance(value, list):
            raise ValueError((
                'input_size expected to be a list, found {value} which has type {type}'
            ).format(value=value, type=type(value)))
        self._input_size = value

    @property
    def schemes(self) -> dict:
        """
        Schemes are the pre-defined network architectures of various depths and complexities that can be used for the
        InputEmbedder. Should be implemented in child classes, and are used to create Block when InputEmbedder is
        initialised.

        :return: dictionary of schemes, with key of type EmbedderScheme enum and value being list of Tensorflow layers.
        """
        raise NotImplementedError("Inheriting embedder must define schemes matching its allowed default "
                                  "configurations.")

    def get_name(self) -> str:
        """
        Get a formatted name for the module
        :return: the formatted name
        """
        return self.name

    def get_config(self):
        config = super(InputEmbedder, self).get_config()
        config.update({'name': self.name})
        return config

    def __str__(self):
        result = ['Input size = {}'.format(self._input_size)]
        if self.input_rescaling != 1.0 or self.input_offset != 0.0:
            result.append('Input Normalization (scale = {}, offset = {})'.format(self.input_rescaling, self.input_offset))
        result.extend([str(l) for l in self.embbeder_layers])
        if not self.embbeder_layers:
            result.append('No layers')

        return '\n'.join(result)
