export type LifeState = {
  life_id: string;
  person_id: string;
  age: number;
  life_stage: string;
  is_dead: boolean;
  death_reason: string | null;
  attributes: Record<string, number>;
  health: Record<string, number>;
  family: Record<string, unknown>;
  education: Record<string, unknown>;
  career: Record<string, unknown>;
  assets: Record<string, number>;
  flags: Record<string, unknown>;
  rule_version: string;
};

export type AvailableChoice = {
  id: string;
  label: string;
};

export type SimulationEvent = {
  event_type: string;
  source_module: string;
  payload: Record<string, unknown>;
};

export type YearResult = {
  life_id: string;
  age_before: number;
  age_after: number;
  is_dead: boolean;
  death_reason: string | null;
  changed_attributes: Record<string, number>;
  changed_health: Record<string, number>;
  changed_assets: Record<string, number>;
  occurred_events: SimulationEvent[];
  narrative_text: string;
  next_available_choices: AvailableChoice[];
};

export type LifeStateResponse = {
  state: LifeState;
  available_choices: AvailableChoice[];
};
