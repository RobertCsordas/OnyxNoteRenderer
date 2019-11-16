import numpy as np

def moving_average(bdata, window_size):
    if window_size<=1 or bdata.shape[0] < 4:
        return bdata

    window_size = min(bdata.shape[0], window_size)

    before = window_size // 2
    after = window_size - before - window_size % 1

    first = (window_size * bdata[:1] - bdata[:after].sum(axis=0, keepdims=True)) / before
    last = (window_size * bdata[-1:] - bdata[-before:].sum(axis=0, keepdims=True)) / after

    bpad = [first] * before
    epad = [last] * after

    bdata = np.concatenate((*bpad, bdata, *epad), axis=0)

    csum = np.cumsum(bdata, 0)
    bdata = csum[window_size:] - csum[:-window_size]

    return bdata / window_size


def subsample(bdata, subsample):
    if subsample<=1:
        return bdata

    if bdata.shape[0] % subsample != 0:
        last = bdata[-1:]
        bdata = np.concatenate((bdata, *([last] * (subsample - bdata.shape[0] % subsample))), axis=0)

    bdata = bdata.reshape(-1, subsample, *bdata.shape[1:])
    return bdata.mean(1)


def smoothen(bdata, window_size, n_subsample):
    bdata = moving_average(bdata, window_size)
    bdata = subsample(bdata, n_subsample)
    return bdata
