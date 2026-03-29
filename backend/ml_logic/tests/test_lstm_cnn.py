import torch
from django.test import TestCase

from ml_logic.lstm_cnn import CNNLSTMModel


class CNNLSTMModelTests(TestCase):
    def setUp(self):
        self.model = CNNLSTMModel(
            vocab_size=1000,
            embedding_dim=64,
            lstm_hidden_dim=64,
            num_classes=3,
            ticker_vocab_size=10,
            dropout=0.1,
        )
        self.model.eval()

    def test_output_shape_single_sample(self):
        x_text = torch.randint(0, 1000, (1, 30))
        x_ticker = torch.tensor([1])
        output = self.model(x_text, x_ticker)
        self.assertEqual(output.shape, (1, 3))

    def test_output_shape_batch(self):
        x_text = torch.randint(0, 1000, (8, 30))
        x_ticker = torch.randint(0, 10, (8,))
        output = self.model(x_text, x_ticker)
        self.assertEqual(output.shape, (8, 3))

    def test_output_is_logits_not_probabilities(self):
        x_text = torch.randint(0, 1000, (1, 30))
        x_ticker = torch.tensor([0])
        output = self.model(x_text, x_ticker)
        # Logits can be negative and don't sum to 1
        self.assertFalse(torch.allclose(output.sum(dim=1), torch.tensor([1.0]), atol=0.01))

    def test_softmax_produces_valid_probabilities(self):
        x_text = torch.randint(0, 1000, (1, 30))
        x_ticker = torch.tensor([0])
        output = self.model(x_text, x_ticker)
        probs = torch.nn.functional.softmax(output, dim=1)
        self.assertTrue(torch.allclose(probs.sum(dim=1), torch.tensor([1.0]), atol=1e-5))
        self.assertTrue((probs >= 0).all())

    def test_padding_index_zero_produces_zero_embedding(self):
        # Padding index 0 should produce zero embeddings
        zero_input = torch.zeros(1, 30, dtype=torch.long)
        embedding = self.model.embedding(zero_input)
        self.assertTrue(torch.allclose(embedding, torch.zeros_like(embedding)))

    def test_different_inputs_produce_different_outputs(self):
        x_text1 = torch.randint(1, 1000, (1, 30))
        x_text2 = torch.randint(1, 1000, (1, 30))
        x_ticker = torch.tensor([1])
        out1 = self.model(x_text1, x_ticker)
        out2 = self.model(x_text2, x_ticker)
        # Very unlikely to be exactly the same with random inputs
        self.assertFalse(torch.allclose(out1, out2))

    def test_different_tickers_produce_different_outputs(self):
        x_text = torch.randint(1, 1000, (1, 30))
        out1 = self.model(x_text, torch.tensor([0]))
        out2 = self.model(x_text, torch.tensor([1]))
        self.assertFalse(torch.allclose(out1, out2))

    def test_model_parameter_count(self):
        total_params = sum(p.numel() for p in self.model.parameters())
        self.assertGreater(total_params, 0)

    def test_model_trainable_parameters(self):
        trainable = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        total = sum(p.numel() for p in self.model.parameters())
        self.assertEqual(trainable, total)

    def test_variable_sequence_lengths(self):
        for seq_len in [10, 30, 50]:
            x_text = torch.randint(0, 1000, (1, seq_len))
            x_ticker = torch.tensor([0])
            output = self.model(x_text, x_ticker)
            self.assertEqual(output.shape, (1, 3))

    def test_gradient_flow(self):
        self.model.train()
        x_text = torch.randint(0, 1000, (2, 30))
        x_ticker = torch.randint(0, 10, (2,))
        target = torch.tensor([0, 2])

        output = self.model(x_text, x_ticker)
        loss = torch.nn.functional.cross_entropy(output, target)
        loss.backward()

        has_grad = any(
            p.grad is not None and p.grad.abs().sum() > 0
            for p in self.model.parameters()
        )
        self.assertTrue(has_grad)
