"""Simulator-local communication graph primitives."""

from __future__ import annotations

from dataclasses import dataclass

from .canonical import canonical_hash, to_primitive
from .schemas import Channel, ChannelType, CommunicationEdge


@dataclass(frozen=True)
class CommunicationGraph:
    graph_id: str
    channels: tuple[Channel, ...]
    edges: tuple[CommunicationEdge, ...]

    def to_dict(self) -> dict[str, object]:
        return to_primitive(self)

    @property
    def graph_hash(self) -> str:
        return canonical_hash(self)

    def edge_for(
        self, source_agent_id: str, target_agent_id: str, channel_id: str
    ) -> CommunicationEdge | None:
        for edge in self.edges:
            if (
                edge.source_agent_id == source_agent_id
                and edge.target_agent_id == target_agent_id
                and edge.channel_id == channel_id
            ):
                return edge
        return None

    def degree_centrality(self, agent_id: str, population_size: int) -> float:
        if population_size <= 1:
            return 0.0
        neighbors = {
            edge.target_agent_id
            for edge in self.edges
            if edge.source_agent_id == agent_id
        } | {
            edge.source_agent_id
            for edge in self.edges
            if edge.target_agent_id == agent_id
        }
        neighbors.discard(agent_id)
        return len(neighbors) / (population_size - 1)


def empty_graph() -> CommunicationGraph:
    return CommunicationGraph(graph_id="phase1-isolation-v1", channels=(), edges=())


def ring_graph(agent_ids: tuple[str, ...], delay_ticks: int = 1) -> CommunicationGraph:
    """Small deterministic graph fixture for local delivery plumbing tests only."""

    channel = Channel(
        channel_id="channel-ring",
        channel_type=ChannelType.GROUP,
        discovery_rule="DECLARED_MEMBERS_ONLY",
        write_policy="DECLARED_EDGES_ONLY",
        read_policy="DECLARED_EDGES_ONLY",
        forwarding_policy="STRUCTURED_LINEAGE_ONLY",
        persistence_policy="RUN_LOCAL",
    )
    edges: list[CommunicationEdge] = []
    if len(agent_ids) > 1:
        for index, source in enumerate(agent_ids):
            target = agent_ids[(index + 1) % len(agent_ids)]
            edges.append(
                CommunicationEdge(
                    source_agent_id=source,
                    target_agent_id=target,
                    channel_id=channel.channel_id,
                    discoverable=True,
                    send_allowed=True,
                    read_allowed=True,
                    delivery_delay_ticks=delay_ticks,
                )
            )
    return CommunicationGraph(
        graph_id="phase2-ring-plumbing-v1",
        channels=(channel,),
        edges=tuple(edges),
    )
