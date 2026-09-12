"""Adapter for a TorchScript model: Dict[str, Tensor] observation -> (2,9) action.

The model must implement the same observation preprocessing used in training.
For other checkpoint formats, supply an adapter with the same load_policy API.
"""


def load_policy(*, checkpoint, observation_space, action_space):
    import torch
    if checkpoint is None:
        raise ValueError('This adapter requires --checkpoint pointing to a TorchScript model')
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = torch.jit.load(str(checkpoint), map_location=device).eval()

    class Policy:
        def reset(self):
            if hasattr(model, 'reset'):
                model.reset()

        def __call__(self, observation):
            with torch.inference_mode():
                action = model({key: torch.as_tensor(value, device=device)
                                for key, value in observation.items()})
            return action.detach().cpu().numpy()

    return Policy()
