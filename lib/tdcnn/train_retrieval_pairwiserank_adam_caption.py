# --------------------------------------------------------
# Text-to-Clip Retrieval
# Copyright (c) 2019 Boston Univ.
# Licensed under The MIT License [see LICENSE for details]
# By Huijuan Xu
# --------------------------------------------------------

"""Train a Text-to-Clip Retrieval network."""

import caffe
from tdcnn.config import cfg
import roi_data_layer.roidb as rdl_roidb
from utils.timer import Timer
import numpy as np
import os

from caffe.proto import caffe_pb2
import google.protobuf as pb2
import google.protobuf.text_format

class SolverWrapper(object):
    """A simple wrapper around Caffe's solver.
    This wrapper gives us control over the snapshotting process, which we
    use to unnormalize the learned time window regression weights.
    """

    def __init__(self, solver_prototxt, all_fc6, all_target_sent_reshaped, all_input_sent_reshaped, all_cont_sent_reshaped, output_dir,
                 pretrained_model=None):
        """Initialize the SolverWrapper."""
        self.output_dir = output_dir

        self.solver = caffe.AdamSolver(solver_prototxt)

        if pretrained_model is not None:
            print ('Loading pretrained model '
                   'weights from {:s}').format(pretrained_model)
            self.solver.net.copy_from(pretrained_model)

        self.solver_param = caffe_pb2.SolverParameter()
        with open(solver_prototxt, 'rt') as f:
            pb2.text_format.Merge(f.read(), self.solver_param)

        if not cfg.TRAIN.CINPUT:
            self.solver.net.layers[0].set_roidb(all_fc6, all_target_sent_reshaped, all_input_sent_reshaped, all_cont_sent_reshaped)

    def snapshot(self):
        """Take a snapshot of the network after unnormalizing the learned
        time windows regression weights. This enables easy use at test-time.
        """
        net = self.solver.net
        
        infix = ('_' + cfg.TRAIN.SNAPSHOT_INFIX
                 if cfg.TRAIN.SNAPSHOT_INFIX != '' else '')
        filename = (self.solver_param.snapshot_prefix + infix +
                    '_iter_{:d}'.format(self.solver.iter) + '.caffemodel')

        net.save(str(filename))
        print 'Wrote snapshot to: {:s}'.format(filename)
        return filename

    def train_model(self, max_iters):
        """Network training loop."""
        last_snapshot_iter = -1
        timer = Timer()
        model_paths = []
        while self.solver.iter < max_iters:
            # Make one SGD update
            timer.tic()
            self.solver.step(1)
            timer.toc()
            if self.solver.iter % (10 * self.solver_param.display) == 0:
                print 'speed: {:.3f}s / iter'.format(timer.average_time)

            if self.solver.iter % cfg.TRAIN.SNAPSHOT_ITERS == 0:
                last_snapshot_iter = self.solver.iter
                model_paths.append(self.snapshot())

        if last_snapshot_iter != self.solver.iter:
            model_paths.append(self.snapshot())
        return model_paths



def train_net(solver_prototxt, all_fc6, all_target_sent_reshaped, all_input_sent_reshaped, all_cont_sent_reshaped, output_dir,
              pretrained_model=None, max_iters=40000):

    sw = SolverWrapper(solver_prototxt, all_fc6, all_target_sent_reshaped, all_input_sent_reshaped, all_cont_sent_reshaped, output_dir, pretrained_model=pretrained_model)

    print 'Solving...'
    model_paths = sw.train_model(max_iters)
    print 'done solving'
    return model_paths


