import random
import uuid
import networkx as nx
from networkx import NetworkXError
from lxml import etree
import numpy as np
import plotly.graph_objs as go
import plotly.io as pio

# Create an empty NetworkX graph
g = nx.Graph()

# Parse the GML file
tree = etree.parse('data/oproad_gml3_gb/data/OSOpenRoads_SZ.gml')

# Define the namespaces used in the GML
ns = {
    'road': 'http://namespaces.os.uk/Open/Roads/1.0',
    'net': 'urn:x-inspire:specification:gmlas:Network:3.2',
    'xlink': 'http://www.w3.org/1999/xlink',
    'gml': 'http://www.opengis.net/gml/3.2',
}

# Initialise min and max edge (road) lengths
min_length = 1000000000
max_length = 0

# Iterate through each RoadLink element in the tree
for road_link in tree.xpath('//road:RoadLink', namespaces=ns):
    # Extract the startNode and endNode elements
    start_node_element = road_link.find('net:startNode', namespaces=ns)
    end_node_element = road_link.find('net:endNode', namespaces=ns)
    # Extract the centreline
    centreline_geometry = road_link.find('net:centrelineGeometry', namespaces=ns)
    line_string_element = centreline_geometry.find('gml:LineString', namespaces=ns)

    # Extract the posList element containing (Easting, Northing) pairs
    pos_list = line_string_element.find('gml:posList', namespaces=ns).text

    # Split the posList into individual coordinates
    eastings_and_northings = pos_list.split()

    # Convert the strings to floats and group them into (Easting, Northing) pairs
    centreline_coordinates = [(float(eastings_and_northings[i]), float(eastings_and_northings[i + 1]))
                   for i in range(0, len(eastings_and_northings), 2)]

    # Extract the start and end node coordinates
    start_node_coords = centreline_coordinates[0]  # First pair
    end_node_coords = centreline_coordinates[-1]  # Last pair

    # Extract the xlink:href attributes
    start_node_id = start_node_element.get('{http://www.w3.org/1999/xlink}href')[2:]
    end_node_id = end_node_element.get('{http://www.w3.org/1999/xlink}href')[2:]

    # Extract the road name
    road_name_element = road_link.find('road:name1', namespaces=ns)
    road_name = road_name_element.text if road_name_element is not None else 'N/A'

    # Extract the length element
    length_element = road_link.find('road:length', namespaces=ns)
    length_value = int(length_element.text) if length_element is not None else None
    if length_value < min_length:
        min_length = length_value
    if length_value > max_length:
        max_length = length_value
    # Generate a UUID for the new edge
    edge_id = str(uuid.uuid4())
    # Add the edge (road) to the graph `g`
    g.add_edge(start_node_id, end_node_id, id=edge_id, weight=length_value, name=road_name)
    # Update the start and end nodes with Easting and Northing attributes
    g.nodes[start_node_id].update({'easting': start_node_coords[0], 'northing': start_node_coords[1]})
    g.nodes[end_node_id].update({'easting': end_node_coords[0], 'northing': end_node_coords[1]})

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
    # Select a random start node
    start_node = random.choice(list(graph.nodes))
    path = [start_node]

    while len(path) < max_edges:
        neighbours = list(graph.neighbors(path[-1]))
        if not neighbours or (len(path) >= min_edges and random.random() < 0.5):
            break
        next_node = random.choice(neighbours)
        if next_node not in path:  # Avoid cycles
            path.append(next_node)

    return path


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


# Initialise a list of closed roads
closed_roads = []
# Initialise min and max range values for number of closed roads selected at random
min_closed_roads = 3
max_closed_roads = 13

# Pick a random number between min_closed_roads and max_closed_roads
num_closed_roads = random.randint(min_closed_roads, max_closed_roads)
print(f"Number of closed roads: {num_closed_roads}")

# Initialise a counter for the number of closed roads
i = num_closed_roads
# Close some roads
while i > 0:
    try:
        # Pick a random node
        start_node = random.choice(list(subgraph.nodes))
        # Get the start_node's neighbours
        neighbours = list(subgraph.neighbors(start_node))
        if neighbours:
            # Pick a random neighbour, i.e. linked to start_node with an edge
            end_node = random.choice(neighbours)
            # Add the "road" (edge) between start_node and end_node to the list of closed roads
            closed_roads.append((start_node, end_node))
            # Reduce the counter by 1
            i -= 1
    except NetworkXError:
        pass

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

# Display the graph
# Define positions for the nodes
# Extract positions from Eastings and Northings on all nodes
pos = {node: (data['easting'], data['northing']) for node, data in subgraph.nodes(data=True)}

# Calculate the bounding box for the graph
# Deprecated: not currently used
min_easting = min(data['easting'] for node, data in subgraph.nodes(data=True))
max_easting = max(data['easting'] for node, data in subgraph.nodes(data=True))
min_northing = min(data['northing'] for node, data in subgraph.nodes(data=True))
max_northing = max(data['northing'] for node, data in subgraph.nodes(data=True))

# Normalize the size
# Deprecated: not currently used
scale_factor = 1.1  # Adjust this factor to scale the figure size
width = (max_easting - min_easting) * scale_factor
height = (max_northing - min_northing) * scale_factor

# Extract edge and node data for plotting
edge_x = []
edge_y = []
edge_text = []  # To store tooltips for edges
edge_labels_x = []
edge_labels_y = []
edge_labels_text = []
for edge in subgraph.edges():
    x0, y0 = pos[edge[0]]
    x1, y1 = pos[edge[1]]
    edge_x.extend([x0, x1, None])
    edge_y.extend([y0, y1, None])

# Calculate the midpoint for the edge label
    edge_labels_x.append((x0 + x1) / 2)
    edge_labels_y.append((y0 + y1) / 2)
    edge_labels_text.append(f"{subgraph[edge[0]][edge[1]]['weight']}")  # Use edge weight as label
    edge_text.append(f"Edge from {edge[0]} to {edge[1]}<br>Weight: {subgraph[edge[0]][edge[1]]['weight']}")

edge_trace = go.Scatter(
    x=edge_x, y=edge_y,
    line=dict(width=1, color='#888'),
    hoverinfo='none',
    mode='lines')

edge_labels_trace = go.Scatter(
    x=edge_labels_x, y=edge_labels_y,
    mode='text',
    text=edge_labels_text,
    textposition='middle center',
    hoverinfo='none',  # Prevent hoverinfo on labels
    showlegend=False
)

node_x = []
node_y = []
node_text = []
for node in subgraph.nodes():
    x, y = pos[node]
    node_x.append(x)
    node_y.append(y)
    node_text.append(f"Node ID: {node}")

node_trace = go.Scatter(
    x=node_x, y=node_y,
    mode='markers',
    hoverinfo='text',
    text=node_text,
    marker=dict(
        showscale=True,
        colorscale='YlGnBu',
        size=10,
    )
)

fig = go.Figure(
    data=[edge_trace, edge_labels_trace, node_trace],
    layout=go.Layout(
        showlegend=False,
        hovermode='closest',
        margin=dict(b=0, l=0, r=0, t=0),
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=False, zeroline=False)),
        #width=800,
        #height=600,
)

pio.show(fig)


if __name__ == '__main__':
    pass
