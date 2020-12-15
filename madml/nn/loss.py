from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import madml
from madml import tensor, zeros_like, zeros
from .module import Module
from typing import Optional, List
import math


def _size(shape: List[int]) -> int:
    size = 1
    for s in shape:
        size *= s
    return size


def regularization(reg_type='l2', lam=1e-3):
    reg_lambda = dict()[reg_type]
    return 1


class _Loss(Module):
    reduction: str

    def __init__(self, size_average=None, reduce=None, reduction: str = 'mean', backend=None) -> None:
        super(_Loss, self).__init__(backend)
        if size_average is not None or reduce is not None:
            self.reduction = None  # _Reduction.legacy_get_string(size_average, reduce)
        else:
            self.reduction = reduction


class _WeightedLoss(_Loss):
    def __init__(self, weight=None, size_average=None, reduce=None, reduction: str = 'mean') -> None:
        super(_WeightedLoss, self).__init__(size_average, reduce, reduction)
        self.weight = weight


class CrossEntropyLoss(_WeightedLoss):
    __constants__ = ['ignore_index', 'reduction']
    ignore_index: int

    def __init__(self, weight: Optional[tensor] = None, size_average=None, ignore_index: int = -100,
                 reduce=None, reduction: str = 'mean') -> None:
        super(CrossEntropyLoss, self).__init__(weight, size_average, reduce, reduction)
        self.args = None
        self.ignore_index = ignore_index
        self.exps = None
        self.loss = tensor([0], [1])

    def forward_cpu(self, logit: tensor, target: tensor) -> tensor:
        batchsize = logit.shape[0]
        if self.args is None:
            pass

        # MAX
        max = 0
        for i in range(logit.size):
            max = logit.host_data[i] if logit.host_data[i] > max else max

        # REDUCE_SUM
        reduce_sum = zeros(logit.shape[:1])
        upper = _size(logit.shape[:1])
        lower = _size(logit.shape[1:])
        for i in range(upper):
            acc = 0
            for j in range(lower):
                acc += logit.host_data[i * lower + j]
            reduce_sum.host_data[i] = acc

        # PROBABILITY
        prob = zeros_like(logit)
        for i in range(upper):
            for j in range(lower):
                prob.host_data[i * lower + j] = math.exp(logit.host_data[i * lower + j] - max)
            mu = 0
            for j in range(lower):
                mu += prob.host_data[i * lower + j]
            for j in range(lower):
                prob.host_data[i * lower + j] /= mu

        # LOG FN
        log_like = zeros_like(logit)
        for i in range(upper):
            for j in range(lower):
                log_like.host_data[i * lower + j] = -math.log(prob.host_data[i*lower + target.host_data[i]])

        self.loss.host_data[0] = 0
        for x in range(logit.size):
            self.loss.host_data[0] += logit.host_data[x] / batchsize

        self.cache.append(logit)
        self.cache.append(target)
        self.cache.append(prob)

        return self.loss

    def backward_cpu(self) -> tensor:
        logit, target, grad_y, m = self.cache

        upper = _size(logit.shape[:1])
        lower = _size(logit.shape[1:])

        for i in range(upper):
            for j in range(lower):
                grad_y.host_data[i*lower + target.host_data[i]] -= 1.
                grad_y.host_data[i * lower + target.host_data[i]] /= m

        return grad_y