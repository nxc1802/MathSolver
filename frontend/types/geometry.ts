/**
 * Comprehensive Geometry & Visualization Graph Types
 * Aligns frontend mathematical diagram rendering with backend solver & vis_planner.
 */

export type ImportanceTier = "REQUIRED" | "HELPFUL" | "OPTIONAL";
export type EntityKind = "PRIMARY" | "AUXILIARY" | "DERIVED";
export type EdgeStyle = "solid" | "dashed" | "dotted";

export interface VisVertex {
  id: string;
  coordinates: number[];
  role: string; // vertex, apex, foot, midpoint, center, auxiliary_point
  tier?: ImportanceTier;
  kind?: EntityKind;
  label?: string | null;
  show_label?: boolean;
  parent_solid?: string | null;
}

export interface VisEdge {
  id: string; // e.g. "AB"
  source: string;
  target: string;
  role: string; // base_edge, lateral_edge, altitude, median, bisector, diagonal, projection, segment
  tier?: ImportanceTier;
  kind?: EntityKind;
  style?: EdgeStyle;
  is_hidden?: boolean;
  parent_solid?: string | null;
  label?: string | null;
}

export interface VisFace {
  id: string; // e.g. "face_ABCD"
  vertices: string[]; // Ordered cyclic vertices [A, B, C, D]
  role?: string; // base_face, lateral_face, top_face, cross_section, polygon_face
  parent_solid?: string | null;
  plane_equation?: number[] | null; // [a, b, c, d]
  tier?: ImportanceTier;
  kind?: EntityKind;
  opacity?: number;
  fill?: boolean;
}

export interface VisSolid {
  id: string;
  type: string; // pyramid, prism, cube, cuboid, tetrahedron, sphere, frustum
  vertices: string[];
  edges: string[];
  faces: string[];
  apex?: string | null;
  base_vertices?: string[];
  top_vertices?: string[];
  tier?: ImportanceTier;
  kind?: EntityKind;
}

export interface PerpendicularMark {
  vertex: string;
  lines: string[]; // [line1_pt, line2_pt]
}

export interface AngleMark {
  vertex: string;
  lines: string[]; // [line1_pt, line2_pt]
  degrees?: number;
  label?: string;
}

export interface EqualTickMark {
  segment: [string, string];
  ticks: number; // 1, 2, 3
}

export interface ParallelMark {
  segments: Array<[string, string]>;
  arrows: number; // 1, 2
}

export interface VisAuxiliaryConstruction {
  id: string;
  type: string; // height, foot, median, bisector, diagonal, center, midpoint, section, projection
  source_entity?: string;
  target_entity?: string;
  created_vertices?: string[];
  created_edges?: string[];
  perpendicular_marks?: PerpendicularMark[];
  angle_marks?: AngleMark[];
  equal_ticks?: EqualTickMark[];
  parallel_marks?: ParallelMark[];
  tier?: ImportanceTier;
}

export interface DrawingPhase {
  phase: number;
  label: string;
  points: string[];
  segments: string[][];
}

export interface VisualizationGraph {
  vertices: Record<string, VisVertex>;
  edges: Record<string, VisEdge>;
  faces: Record<string, VisFace>;
  solids: Record<string, VisSolid>;
  auxiliary: VisAuxiliaryConstruction[];
  perpendicular_marks?: PerpendicularMark[];
  angle_marks?: AngleMark[];
  equal_ticks?: EqualTickMark[];
  parallel_marks?: ParallelMark[];
  drawing_phases: DrawingPhase[];
  is_3d: boolean;
}

export interface GeometryMetadata {
  coordinates?: Record<string, [number, number] | [number, number, number] | number[]>;
  polygon_order?: string[];
  polygonOrder?: string[];
  circles?: Array<{ center: string; radius: number }>;
  solids?: Array<{
    type: string;
    center?: string;
    center1?: string;
    center2?: string;
    apex?: string;
    radius?: number;
    height?: number;
    base?: string[];
    base1?: string[];
    base2?: string[];
    points?: string[];
    [key: string]: unknown;
  }>;
  faces?: string[][];
  drawing_phases?: DrawingPhase[];
  drawingPhases?: DrawingPhase[];
  lines?: Array<[string, string]>;
  rays?: Array<[string, string]>;
  visualization_graph?: VisualizationGraph;
  visualizationGraph?: VisualizationGraph;
  auxiliary?: VisAuxiliaryConstruction[];
  is_3d?: boolean;
  is3d?: boolean;
  video_url?: string;
  videoUrl?: string;
  job_id?: string;
  jobId?: string;
  solution?: {
    answer: string;
    steps: string[];
    symbolic_math?: Record<string, string>;
  };
  semantic_analysis?: string;
  geometry_dsl?: string;
  image_url?: string;
}
