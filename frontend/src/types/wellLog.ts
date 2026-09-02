export interface CurvePoint {
  depth: number;
  GR?: number | null;
  RDEP?: number | null;
  RHOB?: number | null;
  NPHI?: number | null;
  DTC?: number | null;
}

export interface WellCurves {
  well_name: string;
  depth_range: [number, number];
  n_source_samples: number;
  points: CurvePoint[];
  available_curves: string[];
}

export interface SampleWell {
  id: string;
  well_name: string;
  label: string;
  description: string;
  depth_range: [number, number];
}

export interface CurveReport {
  detected: string[];
  required_present: string[];
  required_missing: string[];
  optional_present: string[];
}
