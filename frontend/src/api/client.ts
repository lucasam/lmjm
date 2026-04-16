import type {
  CattleAnimal,
  Insemination,
  Diagnostic,
  Weight,
  Module,
  Batch,
  FeedSchedule,
  FeedTruckArrival,
  PigTruckArrival,
  Mortality,
  Medication,
  MedicationShot,
  FeedConsumptionPlanEntry,
  FeedBalance,
  FiscalDocument,
  FeedScheduleFiscalDocument,
  RawMaterialType,
  BatchFinancialResult,
  IntegratorWeeklyData,
  FeedConsumptionTemplate,
} from '../types/models';

// Request types for POST/PUT operations
export interface PostInseminationRequest {
  insemination_date: string;
  semen: string;
  note?: string;
}

export interface PostDiagnosticRequest {
  diagnostic_date: string;
  pregnant: boolean;
  note?: string;
  tags?: string;
}

export interface CreateBatchRequest {
  supply_id: number;
  module_id: string;
  min_feed_stock_threshold: number;
}

export interface PostFeedTruckArrivalRequest {
  receive_date: string;
  fiscal_document_number: string;
  actual_amount_kg: number;
  feed_type: string;
  feed_description?: string;
  feed_schedule_id?: string;
}

export interface PostPigTruckArrivalRequest {
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

export interface PostMortalityRequest {
  mortality_date: string;
  sex: 'Male' | 'Female';
  origin: string;
  death_reason: string;
  reported_by: string;
}

export interface PostMedicationRequest {
  medication_name: string;
  expiration_date: string;
  part_number: string;
}

export interface PostMedicationShotRequest {
  medication_name: string;
  shot_count: number;
  date: string;
}

export interface PostFeedBalanceRequest {
  measurement_date: string;
  balance_kg: number;
}

import { getConfig } from '../config';
import { isTokenExpired } from '../auth/cognito';

function getBaseUrl(): string {
  return getConfig().apiUrl.replace(/\/+$/, '');
}

class ApiError extends Error {
  constructor(public statusCode: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshTokenVal = localStorage.getItem('lmjm_refresh_token');
  if (!refreshTokenVal) return null;

  try {
    const { cognitoDomain, cognitoClientId } = getConfig();

    const response = await fetch(`${cognitoDomain}/oauth2/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        client_id: cognitoClientId,
        refresh_token: refreshTokenVal,
      }),
    });

    if (!response.ok) return null;

    const data = await response.json();
    localStorage.setItem('lmjm_access_token', data.access_token);
    if (data.id_token) localStorage.setItem('lmjm_id_token', data.id_token);
    return data.access_token as string;
  } catch {
    return null;
  }
}

function clearTokensAndRedirect(): never {
  localStorage.removeItem('lmjm_access_token');
  localStorage.removeItem('lmjm_id_token');
  localStorage.removeItem('lmjm_refresh_token');
  window.location.href = '/login';
  throw new ApiError(401, 'Session expired');
}

async function fetchWithAuth(path: string, options: RequestInit = {}): Promise<Response> {
  let token = localStorage.getItem('lmjm_id_token');

  // Proactively refresh if token is expired or about to expire
  if (!token || isTokenExpired(token)) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      token = localStorage.getItem('lmjm_id_token');
    }
    if (!token || isTokenExpired(token)) {
      clearTokensAndRedirect();
    }
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response = await fetch(`${getBaseUrl()}${path}`, { ...options, headers });

  if (response.status === 401 || response.status === 403) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      // After refresh, both id_token and access_token are updated in localStorage
      const freshIdToken = localStorage.getItem('lmjm_id_token');
      if (freshIdToken) {
        headers['Authorization'] = `Bearer ${freshIdToken}`;
      }
      response = await fetch(`${getBaseUrl()}${path}`, { ...options, headers });
    }
    if (!newToken || response.status === 401 || response.status === 403) {
      clearTokensAndRedirect();
    }
  }

  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      message = body.message ?? message;
    } catch {
      // use statusText
    }
    throw new ApiError(response.status, message);
  }

  return response;
}

async function get<T>(path: string): Promise<T> {
  const response = await fetchWithAuth(path);
  return response.json() as Promise<T>;
}

async function post(path: string, data?: unknown): Promise<void> {
  await fetchWithAuth(path, {
    method: 'POST',
    body: data !== undefined ? JSON.stringify(data) : undefined,
  });
}

async function put(path: string, data: unknown): Promise<void> {
  await fetchWithAuth(path, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// --- Cattle ---

export function listCattleAnimals(): Promise<CattleAnimal[]> {
  return get<CattleAnimal[]>('/cattle/animals');
}

export function getCattleAnimal(earTag: string): Promise<CattleAnimal> {
  return get<CattleAnimal>(`/cattle/animals/${encodeURIComponent(earTag)}`);
}

export function listInseminations(earTag: string): Promise<Insemination[]> {
  return get<Insemination[]>(`/cattle/animals/${encodeURIComponent(earTag)}/inseminations`);
}

export function listDiagnostics(earTag: string): Promise<Diagnostic[]> {
  return get<Diagnostic[]>(`/cattle/animals/${encodeURIComponent(earTag)}/diagnostics`);
}

export function postInsemination(earTag: string, data: PostInseminationRequest): Promise<void> {
  return post(`/cattle/animals/${encodeURIComponent(earTag)}/inseminations`, data);
}

export function postDiagnostic(earTag: string, data: PostDiagnosticRequest): Promise<void> {
  return post(`/cattle/animals/${encodeURIComponent(earTag)}/diagnostics`, data);
}

export function listWeights(earTag: string): Promise<Weight[]> {
  return get<Weight[]>(`/cattle/animals/${encodeURIComponent(earTag)}/pesos`);
}

export function postWeight(earTag: string, data: { weighing_date: string; weight_kg: number }): Promise<void> {
  return post(`/cattle/animals/${encodeURIComponent(earTag)}/pesos`, data);
}

// --- Pig Infrastructure ---

export function listModules(): Promise<Module[]> {
  return get<Module[]>('/pigs/modules');
}

export function getModule(moduleId: string): Promise<Module> {
  return get<Module>(`/pigs/modules/${encodeURIComponent(moduleId)}`);
}

export interface UpdateModuleRequest {
  name?: string;
  area?: number;
  supported_animal_count?: number;
  silo_capacity?: number;
}

export function updateModule(moduleId: string, data: UpdateModuleRequest): Promise<void> {
  return put(`/pigs/modules/${encodeURIComponent(moduleId)}`, data);
}

// --- Pig Batches ---

export function listBatches(): Promise<Batch[]> {
  return get<Batch[]>('/pigs/batches');
}

export function getBatch(batchId: string): Promise<Batch> {
  return get<Batch>(`/pigs/batches/${encodeURIComponent(batchId)}`);
}

export interface UpdateBatchRequest {
  status?: string;
  supply_id?: number;
  expected_slaughter_date?: string;
  min_feed_stock_threshold?: number;
  total_animal_count?: number;
  average_start_date?: string;
  distinct_origin_count?: number;
  origin_types?: string[];
  feed_leftover?: number;
}

export function updateBatch(batchId: string, data: UpdateBatchRequest): Promise<void> {
  return put(`/pigs/batches/${encodeURIComponent(batchId)}`, data);
}

export function createBatch(data: CreateBatchRequest): Promise<void> {
  return post('/pigs/batches', data);
}

export function getFeedSchedule(batchId: string): Promise<FeedSchedule[]> {
  return get<FeedSchedule[]>(`/pigs/batches/${encodeURIComponent(batchId)}/feed-schedule`);
}

export function updateFeedSchedule(batchId: string, data: FeedSchedule[]): Promise<void> {
  return put(`/pigs/batches/${encodeURIComponent(batchId)}/feed-schedule`, data);
}

export function postFeedTruckArrival(batchId: string, data: PostFeedTruckArrivalRequest): Promise<void> {
  return post(`/pigs/batches/${encodeURIComponent(batchId)}/feed-truck-arrivals`, data);
}

export function listFeedTruckArrivals(batchId: string): Promise<FeedTruckArrival[]> {
  return get<FeedTruckArrival[]>(`/pigs/batches/${encodeURIComponent(batchId)}/feed-truck-arrivals`);
}

export function postPigTruckArrival(batchId: string, data: PostPigTruckArrivalRequest): Promise<void> {
  return post(`/pigs/batches/${encodeURIComponent(batchId)}/pig-truck-arrivals`, data);
}

export function listPigTruckArrivals(batchId: string): Promise<PigTruckArrival[]> {
  return get<PigTruckArrival[]>(`/pigs/batches/${encodeURIComponent(batchId)}/pig-truck-arrivals`);
}

export interface UpdatePigTruckArrivalRequest {
  animal_count?: number;
  sex?: 'Male' | 'Female';
  pig_age_days?: number;
  origin_name?: string;
  origin_type?: 'UPL' | 'Creche';
  fiscal_document_number?: string;
  animal_weight?: number;
  gta_number?: string;
  mossa?: string;
  suplier_code?: number;
}

export function updatePigTruckArrival(batchId: string, arrivalSk: string, data: UpdatePigTruckArrivalRequest): Promise<void> {
  return put(`/pigs/batches/${encodeURIComponent(batchId)}/pig-truck-arrivals/${encodeURIComponent(arrivalSk)}`, data);
}

export function createBatchStartSummary(batchId: string): Promise<void> {
  return post(`/pigs/batches/${encodeURIComponent(batchId)}/start-summary`);
}

// --- Mortality ---

export function postMortality(batchId: string, data: PostMortalityRequest): Promise<void> {
  return post(`/pigs/batches/${encodeURIComponent(batchId)}/mortalities`, data);
}

export function listMortalities(batchId: string): Promise<Mortality[]> {
  return get<Mortality[]>(`/pigs/batches/${encodeURIComponent(batchId)}/mortalities`);
}

// --- Medications ---

export function postMedication(batchId: string, data: PostMedicationRequest): Promise<void> {
  return post(`/pigs/batches/${encodeURIComponent(batchId)}/medications`, data);
}

export function listMedications(batchId: string): Promise<Medication[]> {
  return get<Medication[]>(`/pigs/batches/${encodeURIComponent(batchId)}/medications`);
}

export function postMedicationShot(batchId: string, data: PostMedicationShotRequest): Promise<void> {
  return post(`/pigs/batches/${encodeURIComponent(batchId)}/medication-shots`, data);
}

export function listMedicationShots(batchId: string, month?: string): Promise<MedicationShot[]> {
  const query = month ? `?month=${encodeURIComponent(month)}` : '';
  return get<MedicationShot[]>(`/pigs/batches/${encodeURIComponent(batchId)}/medication-shots${query}`);
}

// --- Feed Consumption Plan ---

export function putFeedConsumptionPlan(batchId: string, data: FeedConsumptionPlanEntry[]): Promise<void> {
  return put(`/pigs/batches/${encodeURIComponent(batchId)}/feed-consumption-plan`, data);
}

export function getFeedConsumptionPlan(batchId: string): Promise<FeedConsumptionPlanEntry[]> {
  return get<FeedConsumptionPlanEntry[]>(`/pigs/batches/${encodeURIComponent(batchId)}/feed-consumption-plan`);
}

// --- Feed Balance ---

export function postFeedBalance(batchId: string, data: PostFeedBalanceRequest): Promise<void> {
  return post(`/pigs/batches/${encodeURIComponent(batchId)}/feed-balances`, data);
}

export function listFeedBalances(batchId: string): Promise<FeedBalance[]> {
  return get<FeedBalance[]>(`/pigs/batches/${encodeURIComponent(batchId)}/feed-balances`);
}

// --- Fiscal Documents ---

export function listFiscalDocuments(batchId: string): Promise<FiscalDocument[]> {
  return get<FiscalDocument[]>(`/pigs/batches/${encodeURIComponent(batchId)}/fiscal-documents`);
}

export function listFeedScheduleFiscalDocuments(batchId: string): Promise<FeedScheduleFiscalDocument[]> {
  return get<FeedScheduleFiscalDocument[]>(`/pigs/batches/${encodeURIComponent(batchId)}/feed-schedule-fiscal-documents`);
}

// --- Raw Material Types ---

export function listRawMaterialTypes(): Promise<RawMaterialType[]> {
  return get<RawMaterialType[]>('/raw-material-types');
}

// --- All Fiscal Documents ---

export function listAllFiscalDocuments(): Promise<FiscalDocument[]> {
  return get<FiscalDocument[]>('/fiscal-documents');
}

export function reprocessFiscalDocument(pk: string, fiscalDocumentNumber: string): Promise<void> {
  return post('/fiscal-documents/reprocess', { pk, fiscal_document_number: fiscalDocumentNumber });
}

// --- Batch Financial Results (Borderô) ---

export function postBatchFinancialResult(batchId: string, data: Record<string, unknown>): Promise<void> {
  return post(`/pigs/batches/${encodeURIComponent(batchId)}/financial-results`, data);
}

export function listBatchFinancialResults(batchId: string): Promise<BatchFinancialResult[]> {
  return get<BatchFinancialResult[]>(`/pigs/batches/${encodeURIComponent(batchId)}/financial-results`);
}

// --- Integrator Weekly Data ---

export function postIntegratorWeeklyData(data: Record<string, unknown>): Promise<void> {
  return post('/pigs/integrator-weekly-data', data);
}

export function listIntegratorWeeklyData(): Promise<IntegratorWeeklyData[]> {
  return get<IntegratorWeeklyData[]>('/pigs/integrator-weekly-data');
}

export interface PostRawMaterialTypeRequest {
  code: string;
  description: string;
  category: 'feed' | 'medicine';
}

export function postRawMaterialType(data: PostRawMaterialTypeRequest): Promise<void> {
  return post('/raw-material-types', data);
}

// --- Feed Consumption Templates ---

export interface PostFeedConsumptionTemplateRequest {
  sequence: number;
  expected_piglet_weight: number;
  expected_kg_per_animal: number;
}

export function listFeedConsumptionTemplates(): Promise<FeedConsumptionTemplate[]> {
  return get<FeedConsumptionTemplate[]>('/pigs/feed-consumption-templates');
}

export function postFeedConsumptionTemplate(data: PostFeedConsumptionTemplateRequest): Promise<void> {
  return post('/pigs/feed-consumption-templates', data);
}

export interface GenerateFeedPlanRequest {
  average_start_date?: string;
  initial_animal_weight?: number;
}

export async function generateFeedPlan(batchId: string, params?: GenerateFeedPlanRequest): Promise<FeedConsumptionPlanEntry[]> {
  const response = await fetchWithAuth(`/pigs/batches/${encodeURIComponent(batchId)}/generate-feed-plan`, {
    method: 'POST',
    ...(params ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(params) } : {}),
  });
  return response.json() as Promise<FeedConsumptionPlanEntry[]>;
}
