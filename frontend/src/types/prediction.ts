export type DistributionStatus = 'ok' | 'warning' | 'out_of_distribution' | 'unknown';

export interface LithologyInterval {
  top: number;
  base: number;
  thickness: number;
  lithology_code: number;
  lithology: string;
  confidence: number;
  n_samples: number;
}

export interface LithologyShare {
  lithology: string;
  lithology_code: number;
  thickness: number;
  fraction: number;
  mean_confidence: number;
}

export interface SampleRow {
  depth: number;
  lithology_code: number;
  confidence: number;
}

export interface DistributionCheck {
  status: DistributionStatus;
  message: string;
  flagged_curves: string[];
  missing_curves: string[];
}

export interface PredictionResponse {
  well_name: string;
  depth_range: [number, number];
  n_samples: number;
  curves: import('./wellLog').CurveReport;
  distribution: DistributionCheck;
  intervals: LithologyInterval[];
  samples: SampleRow[] | null;
  distribution_by_lithology: LithologyShare[];
  curve_data: import('./wellLog').WellCurves | null;
  model_version: string;
}

export interface ModelInfo {
  version: string;
  trained_at: string;
  n_features: number;
  classes: string[];
  required_curves: string[];
  optional_curves: string[];
  test_accuracy: number;
  test_weighted_f1: number;
  xgboost_version: string;
  sklearn_version: string;
}
