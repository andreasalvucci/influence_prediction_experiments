from typing import List
import torch
from torch import nn
import torch.nn.functional as F
import torchmetrics.retrieval as ir
from collections import defaultdict
import numpy as np
import random
import math
from math import factorial

from influence.ndcg import approxNDCGLoss

class BaseInfluencePredictor(nn.Module):
  TRAINABLE = None

  def __init__(self, num_relations: int, nodes: int, comunicability_degree: float = 8, device: str = "cuda:0"):
    super().__init__()
    self.device = device
    self.c_degree = comunicability_degree
    self.num_relations = num_relations
    self.nodes = nodes

  @property
  def relation_weight(self):
    raise NotImplementedError()
  
  @staticmethod
  def compute_communication_matrix_sparse(input_adj: torch.Tensor, power: int) -> torch.Tensor:

    # Get the non-zero indices of the input adjacency matrix (for sparse creation)
    initial_graph_indices = torch.nonzero(input_adj, as_tuple=False).t()
    
    # Get the non-zero values from the input adjacency matrix
    initial_graph_values = input_adj[initial_graph_indices[0], initial_graph_indices[1]]
    
    # Create a sparse matrix from the indices and values
    initial_graph_sparse = torch.sparse_coo_tensor(initial_graph_indices, initial_graph_values, input_adj.size())
    
    # Initialize the power graph as the sparse adjacency matrix
    initial_graph_sparse = initial_graph_sparse.coalesce()
    graph_power = initial_graph_sparse

    # Convert input_adj to dense to accumulate the result
    result_adj = input_adj

    # Compute higher powers of the sparse matrix
    for i in range(2, power + 1):
        # Perform sparse matrix multiplication
        graph_power = torch.sparse.mm(graph_power, initial_graph_sparse)
        
        # Calculate the coefficient (1/factorial(i))
        coeff = 1 / math.factorial(i)
        
        # Add the weighted power of the matrix to the result
        result_adj = result_adj + (coeff * graph_power.to_dense())
    
    # Return the dense matrix as the result
    return result_adj


  @staticmethod
  def compute_communication_matrix(input_adj: torch.tensor, power: int) -> torch.tensor:
    initial_graph = input_adj
    graph_power = input_adj
    for i in range(2, power + 1):
      graph_power = torch.mm(graph_power, initial_graph)
      coeff = torch.tensor(1 / factorial(i))
      input_adj = input_adj + (coeff * graph_power)
    
    return input_adj

  def forward(self, adj, target, mask_idx):
    raise NotImplementedError()

  def evaluate(self, adj, target, mask_idx, k: int = None):
    with torch.no_grad():
      loss, m = self.forward(adj, target, mask_idx)
    
    pred = m[mask_idx].reshape(-1)
    y = target[mask_idx].reshape(-1)

    hit_m = ir.RetrievalHitRate(top_k=k)
    mrr = ir.RetrievalMRR(top_k=k)
    map = ir.RetrievalMAP(top_k=k)
    dcg = ir.RetrievalNormalizedDCG(top_k=k)
    idxs = torch.tile(torch.arange(mask_idx.shape[0]), (adj.shape[1], 1)).T.reshape(-1)

    return loss, {
      f"H@{k}": hit_m(pred, y, indexes=idxs).item(),
      f"MRR@{k}": mrr(pred, y, indexes=idxs).item(),
      f"MAP@{k}": map(pred, y, indexes=idxs).item(),
      f"DCG@{k}": dcg(pred, y, indexes=idxs).item(),
    }
    

class UniformInfluencePredictor(BaseInfluencePredictor):
  TRAINABLE = False
  
  @property
  def relation_weight(self):
    return torch.ones(self.num_relations)

  def forward(self, adj, target, mask_idx):
    # combine weights (using sum)
    w_input = adj.sum(dim=0)
    w_input = self.compute_communication_matrix(w_input, self.c_degree)

    pred = w_input[mask_idx]
    y = target[mask_idx]
    
    loss = F.cross_entropy(pred, F.softmax(y, -1))
    return loss, w_input


class FrequencyInfluencePredictor(BaseInfluencePredictor):
  TRAINABLE = False
  
  @property
  def relation_weight(self):
    assert hasattr(self, "weights"), "Call forward first to estimate weights."
    return self.weights

  def forward(self, adj, target, mask_idx):
    # estimate weights
    counts = adj.sum(dim=(1, 2))
    self.weights = counts / adj.sum()

    # combine weights (using sum)
    w_input = adj * self.weights.reshape(-1, 1, 1)
    w_input = w_input.sum(dim=0)
    w_input = self.compute_communication_matrix(w_input, self.c_degree)

    pred = w_input[mask_idx]
    y = target[mask_idx]
    
    loss = F.cross_entropy(pred, F.softmax(y, -1))
    return loss, w_input


class InverseFrequencyInfluencePredictor(BaseInfluencePredictor):
  TRAINABLE = False
  
  @property
  def relation_weight(self):
    assert hasattr(self, "weights"), "Call forward first to estimate weights."
    return self.weights

  def forward(self, adj, target, mask_idx):
    # estimate weights
    counts = adj.sum(dim=(1, 2))
    self.weights = adj.sum() / counts

    # combine weights (using sum)
    w_input = adj * self.weights.reshape(-1, 1, 1)
    w_input = w_input.sum(dim=0)
    w_input = self.compute_communication_matrix(w_input, self.c_degree)

    pred = w_input[mask_idx]
    y = target[mask_idx]
    
    loss = F.cross_entropy(pred, F.softmax(y, -1))
    return loss, w_input


