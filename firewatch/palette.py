"""Stable cluster colors shared by maps and statistical charts."""

CLUSTER_COLORS = ["#C74535", "#327B78", "#D09A34", "#497B9D", "#9066A2", "#758F46", "#B86D87", "#715C4D", "#667D8D", "#94522C"]


def cluster_color(cluster: int) -> str:
    return CLUSTER_COLORS[(int(cluster) - 1) % len(CLUSTER_COLORS)]
