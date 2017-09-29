import time
from numpy.testing import assert_allclose
import numpy.random
from ...neural._classes.maxout import Maxout
from ...neural._fast_maxout_cnn import MaxoutWindowEncode

numpy.random.seed(0)

def test_create():
    mwe = MaxoutWindowEncode(16, 4)


def test_fwd_runs():
    mwe = MaxoutWindowEncode(32, 4)
    X = mwe.ops.allocate((5, 32), dtype='f')
    y = mwe([X])[0]
    assert y.shape == X.shape
    assert y.sum() == 0.
    y += 2
    z = mwe([y])[0]
    assert z.sum() != 0.


def test_bwd_runs():
    mwe = MaxoutWindowEncode(32, 4)
    X = mwe.ops.allocate((5, 32), dtype='f')
    dy = mwe.ops.allocate((5, 32), dtype='f')
    y, bp_y = mwe.begin_update([X])
    dX = bp_y([dy])


def baseline_mwe(nO, nP, depth):
    from thinc.neural._classes.model import Model
    from thinc.neural._classes.resnet import Residual
    from thinc.neural._classes.convolution import ExtractWindow
    from thinc.neural._classes.layernorm import LayerNorm
    from thinc.api import chain, clone, with_flatten
    maxout = Maxout(nO, nO*3, pieces=nP)
    normalize = LayerNorm(maxout)
    with Model.define_operators({'>>': chain, '**': clone}):
        model = ExtractWindow(nW=1) >> normalize
        model = with_flatten(chain(*[model]*depth))
    model.maxout = maxout
    model.normalize = normalize
    return model


def test_fwd_correctness(nr_row=10, nr_dim=4, nr_piece=3):

    base = baseline_mwe(nr_dim, 3, 4)
    fast = MaxoutWindowEncode(nr_dim, 4)
    fast.maxout.W[:] = base.maxout.W
    fast.normalize.G[:] = base.normalize.G
    Xs = [fast.ops.normal_init(fast.ops.allocate((nr_row, nr_dim)), nr_dim)
          for _ in range(10)]
    Ys_new = fast(Xs)
    Ys_old = base(Xs)
    for Y1, Y2 in zip(Ys_new, Ys_old):
        assert_allclose(Y1, Y2, rtol=1e-4, atol=1e-4)

#def test_fwd_speed(nr_row=10, nr_dim=128, nr_piece=3):
#    mwe = MaxoutWindowEncode(nr_dim, 4)
#    Xs = [mwe.ops.allocate((nr_row, nr_dim)) for _ in range(10)]
#    start = time.clock()
#    ys = mwe(Xs)
#    end = time.clock()
#    print('Fwd Fast?', end, start, end-start)
#    mwe = baseline_mwe(nr_dim, nr_piece, 4)
#    flat_X = mwe.ops.flatten(Xs)
#    start = time.clock()
#    y = mwe(flat_X)
#    end = time.clock()
#    print('Fwd Slow?', end, start, end-start)

def test_bwd_speed(nr_row=10, nr_dim=128, nr_piece=3):
    mwe = MaxoutWindowEncode(nr_dim, 4)
    Xs = [mwe.ops.allocate((nr_row, nr_dim)) for _ in range(10)]
    start = time.clock()
    ys, bp_ys = mwe.begin_update(Xs)
    dx = bp_ys(Xs)
    end = time.clock()
    print('Fast?', end, start, '%.4f' % (end-start))
    mwe = baseline_mwe(nr_dim, nr_piece, 4)
    flat_X = mwe.ops.flatten(Xs)
    start = time.clock()
    ys, bp_ys = mwe.begin_update(flat_X)
    dx = bp_ys(flat_X)
    end = time.clock()
    print('Slow?', end, start, '%.4f' % (end-start))
