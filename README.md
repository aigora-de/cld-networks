# cld-networks
A simple demo of the idea in "Causal Leverage Density: A General Approach in Semantic Information", https://arxiv.org/pdf/2407.07335

The output or score is the absolute divergence between the original network and the "intervened" network folloing road closures, as measured by comparing all shortests paths. Presumably this could be changed to measure relative degradation (or improvement). Also, there are several factors that could be used to measure divergence, e.g. average journey times.

It should also be possible to update the weights on roads (links) after road closures, since diverted traffic flows would impact this.

## Requirements
Runs in Python 3.9

See requirements.txt to install dependencies.

## Data
You need some data. I downloaded UK Ordnance Survey data for the grid SZ (includes Isle of Wight) - https://osdatahub.os.uk/downloads/open/OpenRoads (no registration needed)

Download the GML 3 data and unzip to the data folder. This rough and ready script reads the road network data from a hardwired path, so please change it as needed.

## Performance
The script calculates all shortest paths for the entire weighted graph and this has time complexity O(N * (E + N log N)), which rapidly becomes infeasible (or at least very costly) for large networks. However, it should be possible to evaluate a localised sub-network of roads and also aggregating links to reduce the graph to have only actual junctions as nodes. 
