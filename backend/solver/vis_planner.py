"""Visualization Planner & Topology Derivation Engine.

Derives complete topological models (vertices, edges, faces, solids, auxiliary
constructions, visibility, and drawing phases) from semantic geometry definitions
and solved coordinates.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np

from .models import Point, Constraint
from .vis_graph import (
    EdgeStyle,
    EntityKind,
    ImportanceTier,
    VisAuxiliaryConstruction,
    VisEdge,
    VisFace,
    VisSolid,
    VisVertex,
    VisualizationGraph,
)

logger = logging.getLogger(__name__)


class VisualizationPlanner:
    """
    Constructs a complete, minimal sufficient Visualization Graph from
    mathematical geometry results and semantic DSL constraints.
    """

    def plan(
        self,
        coords: Dict[str, List[float]],
        constraints: List[Constraint],
        solids_meta: List[Dict[str, Any]],
        circles_meta: List[Dict[str, Any]],
        polygon_order: List[str],
        segments_meta: List[List[str]],
        lines_meta: List[List[str]],
        rays_meta: List[List[str]],
        pt_list: List[Point],
        is_3d: bool = False,
    ) -> VisualizationGraph:
        graph = VisualizationGraph(is_3d=is_3d)

        # ---------------------------------------------------------------------
        # 1. Register All Known Points as Vertices
        # ---------------------------------------------------------------------
        all_ids = [p.id for p in pt_list]
        for pid in all_ids:
            if pid in coords:
                graph.add_vertex(
                    pid=pid,
                    coords=coords[pid],
                    role="vertex",
                    tier=ImportanceTier.REQUIRED,
                    kind=EntityKind.PRIMARY,
                )

        # ---------------------------------------------------------------------
        # 2. Derive Standard 3D Solid Topologies (Vertices, Edges, Faces)
        # ---------------------------------------------------------------------
        for solid in solids_meta:
            s_type = solid.get("type", "solid")
            s_id = f"{s_type}_{'_'.join(solid.get('points', []))}" if solid.get("points") else f"{s_type}_{len(graph.solids)}"

            if s_type == "pyramid":
                apex = solid.get("apex")
                base = solid.get("base", [])
                if apex and len(base) >= 3:
                    s_id = f"pyramid_{apex}_{''.join(base)}"
                    # Mark apex role
                    if apex in graph.vertices:
                        graph.vertices[apex].role = "apex"

                    pyramid_edges: List[str] = []
                    pyramid_faces: List[str] = []

                    # Base edges (cyclic)
                    for i in range(len(base)):
                        p1 = base[i]
                        p2 = base[(i + 1) % len(base)]
                        e = graph.add_edge(
                            p1=p1,
                            p2=p2,
                            role="base_edge",
                            tier=ImportanceTier.REQUIRED,
                            kind=EntityKind.PRIMARY,
                            parent_solid=s_id,
                        )
                        pyramid_edges.append(e.id)

                    # Lateral edges (apex -> base)
                    for bp in base:
                        e = graph.add_edge(
                            p1=apex,
                            p2=bp,
                            role="lateral_edge",
                            tier=ImportanceTier.REQUIRED,
                            kind=EntityKind.PRIMARY,
                            parent_solid=s_id,
                        )
                        pyramid_edges.append(e.id)

                    # Base face
                    f_base = graph.add_face(
                        vertices=base,
                        role="base_face",
                        tier=ImportanceTier.HELPFUL,
                        parent_solid=s_id,
                        opacity=0.15,
                    )
                    pyramid_faces.append(f_base.id)

                    # Lateral faces
                    for i in range(len(base)):
                        p1 = base[i]
                        p2 = base[(i + 1) % len(base)]
                        f_lat = graph.add_face(
                            vertices=[apex, p1, p2],
                            role="lateral_face",
                            tier=ImportanceTier.HELPFUL,
                            parent_solid=s_id,
                            opacity=0.25,
                        )
                        pyramid_faces.append(f_lat.id)

                    graph.solids[s_id] = VisSolid(
                        id=s_id,
                        type="pyramid",
                        vertices=base + [apex],
                        edges=pyramid_edges,
                        faces=pyramid_faces,
                        apex=apex,
                        base_vertices=base,
                    )

            elif s_type in ("prism", "cube", "cuboid", "frustum"):
                b1 = solid.get("base1", [])
                b2 = solid.get("base2", [])
                if len(b1) >= 3 and len(b2) >= 3 and len(b1) == len(b2):
                    s_id = f"{s_type}_{''.join(b1)}_{''.join(b2)}"
                    prism_edges: List[str] = []
                    prism_faces: List[str] = []

                    # Base 1 cyclic edges
                    for i in range(len(b1)):
                        e = graph.add_edge(
                            p1=b1[i],
                            p2=b1[(i + 1) % len(b1)],
                            role="base_edge",
                            tier=ImportanceTier.REQUIRED,
                            parent_solid=s_id,
                        )
                        prism_edges.append(e.id)

                    # Base 2 cyclic edges
                    for i in range(len(b2)):
                        e = graph.add_edge(
                            p1=b2[i],
                            p2=b2[(i + 1) % len(b2)],
                            role="top_edge",
                            tier=ImportanceTier.REQUIRED,
                            parent_solid=s_id,
                        )
                        prism_edges.append(e.id)

                    # Lateral edges
                    for p1, p2 in zip(b1, b2):
                        e = graph.add_edge(
                            p1=p1,
                            p2=p2,
                            role="lateral_edge",
                            tier=ImportanceTier.REQUIRED,
                            parent_solid=s_id,
                        )
                        prism_edges.append(e.id)

                    # Base 1 face
                    f1 = graph.add_face(
                        vertices=b1,
                        role="base_face",
                        tier=ImportanceTier.HELPFUL,
                        parent_solid=s_id,
                        opacity=0.15,
                    )
                    prism_faces.append(f1.id)

                    # Base 2 face
                    f2 = graph.add_face(
                        vertices=b2,
                        role="top_face",
                        tier=ImportanceTier.HELPFUL,
                        parent_solid=s_id,
                        opacity=0.15,
                    )
                    prism_faces.append(f2.id)

                    # Lateral faces
                    for i in range(len(b1)):
                        i_next = (i + 1) % len(b1)
                        f_lat = graph.add_face(
                            vertices=[b1[i], b1[i_next], b2[i_next], b2[i]],
                            role="lateral_face",
                            tier=ImportanceTier.HELPFUL,
                            parent_solid=s_id,
                            opacity=0.25,
                        )
                        prism_faces.append(f_lat.id)

                    graph.solids[s_id] = VisSolid(
                        id=s_id,
                        type=s_type,
                        vertices=b1 + b2,
                        edges=prism_edges,
                        faces=prism_faces,
                        base_vertices=b1,
                        top_vertices=b2,
                    )

            elif s_type == "tetrahedron":
                pts = solid.get("points", [])
                if len(pts) >= 4:
                    s_id = f"tetrahedron_{''.join(pts[:4])}"
                    tet_edges: List[str] = []
                    tet_faces: List[str] = []

                    # All 6 edges
                    for i in range(4):
                        for j in range(i + 1, 4):
                            e = graph.add_edge(
                                p1=pts[i],
                                p2=pts[j],
                                role="edge",
                                tier=ImportanceTier.REQUIRED,
                                parent_solid=s_id,
                            )
                            tet_edges.append(e.id)

                    # 4 faces
                    f_defs = [
                        [pts[1], pts[2], pts[3]],
                        [pts[0], pts[1], pts[2]],
                        [pts[0], pts[2], pts[3]],
                        [pts[0], pts[3], pts[1]],
                    ]
                    for fv in f_defs:
                        f = graph.add_face(
                            vertices=fv,
                            role="lateral_face",
                            tier=ImportanceTier.HELPFUL,
                            parent_solid=s_id,
                            opacity=0.2,
                        )
                        tet_faces.append(f.id)

                    graph.solids[s_id] = VisSolid(
                        id=s_id,
                        type="tetrahedron",
                        vertices=pts[:4],
                        edges=tet_edges,
                        faces=tet_faces,
                        base_vertices=pts[1:4],
                    )

        # ---------------------------------------------------------------------
        # 3. Derive 2D Polygon Perimeter Edges & Faces
        # ---------------------------------------------------------------------
        if not is_3d:
            poly_pts = polygon_order if polygon_order else all_ids[:4]
            if len(poly_pts) >= 3:
                for i in range(len(poly_pts)):
                    p1 = poly_pts[i]
                    p2 = poly_pts[(i + 1) % len(poly_pts)]
                    graph.add_edge(
                        p1=p1,
                        p2=p2,
                        role="polygon_edge",
                        tier=ImportanceTier.REQUIRED,
                        kind=EntityKind.PRIMARY,
                    )
                graph.add_face(
                    vertices=poly_pts,
                    role="polygon_face",
                    tier=ImportanceTier.HELPFUL,
                    kind=EntityKind.PRIMARY,
                    opacity=0.1,
                )

        # ---------------------------------------------------------------------
        # 4. Add Explicit Segments from DSL
        # ---------------------------------------------------------------------
        for seg in segments_meta:
            if len(seg) == 2:
                p1, p2 = seg[0], seg[1]
                graph.add_edge(
                    p1=p1,
                    p2=p2,
                    role="segment",
                    tier=ImportanceTier.REQUIRED,
                    kind=EntityKind.PRIMARY,
                )

        # ---------------------------------------------------------------------
        # 5. Derive Auxiliary Constructions & Solution Entities (P0 / P1)
        # ---------------------------------------------------------------------
        for c in constraints:
            c_type = c.type
            targets = [t.strip() for t in c.targets if isinstance(t, str)]

            # -------------------------------------------------------------
            # HEIGHT / ALTITUDE: HEIGHT(S, O, ABCD)
            # -------------------------------------------------------------
            if c_type in ("height", "altitude") and len(targets) >= 2:
                s_apex = targets[0]
                o_foot = targets[1]
                base_pts = targets[2:]

                if o_foot in graph.vertices:
                    graph.vertices[o_foot].role = "foot"
                    graph.vertices[o_foot].kind = EntityKind.AUXILIARY
                elif o_foot in coords:
                    graph.add_vertex(o_foot, coords[o_foot], role="foot", kind=EntityKind.AUXILIARY)

                # Add Altitude Edge SO (Dashed in 3D interior)
                edge_so = graph.add_edge(
                    p1=s_apex,
                    p2=o_foot,
                    role="altitude",
                    tier=ImportanceTier.REQUIRED,
                    kind=EntityKind.AUXILIARY,
                    style=EdgeStyle.DASHED if is_3d else EdgeStyle.SOLID,
                )

                # Ground the foot O: if base is square/rectangle, add diagonals AC & BD
                created_diags = []
                if len(base_pts) >= 4:
                    e_ac = graph.add_edge(
                        p1=base_pts[0],
                        p2=base_pts[2],
                        role="diagonal",
                        tier=ImportanceTier.HELPFUL,
                        kind=EntityKind.AUXILIARY,
                        style=EdgeStyle.DASHED if is_3d else EdgeStyle.SOLID,
                    )
                    e_bd = graph.add_edge(
                        p1=base_pts[1],
                        p2=base_pts[3],
                        role="diagonal",
                        tier=ImportanceTier.HELPFUL,
                        kind=EntityKind.AUXILIARY,
                        style=EdgeStyle.DASHED if is_3d else EdgeStyle.SOLID,
                    )
                    created_diags.extend([e_ac.id, e_bd.id])
                elif len(base_pts) == 3:
                    # Triangular base: add median / altitude on base
                    e_base_aux = graph.add_edge(
                        p1=base_pts[0],
                        p2=o_foot,
                        role="projection",
                        tier=ImportanceTier.HELPFUL,
                        kind=EntityKind.AUXILIARY,
                        style=EdgeStyle.DASHED if is_3d else EdgeStyle.SOLID,
                    )
                    created_diags.append(e_base_aux.id)

                graph.auxiliary.append(
                    VisAuxiliaryConstruction(
                        id=f"height_{s_apex}_{o_foot}",
                        type="height",
                        source_entity=s_apex,
                        target_entity=o_foot,
                        created_vertices=[o_foot],
                        created_edges=[edge_so.id] + created_diags,
                        perpendicular_marks=[{"vertex": o_foot, "lines": [s_apex, base_pts[0] if base_pts else o_foot]}],
                        tier=ImportanceTier.REQUIRED,
                    )
                )

            # -------------------------------------------------------------
            # FOOT OF PERPENDICULAR: FOOT(H, P, AB)
            # -------------------------------------------------------------
            elif c_type in ("foot", "foot_perp") and len(targets) >= 3:
                pH, pP = targets[0], targets[1]
                pA = targets[2]
                pB = targets[3] if len(targets) > 3 else "B"

                if pH in graph.vertices:
                    graph.vertices[pH].role = "foot"
                    graph.vertices[pH].kind = EntityKind.AUXILIARY
                elif pH in coords:
                    graph.add_vertex(pH, coords[pH], role="foot", kind=EntityKind.AUXILIARY)

                e_ph = graph.add_edge(
                    p1=pP,
                    p2=pH,
                    role="projection",
                    tier=ImportanceTier.REQUIRED,
                    kind=EntityKind.AUXILIARY,
                    style=EdgeStyle.DASHED if is_3d else EdgeStyle.SOLID,
                )
                graph.auxiliary.append(
                    VisAuxiliaryConstruction(
                        id=f"foot_{pH}_{pP}",
                        type="foot",
                        source_entity=pP,
                        target_entity=pH,
                        created_vertices=[pH],
                        created_edges=[e_ph.id],
                        perpendicular_marks=[{"vertex": pH, "lines": [pP, pA]}],
                        tier=ImportanceTier.REQUIRED,
                    )
                )

            # -------------------------------------------------------------
            # MEDIAN: MEDIAN(A, M, BC)
            # -------------------------------------------------------------
            elif c_type == "median" and len(targets) >= 2:
                pA = targets[0]
                pM = targets[1]
                if pM in graph.vertices:
                    graph.vertices[pM].role = "midpoint"
                    graph.vertices[pM].kind = EntityKind.AUXILIARY
                elif pM in coords:
                    graph.add_vertex(pM, coords[pM], role="midpoint", kind=EntityKind.AUXILIARY)

                e_am = graph.add_edge(
                    p1=pA,
                    p2=pM,
                    role="median",
                    tier=ImportanceTier.REQUIRED,
                    kind=EntityKind.AUXILIARY,
                    style=EdgeStyle.SOLID,
                )
                graph.auxiliary.append(
                    VisAuxiliaryConstruction(
                        id=f"median_{pA}_{pM}",
                        type="median",
                        source_entity=pA,
                        target_entity=pM,
                        created_vertices=[pM],
                        created_edges=[e_am.id],
                        tier=ImportanceTier.REQUIRED,
                    )
                )

            # -------------------------------------------------------------
            # BISECTOR: BISECTOR(A, D, BC)
            # -------------------------------------------------------------
            elif c_type == "bisector" and len(targets) >= 2:
                pA = targets[0]
                pD = targets[1]
                if pD in graph.vertices:
                    graph.vertices[pD].role = "bisector_point"
                    graph.vertices[pD].kind = EntityKind.AUXILIARY
                elif pD in coords:
                    graph.add_vertex(pD, coords[pD], role="bisector_point", kind=EntityKind.AUXILIARY)

                e_ad = graph.add_edge(
                    p1=pA,
                    p2=pD,
                    role="bisector",
                    tier=ImportanceTier.REQUIRED,
                    kind=EntityKind.AUXILIARY,
                    style=EdgeStyle.SOLID,
                )
                graph.auxiliary.append(
                    VisAuxiliaryConstruction(
                        id=f"bisector_{pA}_{pD}",
                        type="bisector",
                        source_entity=pA,
                        target_entity=pD,
                        created_vertices=[pD],
                        created_edges=[e_ad.id],
                        tier=ImportanceTier.REQUIRED,
                    )
                )

            # -------------------------------------------------------------
            # MIDPOINT: MIDPOINT(M, AB)
            # -------------------------------------------------------------
            elif c_type == "midpoint" and len(targets) == 3:
                pM, pA, pB = targets[0], targets[1], targets[2]
                if pM in graph.vertices:
                    graph.vertices[pM].role = "midpoint"
                    graph.vertices[pM].kind = EntityKind.AUXILIARY
                elif pM in coords:
                    graph.add_vertex(pM, coords[pM], role="midpoint", kind=EntityKind.AUXILIARY)

            # -------------------------------------------------------------
            # CENTER: CENTER(O, ABCD)
            # -------------------------------------------------------------
            elif c_type in ("center", "centroid") and len(targets) >= 3:
                pO = targets[0]
                poly_pts = targets[1:]
                if pO in graph.vertices:
                    graph.vertices[pO].role = "center"
                    graph.vertices[pO].kind = EntityKind.AUXILIARY
                elif pO in coords:
                    graph.add_vertex(pO, coords[pO], role="center", kind=EntityKind.AUXILIARY)

                # If 4 base points, draw diagonals to visually anchor center
                if len(poly_pts) >= 4:
                    graph.add_edge(
                        p1=poly_pts[0],
                        p2=poly_pts[2],
                        role="diagonal",
                        tier=ImportanceTier.HELPFUL,
                        kind=EntityKind.AUXILIARY,
                        style=EdgeStyle.DASHED if is_3d else EdgeStyle.SOLID,
                    )
                    graph.add_edge(
                        p1=poly_pts[1],
                        p2=poly_pts[3],
                        role="diagonal",
                        tier=ImportanceTier.HELPFUL,
                        kind=EntityKind.AUXILIARY,
                        style=EdgeStyle.DASHED if is_3d else EdgeStyle.SOLID,
                    )

        # ---------------------------------------------------------------------
        # 6. Derive 3D Hidden vs Visible Edges (Canonical Perspective)
        # ---------------------------------------------------------------------
        if is_3d:
            # Edges in the rear/interior of 3D solids are classified as DASHED
            for e_id, edge in graph.edges.items():
                v1 = graph.vertices.get(edge.source)
                v2 = graph.vertices.get(edge.target)
                if v1 and v2 and len(v1.coordinates) >= 3 and len(v2.coordinates) >= 3:
                    # Interior altitude or diagonal
                    if edge.role in ("altitude", "projection", "diagonal"):
                        edge.style = EdgeStyle.DASHED
                        edge.is_hidden = True
                    # Rear base edges: if both vertices are near back-left in standard view
                    elif edge.role == "base_edge":
                        z1, z2 = v1.coordinates[2], v2.coordinates[2]
                        y1, y2 = v1.coordinates[1], v2.coordinates[1]
                        if abs(z1) < 1e-3 and abs(z2) < 1e-3:
                            # If edge lies along the back/left boundary of base
                            if (v1.id == "D" and v2.id in ("A", "C")) or (v1.id == "A" and v2.id == "D"):
                                edge.style = EdgeStyle.DASHED
                                edge.is_hidden = True

        # ---------------------------------------------------------------------
        # 7. Construct Minimal Sufficient Drawing Phases
        # ---------------------------------------------------------------------
        # Phase 1: Base geometry and primary solid edges
        primary_pts = [vid for vid, v in graph.vertices.items() if v.kind == EntityKind.PRIMARY]
        primary_edges = [
            [e.source, e.target]
            for e in graph.edges.values()
            if e.kind == EntityKind.PRIMARY and e.tier == ImportanceTier.REQUIRED
        ]

        graph.drawing_phases.append({
            "phase": 1,
            "label": "Hình cơ bản",
            "points": primary_pts,
            "segments": primary_edges,
        })

        # Phase 2: Auxiliary constructions (Heights, Medians, Projections, Diagonals)
        aux_pts = [vid for vid, v in graph.vertices.items() if v.kind != EntityKind.PRIMARY]
        aux_edges = [
            [e.source, e.target]
            for e in graph.edges.values()
            if e.kind != EntityKind.PRIMARY or e.role in ("altitude", "projection", "median", "bisector", "diagonal")
        ]

        if aux_pts or aux_edges:
            graph.drawing_phases.append({
                "phase": 2,
                "label": "Đường cao và yếu tố phụ",
                "points": aux_pts,
                "segments": aux_edges,
            })

        logger.info(
            f"[VisualizationPlanner] Planned Visualization Graph: "
            f"{len(graph.vertices)} vertices, {len(graph.edges)} edges, "
            f"{len(graph.faces)} faces, {len(graph.solids)} solids, "
            f"{len(graph.auxiliary)} auxiliary constructions."
        )

        return graph
