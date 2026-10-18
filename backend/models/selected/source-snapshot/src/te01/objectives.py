"""Identical seeded exposure and explicit independent-solution positives."""
import random

import torch
from torch.nn import functional as F

from .data import can_pair, eligible_groups
from .io import digest


class PairSampler:
    def __init__(self, items, split, seed, problems=8):
        self.groups = eligible_groups(items, split)
        self.seed, self.problems = seed, problems
        if problems < 2 or len(self.groups) < problems:
            raise ValueError("Insufficient independent positive groups; singleton no-go")

    def draw(self, step):
        rng = random.Random(int(digest([self.seed, step]), 16))
        rows = []
        for problem in rng.sample(sorted(self.groups), self.problems):
            lineages = self.groups[problem]
            for lineage in rng.sample(sorted(lineages), 2):
                rows.append(rng.choice(sorted(lineages[lineage], key=lambda i: i["id"])))
        return rows


def pair_masks(items, device):
    n = len(items)
    valid = torch.zeros(n, n, dtype=torch.bool, device=device)
    positive = valid.clone()
    for i, a in enumerate(items):
        for j, b in enumerate(items):
            if i != j and can_pair(a, b):
                valid[i, j] = True
                positive[i, j] = a["problem_id"] == b["problem_id"]
    return valid, positive


def contrastive_loss(embeddings, items, temperature=.1):
    valid, positive = pair_masks(items, embeddings.device)
    if not positive.any(1).all() or not (valid & ~positive).any(1).all():
        raise ValueError("Each anchor requires an independent positive and an eligible negative")
    logits = F.normalize(embeddings, dim=-1) @ F.normalize(embeddings, dim=-1).T / temperature
    denominator = torch.logsumexp(logits.masked_fill(~valid, -torch.inf), dim=1)
    logp = logits - denominator[:, None]
    return -(logp.masked_fill(~positive, 0).sum(1) / positive.sum(1)).mean()


def scorer_loss(scorer, embeddings, items):
    valid, positive = pair_masks(items, embeddings.device)
    valid = torch.triu(valid, diagonal=1)
    pos, neg = valid & positive, valid & ~positive
    if not pos.any() or not neg.any():
        raise ValueError("Scorer needs independent positives and negatives")
    a, b = torch.where(valid)
    logits = scorer(embeddings[a], embeddings[b])
    labels = positive[a, b].float()
    losses = F.binary_cross_entropy_with_logits(logits, labels, reduction="none")
    return .5 * (losses[labels == 1].mean() + losses[labels == 0].mean())
