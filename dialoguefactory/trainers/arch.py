#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This module has been adapted from the code provided in the YSDA course in Natural Language Processing
# which is licensed under the MIT License.
# Modifications have been made to the original code.
#
# Original repository: https://github.com/yandexdataschool/nlp_course
#
# Original license notice:
#

# MIT License
#
# Copyright (c) 2018 Yandex School of Data Analysis
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
This module offers classes that implement different machine learning models.
"""
import torch.nn as nn
import torch.nn.functional as F

import torch
import random


class Seq2SeqContModel(nn.Module):
    """
    A sequence-to-sequence model
    (paper reference: "Sequence to Sequence Learning with Neural Networks" by Sutskever, Vinyals and Le).

    This class can be used both for continual and non-continual training.
    For continual learning, the previous encoder's hidden state will be passed to the encoder.
    For non-continual training, the encoder's hidden state will be set to None.

    The model consists of:

        #. A trainable embedding layer that converts the input integers into a vector.
        #. A Gated Recurrent Unit (GRU) for encoding the input.
        #. Linear unit for converting the encoder state size into the decoder state size. This is done because
           the encoder state is input into the decoder, and
           the encoder state size might differ from the decoder state size.
        #. A trainable embedding layer that converts the output integers into a vector.
        #. The GRU decoder takes the output vector and the previous decoder's hidden state to output the next hidden state.
        #. The linear layer is used for converting the decoder's hidden state into the output size vector. The output
           size is the size of the output vocabulary. Later, the softmax is used to compute the probability of each
           output word from the vocabulary.


    Attributes
    ----------
    input_size : int
        The size of the input vocabulary.
    output_size : int
        The size of the output vocabulary.
    embed_size : int
        The size of the input/output embedding layer.
    encoder_hidden_size : int
        The size of the encoder's hidden state.
    decoder_hidden_size : int
        The size of the decoder's hidden state.
    num_layers : int
        The number of layers of the GRU encoder network.

    """

    def __init__(self,
                 input_size,
                 embed_size,
                 encoder_hidden_size,
                 decoder_hidden_size,
                 output_size,
                 num_layers):

        super().__init__()
        self.input_size = input_size
        self.output_size = output_size
        self.encoder_hidden_size = encoder_hidden_size
        self.decoder_hidden_size = decoder_hidden_size
        self.embed_size = embed_size
        self.num_layers = num_layers

        self.emb_input = nn.Embedding(self.input_size, self.embed_size)
        self.encoder = nn.GRU(self.embed_size, self.encoder_hidden_size, num_layers=self.num_layers, batch_first=True)
        self.dec_begin = nn.Linear(self.encoder_hidden_size, self.decoder_hidden_size)
        self.emb_output = nn.Embedding(self.output_size, self.embed_size)
        self.decoder = nn.GRUCell(self.embed_size, self.decoder_hidden_size)
        self.logits = nn.Linear(self.decoder_hidden_size, self.output_size)

    def encode(self, inp, hid_state, eos_ix):
        """
        Encodes the input into a single hidden state. Since a single input is a sequence of multiple values,
        multiple encoding states will be produced. Only the last non-padding one is input into the decoder.

        Parameters
        ----------
        inp : torch.LongTensor (batch_size x max_input_length)
            The input tensor.
        hid_state : torch.Tensor (1 x batch_size x self.encoder_hidden_size)
            The previous encoder's hidden state. If it's the first time running, the hid_state should be None.
        eos_ix : int
            The position of the end-of-string symbol in the input vocabulary. This symbol is used to
            exclude the encoder states that are positioned where the input padding symbols are.

        Returns
        -------
        dec_begin : torch.Tensor (batch_size x decoder_hidden_size)
            The last step of the encoding is to run the encoder state through a Linear layer to convert it to the
            size of the decoder's hidden state. The output of the linear layer is returned.
        enc_last : torch.Tensor (1 x batch_size x encoder_hidden_size)
            The last step of the encoding.
        """
        emb_in = self.emb_input(inp)
        enc_seq, _ = self.encoder(emb_in, hid_state)
        mask = infer_mask(inp, eos_ix).byte()
        end_index = mask.sum(dim=1)
        end_index[end_index >= inp.shape[1]] = inp.shape[1] - 1
        enc_last = enc_seq[range(0, enc_seq.shape[0]), end_index.detach(), :]
        dec_begin = self.dec_begin(enc_last)
        enc_last = enc_last.unsqueeze(0)

        return dec_begin, enc_last

    def decode(self, prev_out, prev_hidden):
        """
        Computes the next output logit-s and the decoder hidden state.

        The previous decoder output and the previous decoder's hidden state are input in the decoder.

        Parameters
        ----------
        prev_out : torch.Tensor
            It's a tensor consisting of a single integer representing the previous output produced by the decoder.
            If the previous output does not exist, the begging-of-string is used.
        prev_hidden : torch.Tensor (batch_size x decoder_hidden_size)
            The hidden decoder state from the previous step.
            If there is no previous step, the encoder's hidden state is input in the decoder.

        Returns
        -------
        dec_hidden : torch.Tensor (batch_size x decoder_hidden_size)
            The dec_hidden is the hidden state outputted by the decoder.
        logits : torch.Tensor (batch_size x output_voc_size)
            The logit layer converts the decoder's hidden state into a vector that has the size of the output vocabulary.
            They are later run through a softmax function to acquire the probabilities of each word in the vocabulary.

        """
        emb_out = self.emb_output(prev_out)
        dec_hidden = self.decoder(emb_out, prev_hidden)
        logits = self.logits(dec_hidden)

        return dec_hidden, logits

    def translate(self, inp, enc_hid_state, bos_ix, eos_ix, max_len=None, greedy=False):
        """
        Runs the input through the model in order to get the outputs and the logits that are necessary
        for computing the loss function.

        Parameters
        ----------
        inp : torch.LongTensor (batch_size x max_input_length)
            The input tensor.
        enc_hid_state : torch.Tensor (1 x batch_size x self.encoder_hidden_size)
            The previous encoder's hidden state. If it is the first time running the function, this parameter can be None.
        bos_ix : int
            The index of the beginning-of-string (bos) symbol in the output vocabulary. This parameter is used to start
            the decoding process.
        eos_ix : int
            The index of the end-of-string (eos) symbol in the input vocabulary. The eos pads the input
            sequences so that they have equal size.
        max_len : int
            The number of outputs to be made by the decoder. This number corresponds to the longest output sequence in the
            dataset.
        greedy : bool
            If True during the decoding process, the output which has the highest probability is selected.
            Otherwise, a random output based on each of the output probabilities is selected.

        Returns
        -------
        out_seq : torch.Tensor (batch_size x max_len)
            The sequence of outputs for each batch.
        logits_seq : torch.Tensor (batch_size x max_len x self.output_size )
            The logits are used for computing the probabilities of the words in the output vocabulary and when computing
            the loss function.
        enc_hid_state : torch.Tensor (1 x batch_size x self.encoder_hidden_size)
            The previous encoder state. It is used during continual learning. If the previous state does not
            exist, then the enc_hid_state is None.
        """

        batch_size = inp.shape[0]
        dec_hidden, enc_hid_state = self.encode(inp, enc_hid_state, eos_ix)
        hid_state = dec_hidden
        logits_seq = []
        out_seq = []
        out_last = torch.LongTensor([bos_ix] * batch_size)
        for i in range(max_len):
            hid_state, logits = self.decode(out_last, hid_state)
            probs = F.softmax(logits, dim=-1)
            if greedy:
                _, y_t = torch.max(probs, dim=-1)
            else:
                y_t = torch.multinomial(probs, 1)[:, 0]
            out_seq.append(y_t)
            logits_seq.append(logits)
            out_last = out_seq[-1]

        return torch.stack(out_seq, 1), torch.stack(logits_seq, 1), enc_hid_state


def compute_loss(model, batch_x, batch_y, input_voc, output_voc, max_len, enc_hid_state):
    """
    Computes the loss for a single batch using the negative log-likelihood (nll) measure:

    .. math:: - \Sigma\,log(y\hat{}\,) * y

    where :math:`y\hat{}\,` is the model prediction, and :math:`y` is the correct output.

    Parameters
    ----------
    model : Seq2SeqContModel
        The model that is used for training.
    batch_x : list of lists
        A list of input data points. A single input datapoint is a list of integers.
        It is padded with the input_voc.eos_ix, so that all input data points have the same length.
    batch_y : list of lists
        A list of output data points. A single inner list represents the output data point.
    input_voc : Vocabulary
        The input vocabulary is needed to fetch the end-of-string (eos) symbol, which pads the input
        sequences.
    output_voc : Vocabulary
        The output vocabulary is needed to fetch the end-of-string (eos) symbol, which is used to start the
        decoding (outputting) process.
        Also, the eos symbols in the output sequence are not included in the computation of the loss function.
    max_len : int
        The number of outputs in a single output sequence.
    enc_hid_state: torch.Tensor
        Since the training process is continuous, the last encoded state from the previous batch is saved, and
        input back into the model.

    Returns
    -------
    loss : float
        The computed loss function.
    enc_hid_state : torch.Tensor
        The encoded hidden state is needed for the next batch.

    """
    batch_x = torch.LongTensor(batch_x)
    batch_y = torch.LongTensor(batch_y)
    _, logits, enc_hid_state = model.translate(batch_x, enc_hid_state, output_voc.bos_ix,
                                               input_voc.eos_ix, max_len, greedy=True)
    logprobs = F.log_softmax(logits, dim=-1)
    nll = - torch.sum(logprobs * to_one_hot(batch_y, len(output_voc)), dim=-1)
    mask = infer_mask(batch_y, output_voc.eos_ix).float()
    loss = torch.sum(mask * nll) / torch.sum(mask)
    return loss, enc_hid_state


def generate_batch(data_x, data_y, batch_size, shuffle=True):
    """
    A generator that yields the next batch from the dataset.

    Parameters
    ----------
    data_x : list of lists
        A list containing the input sequences. Each input sequence consists of a list of integers.
    data_y : list of lists
        A list containing the output sequences. Each output sequence consists of a list of integers.
    batch_size : int
        The size of the batch. Each batch contains one or more elements.
    shuffle : bool
        Whether to shuffle the elements in the batch.

    Yields
    -------
    batch_x : list
        A list of input sequences.
    batch_y : list
        A list of output sequences.
    """
    perm = list(range(len(data_x)))
    if shuffle:
        random.shuffle(perm)

    for i in range(0, len(data_x), batch_size):
        batch_x = [data_x[j] for j in perm[i:i+batch_size]]
        batch_y = [data_y[j] for j in perm[i:i+batch_size]]
        yield batch_x, batch_y


def infer_mask(out, eos_ix, include_eos=True):
    """ Computes a tensor of 0s and 1s in such a way that 1s are non-padding elements of the original tensor.
        Once the padding element is detected in the sequence, all elements that come after are ignored.

        Parameters
        ----------
        out : torch.LongTensor (batch_size x n_dims)
            The input or output tensor.
        eos_ix : int
            The index of the padding symbol in the vocabulary.
        include_eos : bool
            If include_eos is True, the first occurrence of the padding symbol is not ignored from the sequence.
            All other elements following the padding symbol are ignored.

        Returns
        -------
        mask : torch.FloatTensor
            Float tensor of 0s and 1s. The tensor is float because it is used when computing the loss function.
    """
    mask = (out == eos_ix).float()
    if include_eos:
        mask = torch.cat((mask[:, :1]*0, mask[:, :-1]), dim=1)
    mask = mask.cumsum(dim=-1)
    mask = (mask == 0)
    mask = mask.float()
    return mask


def to_one_hot(y, n_dims=None):
    """ Take the integer y (tensor or variable) with n dimensions and
        convert it to 1-hot representation with n+1 dimensions. """
    y_tensor = y
    y_tensor = y_tensor.type(torch.LongTensor).view(-1, 1)
    n_dims = n_dims if n_dims is not None else int(torch.max(y_tensor)) + 1
    y_one_hot = torch.zeros(y_tensor.size()[0], n_dims).scatter_(1, y_tensor, 1)
    y_one_hot = y_one_hot.view(*y.shape, -1)

    return y_one_hot
