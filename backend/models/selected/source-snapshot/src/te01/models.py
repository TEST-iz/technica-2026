"""One tensor contract for pooled/ordered blocks and set/GINE/GATv2/GPS."""
from __future__ import annotations

from dataclasses import dataclass, fields

import torch
from torch import nn
from torch.nn import functional as F
from torch_geometric.nn import GATv2Conv, GINEConv, GPSConv, global_max_pool, global_mean_pool
from torch_geometric.utils import to_dense_batch

from .representation import Graph, Vocabulary


@dataclass
class TensorBatch:
    tokens: torch.Tensor
    instruction_block: torch.Tensor
    instruction_position: torch.Tensor
    block_graph: torch.Tensor
    edge_index: torch.Tensor
    edge_type: torch.Tensor
    structure: torch.Tensor

    def to(self, device):
        return TensorBatch(**{f.name: getattr(self, f.name).to(device) for f in fields(self)})


def collate(graphs, vocabulary, *, rich=True, typed=True, structural=True):
    if not graphs:
        raise ValueError("Empty minibatch")
    tokens, instruction_block, positions, block_graph, edges, kinds, structure = [], [], [], [], [], [], []
    offset = 0
    for gid, graph in enumerate(graphs):
        for bid, block in enumerate(graph.blocks):
            if not block:
                raise ValueError("Empty block")
            for pos, ins in enumerate(block):
                tokens.append(vocabulary.encode(ins if rich else [t for t in ins if t.startswith("mn:")]))
                instruction_block.append(offset + bid)
                positions.append(pos)
            block_graph.append(gid)
        structure.extend(graph.structure if structural else [[0.] * 7 for _ in graph.blocks])
        for u, v, k in graph.edges:
            edges.extend([(offset + u, offset + v), (offset + v, offset + u)])
            kinds.extend([k if typed else 0, k + 7 if typed else 7])
        for bid in range(len(graph.blocks)):
            edges.append((offset + bid, offset + bid))
            kinds.append(14)  # Synthetic self relation, distinct from actual CFG loops.
        offset += len(graph.blocks)
    max_fields = max(map(len, tokens))
    encoded = torch.zeros((len(tokens), max_fields), dtype=torch.long)
    for i, tok in enumerate(tokens):
        encoded[i, :len(tok)] = torch.tensor(tok)
    return TensorBatch(encoded, torch.tensor(instruction_block), torch.tensor(positions),
                       torch.tensor(block_graph), torch.tensor(edges, dtype=torch.long).T.contiguous(),
                       torch.tensor(kinds), torch.tensor(structure, dtype=torch.float32))


def mlp(dim):
    return nn.Sequential(nn.Linear(dim, 2 * dim), nn.GELU(), nn.Linear(2 * dim, dim))


class FunctionEncoder(nn.Module):
    def __init__(self, vocab_size, config):
        super().__init__()
        self.config = dict(config)
        d = config["dim"]
        self.embedding = nn.Embedding(vocab_size, d, padding_idx=0)
        self.instruction = nn.Sequential(nn.Linear(d, d), nn.GELU(), nn.LayerNorm(d))
        self.position = None
        self.ordered = None
        if config["block"] == "ordered":
            self.position = nn.Embedding(256, d)
            layer = nn.TransformerEncoderLayer(d, nhead=4, dim_feedforward=2 * d,
                                               dropout=config["dropout"], batch_first=True, norm_first=True)
            self.ordered = nn.TransformerEncoder(layer, 1, enable_nested_tensor=False)
        self.structure = nn.Linear(7, d, bias=False) if config["structural"] and config["graph"] != "set" else None
        self.edge_embedding = nn.Embedding(15, d) if config["graph"] != "set" else None
        self.layers, self.norms = nn.ModuleList(), nn.ModuleList()
        for _ in range(config["layers"]):
            kind = config["graph"]
            if kind == "set":
                layer = mlp(d)
            elif kind == "gine":
                layer = GINEConv(mlp(d), train_eps=True, edge_dim=d)
            elif kind == "gatv2":
                layer = GATv2Conv(d, d // 4, heads=4, edge_dim=d, add_self_loops=False,
                                  dropout=config["dropout"])
            elif kind == "gps":
                layer = GPSConv(d, GINEConv(mlp(d), train_eps=True, edge_dim=d), heads=4,
                                dropout=config["dropout"], norm="layer_norm", norm_kwargs={"mode": "node"})
            else:
                raise ValueError("Unsupported graph encoder")
            self.layers.append(layer)
            self.norms.append(nn.LayerNorm(d))
        self.dropout = nn.Dropout(config["dropout"])
        self.readout = nn.Sequential(nn.Linear(2 * d, d), nn.LayerNorm(d))

    def forward(self, batch, return_blocks=False):
        mask = batch.tokens != 0
        x = (self.embedding(batch.tokens) * mask.unsqueeze(-1)).sum(1) / mask.sum(1, keepdim=True).clamp_min(1)
        x = self.instruction(x)
        if self.ordered is not None:
            x = x + self.position(batch.instruction_position)
            dense, valid = to_dense_batch(x, batch.instruction_block)
            dense = self.ordered(dense, src_key_padding_mask=~valid)
            x = (dense * valid.unsqueeze(-1)).sum(1) / valid.sum(1, keepdim=True)
        else:
            x = global_mean_pool(x, batch.instruction_block)
        if self.structure is not None:
            x = x + self.structure(batch.structure)
        edges = self.edge_embedding(batch.edge_type) if self.edge_embedding is not None else None
        for layer, norm in zip(self.layers, self.norms):
            if self.config["graph"] == "gps":
                y = layer(x, batch.edge_index, batch=batch.block_graph, edge_attr=edges)
            elif self.config["graph"] == "set":
                y = layer(x)
            else:
                y = layer(x, batch.edge_index, edges)
            x = norm(x + self.dropout(F.gelu(y)))
        z = self.readout(torch.cat([global_mean_pool(x, batch.block_graph), global_max_pool(x, batch.block_graph)], -1))
        z = F.normalize(z, dim=-1)
        if return_blocks:
            return z, [F.normalize(x[batch.block_graph == i], dim=-1) for i in range(z.shape[0])]
        return z


class SymmetricMLP(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(2 * dim, dim), nn.GELU(), nn.Linear(dim, 1))

    def forward(self, left, right):
        return self.net(torch.cat([(left - right).abs(), left * right], -1)).squeeze(-1)


def block_alignment(left, right):
    """Symmetric mean-best block matching. A bounded adaptation, not cross-attention."""
    scores = F.normalize(left, dim=-1) @ F.normalize(right, dim=-1).T
    return .5 * (scores.max(0).values.mean() + scores.max(1).values.mean())
