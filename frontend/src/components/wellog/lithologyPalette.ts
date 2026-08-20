// One colour per lithology, 11 classes. Stays in the HUD amber/brown family
// while remaining distinguishable side by side.
export const LITHOLOGY_COLOURS = [
  '#efb027',
  '#e8ddc7',
  '#c99a3a',
  '#f0d080',
  '#8a6f2c',
  '#d9822b',
  '#a3893f',
  '#b5651d',
  '#6b5a2e',
  '#dfc08a',
  '#7a4f1c',
];

export const colourFor = (index: number): string =>
  LITHOLOGY_COLOURS[index % LITHOLOGY_COLOURS.length];
