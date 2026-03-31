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
  receive_date: string;
  expected_slaughter_date?: string;
  pig_count: number;
  min_feed_stock_threshold: number;
  // Start summary (optional, populated after trigger)
  total_animal_count?: number;
  average_start_date?: string;
  distinct_origin_count?: number;
  origin_types?: string[];
}

export interface FeedSchedule {
  pk: string;
  sk: string;
  feed_type: string;
  planned_date: string;
  expected_amount_kg: number;
  fulfilled_by?: string;
}

export interface FeedTruckArrival {
  pk: string;
  sk: string;
  receive_date: string;
  fiscal_document_number: string;
  actual_amount_kg: number;
  feed_type: string;
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
}

export interface MedicationShot {
  pk: string;
  sk: string;
  medication_name: string;
  shot_count: number;
  date: string;
}

export interface FeedConsumptionPlanEntry {
  day_number: number;
  expected_grams_per_animal: number;
  date: string;
}

export interface FeedBalance {
  pk: string;
  sk: string;
  measurement_date: string;
  balance_kg: number;
}
