"""Structured learned velocity policy with zero motion at zero tracking error."""


def make_dual_pickup_policy():
    import torch

    class PickupPolicy(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.log_gain = torch.nn.Parameter(torch.zeros(6))
            self.close_head = torch.nn.Linear(6, 1)
            self.register_buffer('limits', torch.tensor([.35, .35, .25, .3, .3, .2]))

        def forward(self, features):
            # Independent positive learned gains prevent the unrelated-axis
            # biases observed in the initial dense network's -1 cm trial.
            error = torch.stack((features[..., 0], features[..., 1], features[..., 4],
                                 features[..., 2], -features[..., 3], features[..., 5]), dim=-1)
            phases = features[..., 7:13]
            phase = phases.argmax(-1)
            motion = torch.clamp(error * self.log_gain.exp(), -self.limits, self.limits)
            allowed = torch.ones_like(motion)
            allowed[..., :2] = ((phase >= 1) & (phase <= 3)).unsqueeze(-1)
            allowed *= (phase != 5).unsqueeze(-1)
            return torch.cat((motion * allowed, self.close_head(phases).tanh()), dim=-1)

    return PickupPolicy()


def make_single_pickup_policy(learn_pitch=False):
    import torch

    class SinglePickupPolicy(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.log_gain=torch.nn.Parameter(torch.zeros(5 if learn_pitch else 4))
            self.close_head=torch.nn.Linear(6,1)
            self.register_buffer('limits',torch.tensor([.25,.25,.3,.3]+([.2] if learn_pitch else [])))

        def forward(self,features):
            columns=[features[...,0],features[...,1],features[...,2],-features[...,3]]
            if learn_pitch:columns.append(features[...,11])
            error=torch.stack(columns,dim=-1)
            phases=features[...,5:11];phase=phases.argmax(-1)
            motion=torch.clamp(error*self.log_gain.exp(),-self.limits,self.limits)
            allowed=torch.ones_like(motion)
            allowed[...,:2]=((phase>=1)&(phase<=3)).unsqueeze(-1)
            allowed*=(phase!=5).unsqueeze(-1)
            motion=motion*allowed
            close=self.close_head(phases).tanh()
            return torch.cat((motion[...,:4],close,motion[...,4:]),dim=-1)

    return SinglePickupPolicy()
