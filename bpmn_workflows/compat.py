import networkx as nx

# provide networkx 1.x aliases used by bpmn_python
if not hasattr(nx.Graph, 'node'):
    nx.Graph.node = property(lambda self: self._node)
if not hasattr(nx.DiGraph, 'node'):
    nx.DiGraph.node = property(lambda self: self._node)
if not hasattr(nx.Graph, 'edge'):
    nx.Graph.edge = property(lambda self: self._adj)
if not hasattr(nx.DiGraph, 'edge'):
    nx.DiGraph.edge = property(lambda self: self._adj)
