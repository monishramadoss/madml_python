from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import math

import numpy as np

from madml import tensor, zeros, kaiming_uniform
from .module import Module, Parameter


class Linear(Module):
    __constants__ = ['in_features', 'out_features']
    in_features: int
    out_features: int

    def __init__(self, in_features: int, out_features: int, bias: bool = True) -> None:
        super(Linear, self).__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.weight = Parameter(kaiming_uniform(a=math.sqrt(5), nonlinearity='linear'), [in_features, out_features])
        self.bias = Parameter(zeros, [out_features]) if bias else None

    def forward_cpu(self, x: tensor) -> tensor:
        y = zeros([x.shape[0], self.out_features])

        y.host_data = x.host_data @ self.weight.param.host_data
        if self.bias is not None:
            y.host_data += self.bias.param.host_data

        self.cache = [x, y]
        return y

    def backward_cpu(self) -> tensor:
        x, y = self.cache
        dx, dy = x.gradient, y.gradient

        if self.bias is not None:
            self.bias.param.gradient.host_data = np.sum(dy.host_data, axis=0)

        self.weight.param.gradient.host_data = x.host_data.T @ dy.host_data
        x.gradient.host_data = dy.host_data @ self.weight.param.host_data.T
        y.zero_grad()
        return x

    def print_l(self) -> None:
        x, y = self.cache
        super(Linear, self).print_l()
        print('\tmax input:', x.host_data.max(), 'g', x.gradient.host_data.max(),
              ' weight:', self.weight.param.host_data.max(), 'g', self.weight.param.gradient.host_data.max(),
              ' output:', y.host_data.max(), 'g', y.gradient.host_data.max())
        print('\tmin input:', x.host_data.min(), 'g', x.gradient.host_data.min(),
              ' weight:', self.weight.param.host_data.min(), 'g', self.weight.param.gradient.host_data.min(),
              ' output:', y.host_data.max(), 'g', y.gradient.host_data.min())

    def test(self):
        x, y = self.cache
        import hipsternet.hipsternet.layer as hl
        y_hat, c = hl.fc_forward(x.host_data, self.weight.param.host_data, self.bias.param.host_data)
        dy_hat = hl.fc_backward(x.gradient.host_data, c)
        y.host_data == y_hat
        assert (dy_hat == y.gradient.host_data)