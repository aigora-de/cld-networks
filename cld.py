import random
import uuid
import networkx as nx
from networkx import NetworkXError
from lxml import etree
import numpy as np


# Create an empty NetworkX graph
g = nx.Graph()

# Parse the GML file
tree = etree.parse('data/oproad_gml3_gb/data/OSOpenRoads_SZ.gml')

# Define the namespaces used in your GML
ns = {
    'road': 'http://namespaces.os.uk/Open/Roads/1.0',
    'net': 'urn:x-inspire:specification:gmlas:Network:3.2',
    'xlink': 'http://www.w3.org/1999/xlink'
}

min_length = 1000000000
max_length = 0

# Iterate through each RoadLink element in th tree
for road_link in tree.xpath('//road:RoadLink', namespaces=ns):
    # Extract the startNode and endNode elements
    start_node_element = road_link.find('net:startNode', namespaces=ns)
    end_node_element = road_link.find('net:endNode', namespaces=ns)

    # Extract the xlink:href attributes
    start_node_id = start_node_element.get('{http://www.w3.org/1999/xlink}href')[2:]
    end_node_id = end_node_element.get('{http://www.w3.org/1999/xlink}href')[2:]

    # Extract the length element
    length_element = road_link.find('road:length', namespaces=ns)
    length_value = int(length_element.text) if length_element is not None else None
    if length_value < min_length:
        min_length = length_value
    if length_value > max_length:
        max_length = length_value
    #print(f"RoadLink Start Node: {start_node_id}, End Node: {end_node_id}")
    # Generate UUID for the new edge
    edge_id = str(uuid.uuid4())
    # Add the edge (road)
    g.add_edge(start_node_id, end_node_id, id=edge_id, weight=length_value)

# Print the maximum and minimum edge (road) lengths
print(f"Min length: {min_length}")
print(f"Max length: {max_length}")

# Find all connected components in the graph `g`
connected_components = list(nx.connected_components(g))
print(f"Number of connected components: {len(connected_components)}")
# Find the largest connected component
largest_component = max(connected_components, key=len)
print(f"Number of nodes in the largest connected component: {len(largest_component)}")
# Find the smallest connected component
smallest_component = min(connected_components, key=len)
print(f"Number of nodes in the smallest connected component: {len(smallest_component)}")

# Get all connected components and their sizes
component_sizes = [len(component) for component in nx.connected_components(g)]

# Print the sizes of all components
print("Sizes of all connected components:", component_sizes)

# The subgraph at index 37 has 677 nodes and 779 edges (roads) - let's use it for a demo
subgraph = g.subgraph(connected_components[37]).copy()


def random_edge(graph, min_edges=3, max_edges=7):
    """
    Deprecated: the demo simply removes some number of edges between nodes to simulate closed roads.

    Select a random path (roads) in `graph`

    :param graph: a graph object representing the road network
    :param min_edges: the minimum number of edges to select
    :param max_edges: the maximum number of edges to select
    :return: the path of edges selected
    """
    syytart_node = random.choice(list(graph.nodes))
    path = [start_node]

    while len(path) < max_edges:
        neighbors = list(graph.neighbors(path[-1]))
        if not neighbors or (len(path) >= min_edges and random.random() < 0.5):
            break
        next_node = random.choice(neighbors)
        if next_node not in path:  # Avoid cycles
            path.append(next_node)

    return path


# Function to get shortest path length
def get_all_shortest_paths(graph):
    """
    Get all shortest paths between all pairs of nodes in the graph

    Note for weighted graphs this has time complexity O(N + E log E) where N is the number of nodes and E is the number
    of edges in the graph. In other words, this is expensive to calculate for large real-world networks. However, for
    local sub-networks of a few thousand nodes and edges, this is feasible.

    :param graph:
    :return:
    """
    paths = dict(nx.all_pairs_shortest_path_length(graph))
    return paths


def calculate_divergence(original_paths, intervened_paths):
    """
    Calculate the divergence between the original shortest paths and the intervened shortest paths using the length of
    the shortest paths. The divergence is calculated as the sum of the absolute differences between the original and
    intervened shortest paths.

    Note: cf. paper, "Causal Leverage Density: A General Approach to Semantic Information",
    https://arxiv.org/pdf/2407.07335

    :param original_paths: all shortest paths between all node pairs in the original graph
    :param intervened_paths:
    :return:
    """
    divergence = 0
    for node in original_paths:
        for target in original_paths[node]:
            if node != target:
                original_length = original_paths[node].get(target, np.inf)
                intervened_length = intervened_paths[node].get(target, np.inf)
                if original_length != np.inf and intervened_length != np.inf:
                    if original_length != intervened_length:
                        divergence += abs(original_length - intervened_length)
    return divergence


closed_roads = []
# create closed roads by calling random_edge()
min_closed_roads = 3
max_closed_roads = 13

# Pick a random number between min_closed_roads and max_closed_roads
num_closed_roads = random.randint(min_closed_roads, max_closed_roads)
print(f"Number of closed roads: {num_closed_roads}")

# Initialise a counter for the number of closed roads
i = num_closed_roads
while i > 0:
    try:
        # Pick a random node
        start_node = random.choice(list(subgraph.nodes))
        # Get the start_node's neighbours
        neighbors = list(subgraph.neighbors(start_node))
        if neighbors:
            # Pick a random neighbour, i.e. linked to start_node with an edge
            end_node = random.choice(neighbors)
            # Add the "road" (edge) between start_node and end_node to the list of closed roads
            closed_roads.append((start_node, end_node))
            # Reduce the counter by 1
            i -= 1
    except NetworkXError:
        pass

    """
    try:
        # Pick two random nodes
        node1 = random.choice(list(subgraph.nodes))
        node2 = random.choice(list(subgraph.nodes))
        # Find the shortest path between the two nodes
        # Use weight=None for unweighted
        shortest_path = nx.shortest_path(g, source=node1, target=node2, weight='weight') 
        closed_roads.append(shortest_path)
        num_closed_roads -= 1
        print(f"Shortest path between {node1} and {node2}: {shortest_path}")
    except nx.NetworkXNoPath:
        print(f"No path exists between {node1} and {node2}")
        pass
    """

# Copy the graph to create a new, future state of the network (which will have roads closed)
subgraph_dash = subgraph.copy()

# Remove closed roads from `subgraph_dash`
for closed_road in closed_roads:
    try:
        subgraph_dash.remove_edge(closed_road[0], closed_road[1])
    except NetworkXError:
        pass

    """
    for i in range(len(closed_road) - 1):
        start_node_id = closed_road[i]
        end_node_id = closed_road[i + 1]
        try:
            subgraph_dash.remove_edge(start_node_id, end_node_id)
        except NetworkXError:
            pass
    """

# Get all shortest paths for the original network and the future network with closed roads
shortest_paths = get_all_shortest_paths(subgraph)
shortest_paths_dash = get_all_shortest_paths(subgraph_dash)

divergence = calculate_divergence(shortest_paths, shortest_paths_dash)
print(f'Divergence is {divergence} after closing {num_closed_roads} roads.')


if __name__ == '__main__':
    pass
