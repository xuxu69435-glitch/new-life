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
  legal?: Record<string, unknown>;
  pending_legal_event?: Record<string, unknown> | null;
  mainline?: Record<string, unknown>;
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
  narrative_result?: Record<string, unknown> | null;
  annual_summary_text?: string;
  major_event_texts?: string[];
  display_sections?: Array<{ section_id: string; title: string; content: string }>;
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
  mainline_changes: Record<string, unknown>;
  active_mainline_tasks: MainlineTaskSummary[];
  completed_mainline_tasks_this_year: string[];
  failed_mainline_tasks_this_year: string[];
  expired_mainline_tasks_this_year: string[];
  mainline_rewards: Record<string, unknown>[];
  mainline_narrative: string[];
  current_guidance_text: string;
  newly_unlocked_achievements: Array<{
    achievement_id: string;
    title: string;
    description: string;
    points_gained: number;
    narrative_text?: string;
  }>;
  achievement_points_gained: number;
  milestones_this_year: Array<Record<string, unknown>>;
  achievement_narrative: string[];
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

export type MainlineTaskSummary = {
  task_id: string;
  title: string;
  description: string;
  chapter: string;
  completion_summary: string;
  progress: Record<string, unknown>;
};

export type MainlineStateResponse = {
  life_id: string;
  mainline: Record<string, unknown>;
  active_tasks: MainlineTaskSummary[];
  current_guidance_text: string;
};

export type AchievementStateResponse = {
  life_id: string;
  achievements: Record<string, unknown>;
  achievement_list: Array<{
    achievement_id: string;
    title: string;
    description: string;
    category: string;
    tier: string;
    points?: number;
    hidden: boolean;
    unlocked: boolean;
  }>;
  total_points: number;
  unlocked_count: number;
};

export type TimelineEntry = {
  entry_id: string;
  life_id: string;
  age: number;
  title: string;
  summary: string;
  entry_type: string;
  category: string;
  source_module: string;
  source_id: string;
  importance: number;
  tags: string[];
  display_text: string;
  related_snapshot_id: string;
  created_at: string;
};

export type TimelineEntriesResponse = {
  life_id: string;
  entries: TimelineEntry[];
  count: number;
};

export type YearDetailResponse = {
  life_id: string;
  age: number;
  snapshot_id: string;
  annual_summary: string;
  narrative_result: Record<string, unknown> | null;
  state_changes: {
    attributes: Record<string, number>;
    health: Record<string, number>;
    assets: Record<string, number>;
  };
  events: TimelineEntry[];
  achievements: Record<string, unknown>;
  mainline: Record<string, unknown>;
  milestones: Array<Record<string, unknown>>;
  year_result: YearResult;
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

export type LegalStatePayload = {
  is_in_prison: boolean;
  sentence_total_years: number;
  sentence_remaining_years: number;
  years_served: number;
  rehabilitation_progress: number;
  consecutive_rehabilitation_years: number;
  is_fugitive: boolean;
  has_criminal_record: boolean;
  is_under_supervision: boolean;
  supervision_remaining_years: number;
  research_job_ban_remaining_years: number;
  post_release_employment_penalty_year: number;
  civil_service_banned: boolean;
  [key: string]: unknown;
};

export type LegalStateResponse = {
  life_id: string;
  legal: LegalStatePayload;
  pending_legal_event: Record<string, unknown> | null;
  restrictions: Record<string, unknown>;
};

export type LegalChoiceResponse = {
  life_id: string;
  choice_result: Record<string, unknown>;
  pending_legal_event: Record<string, unknown> | null;
  state: LifeState;
};
