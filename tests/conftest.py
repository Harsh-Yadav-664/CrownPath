"""Tests call graph.reset(), which wipes the graph named by CROWNPATH_GRAPH. Default
to a scratch graph so running pytest can never empty the graph the live demo reads.
Set CROWNPATH_GRAPH explicitly to override."""
import os

os.environ.setdefault("CROWNPATH_GRAPH", "crownpath_test")
