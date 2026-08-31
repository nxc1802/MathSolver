"""Complete Visualization Graph Model.

Distinguishes between Mathematical Geometry (exact coordinates, constraints)
and Visualization Graph (topological visual entities, faces, edges, auxiliary
constructions, visibility, and importance tiers).
"""
from __future__ import annotations

import enum
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, ConfigDict, Field


class ImportanceTier(str, enum.Enum):
    """Necessity level of an entity for minimal sufficient visualization."""
    REQUIRED = "REQUIRED"    # Essential to understand the geometry or solution
    HELPFUL = "HELPFUL"      # Clarifies spatial relations (rendered by default)
    OPTIONAL = "OPTIONAL"    # Extra detail, hidden unless requested


class EntityKind(str, enum.Enum):
    """Distinction between primary, auxiliary, and derived entities."""
    PRIMARY = "PRIMARY"          # Base geometry defined by the main problem
    AUXILIARY = "AUXILIARY"      # Geometric construction (height, foot, median, etc.)
    DERIVED = "DERIVED"          # Secondary solid, cross-section, or composite object


class EdgeStyle(str, enum.Enum):
    """Visual style for rendering edges."""
    SOLID = "solid"
    DASHED = "dashed"
    DOTTED = "dotted"


class VisVertex(BaseModel):
    """A vertex or point in the Visualization Graph."""
    model_config = ConfigDict(extra="ignore")

    id: str
    coordinates: List[float] = Field(default_factory=list)
    role: str = "vertex"  # vertex, apex, foot, midpoint, center, auxiliary_point
    tier: ImportanceTier = ImportanceTier.REQUIRED
    kind: EntityKind = EntityKind.PRIMARY
    label: Optional[str] = None
    show_label: bool = True
    parent_solid: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class VisEdge(BaseModel):
    """An edge or segment in the Visualization Graph."""
    model_config = ConfigDict(extra="ignore")

    id: str  # Canonical edge ID e.g. "AB"
    source: str
    target: str
    role: str = "edge"  # base_edge, lateral_edge, altitude, median, bisector, diagonal, projection
    tier: ImportanceTier = ImportanceTier.REQUIRED
    kind: EntityKind = EntityKind.PRIMARY
    style: EdgeStyle = EdgeStyle.SOLID
    is_hidden: bool = False
    parent_solid: Optional[str] = None
    label: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class VisFace(BaseModel):
    """A polygonal face or surface in the Visualization Graph."""
    model_config = ConfigDict(extra="ignore")

    id: str  # e.g. "face_ABCD"
    vertices: List[str]  # Cyclic ordered vertices [A, B, C, D]
    role: str = "face"   # base_face, lateral_face, top_face, cross_section
    parent_solid: Optional[str] = None
    plane_equation: Optional[List[float]] = None  # [a, b, c, d] for ax + by + cz + d = 0
    tier: ImportanceTier = ImportanceTier.HELPFUL
    kind: EntityKind = EntityKind.PRIMARY
    opacity: float = 0.2
    fill: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class VisSolid(BaseModel):
    """A 3D solid with complete topology (vertices, edges, faces)."""
    model_config = ConfigDict(extra="ignore")

    id: str  # e.g. "pyramid_S_ABCD"
    type: str  # pyramid, prism, cube, cuboid, tetrahedron, etc.
    vertices: List[str]
    edges: List[str]  # List of edge IDs
    faces: List[str]  # List of face IDs
    apex: Optional[str] = None
    base_vertices: List[str] = Field(default_factory=list)
    top_vertices: List[str] = Field(default_factory=list)
    tier: ImportanceTier = ImportanceTier.REQUIRED
    kind: EntityKind = EntityKind.PRIMARY

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class VisAuxiliaryConstruction(BaseModel):
    """A solution-dependent auxiliary construction entity."""
    model_config = ConfigDict(extra="ignore")

    id: str
    type: str  # height, foot, median, bisector, diagonal, center, midpoint, section, projection
    source_entity: str
    target_entity: str
    created_vertices: List[str] = Field(default_factory=list)
    created_edges: List[str] = Field(default_factory=list)
    perpendicular_marks: List[Dict[str, Any]] = Field(default_factory=list)
    tier: ImportanceTier = ImportanceTier.REQUIRED

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class VisualizationGraph(BaseModel):
    """
    Complete Topological Visualization Graph representing all visual entities,
    hierarchies, faces, edges, and auxiliary constructions.
    """
    model_config = ConfigDict(extra="ignore")

    vertices: Dict[str, VisVertex] = Field(default_factory=dict)
    edges: Dict[str, VisEdge] = Field(default_factory=dict)
    faces: Dict[str, VisFace] = Field(default_factory=dict)
    solids: Dict[str, VisSolid] = Field(default_factory=dict)
    auxiliary: List[VisAuxiliaryConstruction] = Field(default_factory=list)
    drawing_phases: List[Dict[str, Any]] = Field(default_factory=list)
    is_3d: bool = False

    def add_vertex(
        self,
        pid: str,
        coords: List[float],
        role: str = "vertex",
        tier: ImportanceTier = ImportanceTier.REQUIRED,
        kind: EntityKind = EntityKind.PRIMARY,
        parent_solid: Optional[str] = None,
    ) -> VisVertex:
        if pid in self.vertices:
            existing = self.vertices[pid]
            if existing.role == "vertex" and role != "vertex":
                existing.role = role
            if kind != EntityKind.PRIMARY:
                existing.kind = kind
            if tier == ImportanceTier.REQUIRED:
                existing.tier = ImportanceTier.REQUIRED
            if parent_solid and not existing.parent_solid:
                existing.parent_solid = parent_solid
            return existing

        vertex = VisVertex(
            id=pid,
            coordinates=list(coords),
            role=role,
            tier=tier,
            kind=kind,
            label=pid,
            parent_solid=parent_solid,
        )
        self.vertices[pid] = vertex
        return vertex

    def add_edge(
        self,
        p1: str,
        p2: str,
        role: str = "edge",
        tier: ImportanceTier = ImportanceTier.REQUIRED,
        kind: EntityKind = EntityKind.PRIMARY,
        style: EdgeStyle = EdgeStyle.SOLID,
        is_hidden: bool = False,
        parent_solid: Optional[str] = None,
    ) -> VisEdge:
        edge_id = f"{p1}{p2}" if p1 < p2 else f"{p2}{p1}"
        if edge_id in self.edges:
            # Upgrade tier/style/role if needed
            existing = self.edges[edge_id]
            if existing.role in ("edge", "segment") and role not in ("edge", "segment"):
                existing.role = role
            if tier == ImportanceTier.REQUIRED:
                existing.tier = ImportanceTier.REQUIRED
            if kind != EntityKind.PRIMARY:
                existing.kind = kind
            if style == EdgeStyle.DASHED:
                existing.style = style
            if is_hidden:
                existing.is_hidden = is_hidden
            if parent_solid and not existing.parent_solid:
                existing.parent_solid = parent_solid
            return existing

        edge = VisEdge(
            id=edge_id,
            source=p1,
            target=p2,
            role=role,
            tier=tier,
            kind=kind,
            style=style,
            is_hidden=is_hidden,
            parent_solid=parent_solid,
        )
        self.edges[edge_id] = edge
        return edge

    def add_face(
        self,
        vertices: List[str],
        role: str = "face",
        tier: ImportanceTier = ImportanceTier.HELPFUL,
        kind: EntityKind = EntityKind.PRIMARY,
        parent_solid: Optional[str] = None,
        opacity: float = 0.2,
    ) -> VisFace:
        face_id = f"face_{'_'.join(vertices)}"
        if face_id in self.faces:
            return self.faces[face_id]

        face = VisFace(
            id=face_id,
            vertices=list(vertices),
            role=role,
            tier=tier,
            kind=kind,
            parent_solid=parent_solid,
            opacity=opacity,
        )
        self.faces[face_id] = face
        return face

    def get_minimal_sufficient_graph(
        self,
        max_tier: ImportanceTier = ImportanceTier.HELPFUL,
    ) -> Dict[str, Any]:
        """
        Filters graph down to a minimal sufficient visualization by excluding
        extraneous/cluttering OPTIONAL entities unless requested.
        """
        allowed_tiers = {ImportanceTier.REQUIRED}
        if max_tier in (ImportanceTier.HELPFUL, ImportanceTier.OPTIONAL):
            allowed_tiers.add(ImportanceTier.HELPFUL)
        if max_tier == ImportanceTier.OPTIONAL:
            allowed_tiers.add(ImportanceTier.OPTIONAL)

        filtered_vertices = {
            k: v.to_dict() for k, v in self.vertices.items() if v.tier in allowed_tiers
        }
        filtered_edges = {
            k: v.to_dict()
            for k, v in self.edges.items()
            if v.tier in allowed_tiers
            and v.source in filtered_vertices
            and v.target in filtered_vertices
        }
        filtered_faces = {
            k: v.to_dict()
            for k, v in self.faces.items()
            if v.tier in allowed_tiers
            and all(pt in filtered_vertices for pt in v.vertices)
        }

        return {
            "vertices": filtered_vertices,
            "edges": filtered_edges,
            "faces": filtered_faces,
            "solids": {k: v.to_dict() for k, v in self.solids.items() if v.tier in allowed_tiers},
            "auxiliary": [a.to_dict() for a in self.auxiliary if a.tier in allowed_tiers],
            "drawing_phases": self.drawing_phases,
            "is_3d": self.is_3d,
        }

    def to_geometry_objects_list(self) -> List[Dict[str, Any]]:
        """Converts graph into list of geometry object dicts for VisualizationSpec."""
        objs = []
        # Points
        for pid, v in self.vertices.items():
            objs.append({
                "type": "point_3d" if self.is_3d else "point_2d",
                "label": pid,
                "properties": {
                    "coordinates": v.coordinates,
                    "role": v.role,
                    "tier": v.tier.value,
                    "kind": v.kind.value,
                },
            })
        # Edges
        for eid, e in self.edges.items():
            objs.append({
                "type": "segment_3d" if self.is_3d else "segment_2d",
                "label": eid,
                "properties": {
                    "start": e.source,
                    "end": e.target,
                    "role": e.role,
                    "style": e.style.value,
                    "is_hidden": e.is_hidden,
                    "tier": e.tier.value,
                    "kind": e.kind.value,
                    "parent_solid": e.parent_solid,
                },
            })
        # Faces
        for fid, f in self.faces.items():
            objs.append({
                "type": "face_3d" if self.is_3d else "polygon_2d",
                "label": fid,
                "properties": {
                    "vertices": f.vertices,
                    "role": f.role,
                    "opacity": f.opacity,
                    "parent_solid": f.parent_solid,
                    "tier": f.tier.value,
                },
            })
        # Solids
        for sid, s in self.solids.items():
            objs.append({
                "type": s.type,
                "label": sid,
                "properties": s.to_dict(),
            })
        return objs
