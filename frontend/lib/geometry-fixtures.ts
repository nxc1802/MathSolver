/** Sample payloads for regression / dev fixture page (mirrors BE-style metadata). */

export const FIXTURE_2D_WITH_TRIPLE_COORDS = {
  is_3d: false,
  coordinates: {
    A: [0, 0, 0],
    B: [3, 0, 0],
    C: [1.5, 2.5, 0],
  },
  polygon_order: ["A", "B", "C"],
  drawing_phases: [
    {
      phase: 1,
      label: "base",
      points: ["A", "B", "C"],
      segments: [
        ["A", "B"],
        ["B", "C"],
        ["C", "A"],
      ],
    },
  ],
};

export const FIXTURE_3D = {
  is_3d: true,
  coordinates: {
    O: [0, 0, 0],
    X: [2, 0, 0],
    Y: [0, 2, 0],
    Z: [0, 0, 2],
  },
  drawing_phases: [
    {
      phase: 1,
      label: "axes",
      points: ["O", "X", "Y", "Z"],
      segments: [
        ["O", "X"],
        ["O", "Y"],
        ["O", "Z"],
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
