export interface CattleAnimal {
  pk: string;
  ear_tag: string;
  breed?: string;
  sex?: string;
  birth_date?: string;
  mother?: string;
  batch?: string;
  status?: string;
  pregnant?: boolean;
  implanted?: boolean;
  inseminated?: boolean;
  lactating?: boolean;
  transferred?: boolean;
  notes?: string[];
  tags?: string[];
}

export interface Insemination {
  pk: string;
  insemination_date: string;
  semen: string;
}

export interface Diagnostic {
  pk: string;
  diagnostic_date: string;
  pregnant: boolean;
  breeding_date?: string;
  expected_delivery_date?: string;
  semen?: string;
}

export interface Module {
  pk: string;
  module_number: number;
  name: string;
  area: number;
  supported_animal_count: number;
  silo_capacity: number;
}

export interface Batch {
  pk: string;
  status: 'created' | 'in_progress' | 'delivered';
  supply_id: number;
  module_id: string;
  expected_slaughter_date?: string;
  min_feed_stock_threshold: number;
  // Start summary (optional, populated after trigger)
  total_animal_count?: number;
  average_start_date?: string;
  distinct_origin_count?: number;
  origin_types?: string[];
  initial_animal_weight?: number;
  feed_leftover?: number;
}

export interface FeedSchedule {
  pk: string;
  sk: string;
  feed_type: string;
  planned_date: string;
  expected_amount_kg: number;
  status: 'scheduled' | 'delivered' | 'canceled';
  fulfilled_by?: string;
  feed_description?: string;
}

export interface FeedTruckArrival {
  pk: string;
  sk: string;
  receive_date: string;
  fiscal_document_number: string;
  actual_amount_kg: number;
  feed_type: string;
  feed_description?: string;
  feed_schedule_id?: string;
}

export interface PigTruckArrival {
  pk: string;
  sk: string;
  animal_count: number;
  sex: 'Male' | 'Female';
  arrival_date: string;
  pig_age_days: number;
  origin_name: string;
  origin_type: 'UPL' | 'Creche';
  fiscal_document_number?: string;
  animal_weight?: number;
  gta_number?: string;
  mossa?: string;
  suplier_code?: number;
}

export interface Mortality {
  pk: string;
  sk: string;
  mortality_date: string;
  sex: 'Male' | 'Female';
  origin: string;
  death_reason: string;
  reported_by: string;
}

export interface Medication {
  pk: string;
  sk: string;
  medication_name: string;
  expiration_date: string;
  part_number: string;
  raw_material_code?: string;
}

export interface RawMaterialType {
  pk: string;
  sk: string;
  code: string;
  description: string;
  category: 'feed' | 'medicine';
}

export interface FiscalDocument {
  pk: string;
  sk: string;
  fiscal_document_number: string;
  issue_date: string;
  actual_amount_kg: number;
  product_code: string;
  product_description: string;
  supplier_name: string;
  order_number: string;
}

export interface FeedScheduleFiscalDocument {
  pk: string;
  sk: string;
  fiscal_document_number: string;
  feed_schedule_id?: string;
  status: 'pending' | 'used' | 'discarded';
  product_code: string;
  actual_amount_kg: number;
  issue_date: string;
  planned_date?: string;
}

export interface MedicationShot {
  pk: string;
  sk: string;
  medication_name: string;
  medication_code: string;
  shot_count: number;
  date: string;
}

export interface FeedConsumptionPlanEntry {
  day_number: number;
  expected_kg_per_animal: number;
  expected_piglet_weight: number;
  date: string;
}

export interface FeedBalance {
  pk: string;
  sk: string;
  measurement_date: string;
  balance_kg: number;
}

export interface Weight {
  pk: string;
  weight_kg: number;
  weighing_date: string;
}

export interface BatchFinancialResult {
  pk: string;
  sk: string;
  type: string;
  created_at: string;

  // Farm data
  housed_count: number;
  mortality_count: number;
  pig_count: number;
  piglet_weight: number;
  pig_weight: number;
  total_feed: number;
  days_housed: number;

  // Integrator parameters
  cap: number;
  map_value: number;
  price_per_kg: number;
  gross_integrator_pct: number;

  // Carcass calculations
  carcass_yield_factor: number;
  piglet_carcass_weight: number;
  pig_carcass_weight: number;
  total_piglet_carcass: number;
  total_pig_carcass: number;
  total_carcass_produced: number;

  // Feed conversion
  real_conversion: number;
  piglet_adjustment: number;
  carcass_adjustment: number;
  adjusted_conversion: number;

  // Performance
  daily_weight_gain: number;
  daily_carcass_gain: number;

  // Mortality
  real_mortality_pct: number;
  adjusted_mortality_pct: number;

  // Integrator percentage
  mortality_adjustment_pct: number;
  conversion_adjustment_pct: number;
  integrator_pct: number;

  // Financial result
  gross_income: number;
  net_income: number;
  gross_income_per_pig: number;
  net_income_per_pig: number;
}

export interface FeedConsumptionTemplate {
  pk: string;
  sk: string;
  sequence: number;
  expected_piglet_weight: number;
  expected_kg_per_animal: number;
}

export interface IntegratorWeeklyData {
  pk: string;
  sk: string;
  date_generated: string;
  validity_start: string;
  validity_end: string;
  source_data_start: string;
  source_data_end: string;
  car: number;
  mar: number;
  avg_piglet_weight: number;
  avg_slaughter_weight: number;
  average_age: number;
  number_of_samples: number;
  gdp: number;

  // Computed CAP/MAP variants
  cap_1: number;
  cap_2: number;
  cap_3: number;
  cap_4: number;
  map_1: number;
  map_2: number;
}

export interface FeedScheduleSuggestion {
  planned_date: string;
  feed_description: string;
  new_planned_date: string;
  description: string;
}

export interface FeedScheduleSuggestionsResponse {
  suggestions: FeedScheduleSuggestion[];
  message: string;
}
