// Minimal, dependency-free Lottie (Bodymovin) payload — a pulsing gold
// funding coin. Kept tiny so it parses instantly and bundles lean.
export const coinAnimation = {
  v: "5.7.4",
  fr: 30,
  ip: 0,
  op: 90,
  w: 200,
  h: 200,
  nm: "CoinPulse",
  ddd: 0,
  assets: [],
  layers: [
    {
      ddd: 0,
      ind: 1,
      ty: 4,
      nm: "gold_circle",
      sr: 1,
      ks: {
        o: { a: 0, k: 100 },
        r: { a: 0, k: 0 },
        p: {
          a: 1,
          k: [
            { i: { x: [0.4], y: [1] }, o: { x: [0.6], y: [0] }, t: 0, s: [100, 100, 0] },
            { t: 45, s: [100, 82, 0] },
            { t: 90, s: [100, 100, 0] },
          ],
        },
        a: { a: 0, k: [0, 0, 0] },
        s: {
          a: 1,
          k: [
            { i: { x: [0.4], y: [1] }, o: { x: [0.6], y: [0] }, t: 0, s: [100, 100, 100] },
            { t: 45, s: [114, 114, 100] },
            { t: 90, s: [100, 100, 100] },
          ],
        },
      },
      ao: 0,
      shapes: [
        {
          ty: "gr",
          nm: "Group 1",
          it: [
            {
              ty: "el",
              nm: "Outer",
              p: { a: 0, k: [0, 0] },
              s: { a: 0, k: [120, 120] },
            },
            {
              ty: "fl",
              nm: "Fill 1",
              c: { a: 0, k: [1, 0.788, 0.17, 1] },
              o: { a: 0, k: 100 },
              r: 1,
            },
            {
              ty: "el",
              nm: "Inner",
              p: { a: 0, k: [0, 0] },
              s: { a: 0, k: [62, 62] },
            },
            {
              ty: "fl",
              nm: "Fill 2",
              c: { a: 0, k: [1, 0.933, 0.69, 1] },
              o: { a: 0, k: 90 },
              r: 1,
            },
            {
              ty: "tr",
              p: { a: 0, k: [0, 0] },
              a: { a: 0, k: [0, 0] },
              s: { a: 0, k: [100, 100] },
              r: { a: 0, k: 0 },
              o: { a: 0, k: 100 },
              sk: { a: 0, k: 0 },
              sa: { a: 0, k: 0 },
            },
          ],
        },
      ],
      ip: 0,
      op: 90,
      st: 0,
      bm: 0,
    },
  ],
};