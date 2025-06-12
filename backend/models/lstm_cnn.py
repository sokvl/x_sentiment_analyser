from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class CNNLSTMModel(nn.Module):

    def __init__(
        self, vocab_size: int, embedding_dim: int, lstm_hidden_dim: int,
        num_classes: int, ticker_vocab_size: int, dropout: float,
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.ticker_embedding = nn.Embedding(ticker_vocab_size, embedding_dim)

        self.conv1 = nn.Conv1d(embedding_dim, 128, kernel_size=3, padding=1)
        self.conv2 = nn.Conv1d(embedding_dim, 128, kernel_size=4, padding=1)
        self.conv3 = nn.Conv1d(embedding_dim, 128, kernel_size=5, padding=2)

        self.lstm = nn.LSTM(
            128 * 3, lstm_hidden_dim,
            batch_first=True, bidirectional=True,
        )
        self.lstm2 = nn.LSTM(
            lstm_hidden_dim * 2, lstm_hidden_dim,
            batch_first=True, bidirectional=True,
        )

        self.dropout = nn.Dropout(dropout)
        self.fc1 = nn.Linear(lstm_hidden_dim * 2 + embedding_dim, 256)
        self.fc2 = nn.Linear(256, num_classes)

    def forward(self, x_text: torch.Tensor, x_ticker: torch.Tensor):
        # Text channel
        x_text = self.embedding(x_text).permute(0, 2, 1)
        x1 = F.relu(self.conv1(x_text))
        x1 = F.max_pool1d(x1, kernel_size=x1.size(2)).squeeze(2)

        x2 = F.relu(self.conv2(x_text))
        x2 = F.max_pool1d(x2, kernel_size=x2.size(2)).squeeze(2)

        x3 = F.relu(self.conv3(x_text))
        x3 = F.max_pool1d(x3, kernel_size=x3.size(2)).squeeze(2)
        x_text = torch.cat((x1, x2, x3), dim=1).unsqueeze(1)

        # Sequence modelling
        lstm_out, _ = self.lstm(x_text)
        lstm_out, _ = self.lstm2(lstm_out)
        lstm_out = lstm_out[:, -1, :]

        # Ticker embedding
        x_ticker = self.ticker_embedding(x_ticker).squeeze()
        if x_ticker.dim() == 1:
            x_ticker = x_ticker.unsqueeze(0)

        # Classification head
        x = torch.cat((lstm_out, x_ticker), dim=1)
        x = self.dropout(x)
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        return self.fc2(x)
