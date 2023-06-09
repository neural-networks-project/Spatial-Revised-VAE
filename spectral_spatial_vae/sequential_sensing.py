"""
Sequential sensing using the proposed LSTM model.

Authors: Brock Dyer, Dade Wood
CSCI 736
"""

import torch
import torch.nn as nn


class ExtractLSTMOutput(nn.Module):
    """Extractor for taking out LSTM output data."""
    def forward(self, x):
        output, _ = x
        return output


class SequentialSensingNet(nn.Module):

    def __init__(self, s, ld, spectral_bands, lstm_layers=3) -> None:
        """
        The LSTM network for sequential sensing.

        The input of this network is a sxsxN neighborhood region around the pixel
        vector which is Nx1.

        The output of this network is an (ld/4)x1 vector containing the sequential
        spacial features used to modify the mean and std. dev. of the VAE.

        Note that each layer of the LSTM is modeled similarly to a CNN, where each
        layer works on a smaller dimensional region.

        Parameters
        ----------
        s
            The size of the neighborhood window. Paper suggests a size of 11.
        ld
            The size of the latent representation. This is also used for the size
            of hidden layers.
        spectral_bands
            The number of hyperspectral bands.
        lstm_layers
            The number of stacked LSTM layers. Paper suggests 3 as a default.
        """
        super(SequentialSensingNet, self).__init__()
        self.window_size = s

        # Setup stacked LSTM
        extractor = ExtractLSTMOutput()
        if lstm_layers == 1:
            stack = nn.LSTM(input_size=spectral_bands, hidden_size=ld // 4,
                            num_layers=lstm_layers, batch_first=True)
            self.lstm_stack = nn.Sequential(stack, extractor)
        else:
            stack = nn.LSTM(input_size=spectral_bands, hidden_size=ld,
                            num_layers=lstm_layers - 1, batch_first=True)
            final = nn.LSTM(input_size=ld, hidden_size=ld // 4,
                            num_layers=1, batch_first=True)
            self.lstm_stack = nn.Sequential(stack, extractor, final, extractor)

        # Pooling needs to get (1, ld // 4)
        # Need to average along the s x s dimension.
        self.average_pooling = nn.AvgPool1d(s * s)
        self.activation = nn.Sigmoid()

    def forward(self, x):
        """
        Perform the forward pass.

        Parameters
        ----------
        x
            The input data.
            This should be a tensor of the shape (s^2, N) where s is the window
            size, and N is the number of spectral bands.

        Returns
        -------
        A (ld/4)x1 vector of sequential spatial features.
        """

        # Run forward pass through LSTM, outputs a tensor (s^2, ld)
        lstm_output = self.lstm_stack(x)

        # Transpose output so that we can do average pooling
        lstm_output_t = torch.transpose(lstm_output, 1, 2)

        # Perform average pooling
        pooled = self.average_pooling(lstm_output_t)

        # Activation layer
        result = self.activation(pooled)

        return result

