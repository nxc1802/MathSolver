/** Sample payloads for regression / dev fixture page (mirrors BE-style metadata). */

export const FIXTURE_2D_WITH_TRIPLE_COORDS = {
  is_3d: false,
  coordinates: {
    A: [0, 0, 0],
    B: [4, 0, 0],
    C: [0, 3, 0],
  },
  polygon_order: ["A", "B", "C"],
  drawing_phases: [
    {
      phase: 1,
      label: "Tam giác vuông ABC",
      points: ["A", "B", "C"],
      segments: [
        ["A", "B"],
        ["B", "C"],
        ["C", "A"],
      ],
    },
    {
      phase: 2,
      label: "Đường cao AH",
      points: ["H"],
      segments: [["A", "H"]],
    },
  ],
  auxiliary: [
    {
      id: "foot_H_A",
      type: "foot",
      created_vertices: ["H"],
      created_edges: ["AH"],
      perpendicular_marks: [{ vertex: "A", lines: ["B", "C"] }],
    },
  ],
};

export const FIXTURE_3D_PYRAMID = {
  is_3d: true,
  coordinates: {
    A: [0, 0, 0],
    B: [3, 0, 0],
    C: [3, 3, 0],
    D: [0, 3, 0],
    O: [1.5, 1.5, 0],
    S: [1.5, 1.5, 4],
  },
  faces: [
    ["A", "B", "C", "D"],
    ["S", "A", "B"],
    ["S", "B", "C"],
    ["S", "C", "D"],
    ["S", "D", "A"],
  ],
  drawing_phases: [
    {
      phase: 1,
      label: "Hình chóp S.ABCD",
      points: ["S", "A", "B", "C", "D"],
      segments: [
        ["A", "B"],
        ["B", "C"],
        ["C", "D"],
        ["D", "A"],
        ["S", "A"],
        ["S", "B"],
        ["S", "C"],
        ["S", "D"],
      ],
    },
    {
      phase: 2,
      label: "Đường cao SO và đường chéo đáy",
      points: ["O"],
      segments: [
        ["S", "O"],
        ["A", "C"],
        ["B", "D"],
      ],
    },
  ],
  auxiliary: [
    {
      id: "height_S_O",
      type: "height",
      created_vertices: ["O"],
      created_edges: ["SO", "AC", "BD"],
      perpendicular_marks: [{ vertex: "O", lines: ["S", "A"] }],
    },
  ],
};

export const FIXTURE_3D_PRISM = {
  is_3d: true,
  coordinates: {
    A: [0, 0, 0],
    B: [3, 0, 0],
    C: [1, 2.5, 0],
    A1: [0, 0, 3.5],
    B1: [3, 0, 3.5],
    C1: [1, 2.5, 3.5],
  },
  faces: [
    ["A", "B", "C"],
    ["A1", "B1", "C1"],
    ["A", "B", "B1", "A1"],
    ["B", "C", "C1", "B1"],
    ["C", "A", "A1", "C1"],
  ],
  drawing_phases: [
    {
      phase: 1,
      label: "Lăng trụ ABC.A1B1C1",
      points: ["A", "B", "C", "A1", "B1", "C1"],
      segments: [
        ["A", "B"],
        ["B", "C"],
        ["C", "A"],
        ["A1", "B1"],
        ["B1", "C1"],
        ["C1", "A1"],
        ["A", "A1"],
        ["B", "B1"],
        ["C", "C1"],
      ],
    },
  ],
};

export const FIXTURE_FLAG_MISMATCH = {
  is_3d: true,
  coordinates: {
    P: [1, 1, 0],
    Q: [4, 1, 0],
  },
  drawing_phases: [] as Array<{
    phase: number;
    label: string;
    points: string[];
    segments: string[][];
  }>,
};
