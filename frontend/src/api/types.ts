export type LifeState = {
  life_id: string;
  person_id: string;
  age: number;
  life_stage: string;
  is_dead: boolean;
  death_reason: string | null;
  attributes: Record<string, number>;
  health: Record<string, unknown>;
  family: Record<string, unknown>;
  education: Record<string, unknown>;
  career: Record<string, unknown>;
  assets: Record<string, number>;
  flags: Record<string, unknown>;
  pending_random_event: Record<string, unknown> | null;
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

export type TriggeredRandomEvent = {
  event_id: string;
  name: string;
  category: string;
  narrative_text: string;
};

export type YearResult = {
  life_id: string;
  age_before: number;
  age_after: number;
  is_dead: boolean;
  death_reason: string | null;
  death_type: string | null;
  changed_attributes: Record<string, number>;
  changed_health: Record<string, number>;
  changed_assets: Record<string, number>;
  health_score_before: number | null;
  health_score_after: number | null;
  health_level_before: string | null;
  health_level_after: string | null;
  health_score_delta: number;
  new_health_warnings: string[];
  natural_death_candidate_created: boolean;
  direct_death_candidate_created: boolean;
  triggered_random_events: TriggeredRandomEvent[];
  random_event_attribute_changes: Record<string, number>;
  random_event_health_changes: Record<string, number>;
  random_event_asset_changes: Record<string, number>;
  inheritance_result: InheritanceResult | null;
  education_stage_before: string | null;
  education_stage_after: string | null;
  education_graduated_this_year: boolean;
  education_changes: Record<string, unknown>;
  career_status_before: string | null;
  career_status_after: string | null;
  career_path: string | null;
  position_level: string | null;
  annual_income: number;
  career_income_change: number;
  occurred_events: SimulationEvent[];
  narrative_text: string;
  next_available_choices: AvailableChoice[];
  pending_random_event: Record<string, unknown> | null;
  unsupported_random_event_effects: Record<string, unknown>[];
  random_event_choice_result: Record<string, unknown> | null;
  relationship_status_before: string | null;
  relationship_status_after: string | null;
  partner_relation_delta: number;
  parent_child_relation_delta: number;
  family_pressure_delta: number;
  married_this_year: boolean;
  child_born_this_year: boolean;
  children_count_delta: number;
  family_history_records: Record<string, unknown>[];
  family_changes: Record<string, unknown>;
};

export type HeirShare = {
  person_id: string;
  relation: string;
  share_ratio: number;
  amount: number;
};

export type InheritanceResult = {
  life_id: string;
  deceased_person_id: string;
  gross_estate: number;
  tax_rate: number;
  tax_amount: number;
  net_estate: number;
  heirs: HeirShare[];
  distribution: Record<string, number>;
  unclaimed_amount: number;
  status: string;
  created_from_death_type: string | null;
};

export type PlayableHeir = {
  person_id: string;
  name: string;
  relation: string;
  inheritance_amount: number;
  generation: number;
  start_age: number;
};

export type PlayableHeirsResponse = {
  life_id: string;
  source_life_id?: string;
  playable_heirs: PlayableHeir[];
  status: string;
};

export type LifeStateResponse = {
  state: LifeState;
  available_choices: AvailableChoice[];
};

export type RandomEventChoiceResponse = {
  life_id: string;
  choice_result: {
    event_id: string;
    choice_id: string;
    choice_text: string;
    effects_text: string;
  };
  pending_random_event: Record<string, unknown> | null;
  state: LifeState;
};

export type PendingRandomEventResponse = {
  life_id: string;
  pending_random_event: Record<string, unknown> | null;
};