class FitInfluencePredictor(BaseInfluencePredictor):
  TRAINABLE = True

  def __init__(self, num_relations: int, nodes: int, comunicability_degree: float = 8, device: str = "cuda:0"):
    super().__init__(num_relations, nodes, comunicability_degree=comunicability_degree, device=device)
    self.relation_embedding = nn.Embedding(num_relations, 1)
    nn.init.constant_(self.relation_embedding.weight, 1)
    self.double()

  @property
  def relation_weight(self):
    w = self.relation_embedding.weight.reshape(-1)
    w = w + w.min()
    return w

  def forward(self, adj, target, mask_idx):
    # prepare a weight for each relation
    relations_idxs = torch.arange(self.num_relations).to(self.device)
    
    # compute weight of each relation
    relation_weight = self.relation_embedding(relations_idxs)
    relation_weight = relation_weight + relation_weight.min()
    
    # weight input by casting the weights to |R| x 1 x 1
    w_input = adj * relation_weight.reshape(-1, 1, 1)

    # combine weights (using sum)
    w_input = w_input.sum(dim=0)
    
    #compute comunicability up to X degree
    w_input = self.compute_communication_matrix(w_input, self.c_degree)
    
    pred = w_input[mask_idx]
    y = target[mask_idx]
    
    loss = F.cross_entropy(pred, F.softmax(y, -1))
    
    return loss, w_input


class DNNInfluencePredictor(FitInfluencePredictor):
  def __init__(self, num_relations: int, nodes: int, comunicability_degree: float = 8, device: str = "cuda:0"):
    super().__init__(num_relations, nodes, comunicability_degree=comunicability_degree, device=device)
    self.dnn = nn.Sequential(
      nn.Linear(num_relations, 256),
      nn.ReLU(),
      nn.Linear(256, 1)
    )
    self.double()

  def forward(self, adj, target, mask_idx):
    # prepare a weight for each relation
    relations_idxs = torch.arange(self.num_relations).to(self.device)
    
    # compute weight of each relation
    relation_weight = self.relation_embedding(relations_idxs)
    relation_weight = relation_weight + relation_weight.min()
    
    # weight input by casting the weights to |R| x 1 x 1
    w_input = adj * relation_weight.reshape(-1, 1, 1)
    w_input = torch.permute(w_input, (1, 2, 0))
    
    w_input = self.dnn(w_input).squeeze(2)
    
    #compute comunicability up to X degree
    w_input = self.compute_communication_matrix(w_input, self.c_degree)
    
    pred = w_input[mask_idx]
    y = target[mask_idx]
    
    loss = F.cross_entropy(pred, F.softmax(y, -1))
    
    return loss, w_input
  

# class DNNInfluencePredictor(FitInfluencePredictor):
#     def __init__(self, num_relations: int, nodes: int, comunicability_degree: float = 8, device: str = "cuda:0"):
#         super().__init__(num_relations, nodes, comunicability_degree=comunicability_degree, device=device)
#         self.dnn = nn.Sequential(
#             nn.Linear(num_relations, 256),
#             nn.ReLU(),
#             nn.Linear(256, 1)
#         )
#         self.double()

#     def forward(self, adj, target, mask_idx):
#         # Converti `adj` in matrice sparsa
#         sparse_adj = torch.sparse_coo_tensor(indices, values, adj.size()).to(self.device)
#         indices = sparse_adj._indices()  # Ottieni gli indici delle celle non nulle
#         values = sparse_adj._values()  # Ottieni i valori delle celle non nulle
        

#         # Prepara un peso per ciascuna relazione
#         relations_idxs = torch.arange(self.num_relations).to(self.device)

#         # Calcola il peso di ciascuna relazione
#         relation_weight = self.relation_embedding(relations_idxs)
#         relation_weight = relation_weight + relation_weight.min()

#         # Pesa l'input
#         w_input = sparse_adj * relation_weight.reshape(-1, 1, 1)
#         w_input = torch.permute(w_input.to_dense(), (1, 2, 0))  # Converti il tensore sparso in denso per la DNN

#         # Passa attraverso la rete DNN
#         w_input = self.dnn(w_input).squeeze(2)

#         # Calcola la comunicabilità fino a X grado
#         w_input = self.compute_communication_matrix(w_input, self.c_degree)

#         pred = w_input[mask_idx]
#         y = target[mask_idx]
        
#         loss = F.cross_entropy(pred, F.softmax(y, -1))
        
#         return loss, w_input

def print_coefficient_of_sparsity(adj: torch.Tensor) -> None:
    # Get the number of non-zero elements in the adjacency matrix
    num_nonzero_elements = torch.nonzero(adj).size(0)
    
    # Get the total number of elements in the adjacency matrix
    total_elements = adj.size(0) * adj.size(1)
    
    # Calculate the coefficient of sparsity
    coefficient_of_sparsity = num_nonzero_elements / total_elements
    
    # Print the coefficient of sparsity
    print(f"Coefficient of Sparsity: {coefficient_of_sparsity}")