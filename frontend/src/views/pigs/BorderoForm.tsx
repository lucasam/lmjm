import { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { postBatchFinancialResult } from '../../api/client';
import {
  calculateBordero,
  selectCapMapVariant,
  findNearestWeeklyData,
} from '../../lib/borderoCalculator';
import type { BorderoResult, IntegratorWeeklyDataRecord } from '../../lib/borderoCalculator';
import type { Batch, BatchFinancialResult, IntegratorWeeklyData } from '../../types/models';
import { formatNumber } from '../../i18n';

interface BorderoFormProps {
  batchId: string;
  batch: Batch;
  weeklyDataRecords: IntegratorWeeklyData[];
  existingResult?: BatchFinancialResult;
  onClose: () => void;
  onSaved: () => void;
}

/** Convert IntegratorWeeklyData (API model) to the calculator's record shape. */
function toWeeklyRecord(d: IntegratorWeeklyData): IntegratorWeeklyDataRecord {
  return {
    dateGenerated: d.date_generated,
    validityStart: d.validity_start,
    validityEnd: d.validity_end,
    cap1: d.cap_1,
    cap2: d.cap_2,
    cap3: d.cap_3,
    cap4: d.cap_4,
    map1: d.map_1,
    map2: d.map_2,
  };
}

export default function BorderoForm({
  batchId,
  batch,
  weeklyDataRecords,
  existingResult,
  onClose,
  onSaved,
}: BorderoFormProps) {
  const { t } = useTranslation();
  const isEdit = !!existingResult;

  // --- Derive defaults from batch ---
  const defaultHousedCount = existingResult?.housed_count ?? batch.total_animal_count ?? 0;
  const defaultMortalityCount = existingResult?.mortality_count ?? 0;
  const defaultTotalFeed = existingResult?.total_feed ?? 0;
  const defaultPigletWeight = existingResult?.piglet_weight ?? batch.initial_animal_weight ?? '';
  const defaultDaysHoused = existingResult?.days_housed ?? (() => {
    if (!batch.average_start_date) return '';
    const start = new Date(batch.average_start_date + 'T00:00:00');
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    return Math.max(0, Math.round((now.getTime() - start.getTime()) / 86400000));
  })();

  // --- Auto-suggest CAP/MAP from weekly data ---
  const suggestedCapMap = useMemo(() => {
    if (weeklyDataRecords.length === 0) return null;
    const records = weeklyDataRecords.map(toWeeklyRecord);
    const targetDate = batch.expected_slaughter_date ?? new Date().toISOString().substring(0, 10);
    const nearest = findNearestWeeklyData(records, targetDate);
    if (!nearest) return null;

    const distinctOriginCount = batch.distinct_origin_count ?? 1;
    const predominantOriginType: 'Creche' | 'UPL' =
      batch.origin_types && batch.origin_types.includes('Creche') ? 'Creche' : 'UPL';

    return selectCapMapVariant(distinctOriginCount, predominantOriginType, nearest);
  }, [weeklyDataRecords, batch]);

  // --- Form state ---
  const [type, setType] = useState<'simulation' | 'actual'>(
    (existingResult?.type as 'simulation' | 'actual') ?? 'simulation',
  );
  const [housedCount, setHousedCount] = useState(String(defaultHousedCount));
  const [mortalityCount, setMortalityCount] = useState(String(defaultMortalityCount));
  const [totalFeed, setTotalFeed] = useState(String(defaultTotalFeed));
  const [pigletWeight, setPigletWeight] = useState(String(defaultPigletWeight));
  const [daysHoused, setDaysHoused] = useState(String(defaultDaysHoused));
  const [pigWeight, setPigWeight] = useState(existingResult?.pig_weight != null ? String(existingResult.pig_weight) : '');
  const [cap, setCap] = useState(
    existingResult?.cap != null ? String(existingResult.cap) : suggestedCapMap ? String(suggestedCapMap.cap) : '',
  );
  const [mapValue, setMapValue] = useState(
    existingResult?.map_value != null ? String(existingResult.map_value) : suggestedCapMap ? String(suggestedCapMap.map) : '',
  );
  const [pricePerKg, setPricePerKg] = useState(existingResult?.price_per_kg != null ? String(existingResult.price_per_kg) : '');
  const [pigletAdjustment, setPigletAdjustment] = useState(
    existingResult?.piglet_adjustment != null ? String(existingResult.piglet_adjustment) : '0',
  );
  const [carcassAdjustment, setCarcassAdjustment] = useState(
    existingResult?.carcass_adjustment != null ? String(existingResult.carcass_adjustment) : '0',
  );

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // --- Live preview ---
  const preview: BorderoResult | null = useMemo(() => {
    const h = Number(housedCount);
    const m = Number(mortalityCount);
    const tf = Number(totalFeed);
    const pw = Number(pigletWeight);
    const pgw = Number(pigWeight);
    const dh = Number(daysHoused);
    const c = Number(cap);
    const mv = Number(mapValue);
    const ppk = Number(pricePerKg);
    const pa = Number(pigletAdjustment);
    const ca = Number(carcassAdjustment);

    if (!h || !pgw || !dh) return null;

    return calculateBordero({
      housedCount: h,
      mortalityCount: m,
      pigletWeight: pw,
      pigWeight: pgw,
      totalFeed: tf,
      daysHoused: dh,
      cap: c,
      mapValue: mv,
      pricePerKg: ppk,
      pigletAdjustment: pa,
      carcassAdjustment: ca,
    });
  }, [housedCount, mortalityCount, totalFeed, pigletWeight, pigWeight, daysHoused, cap, mapValue, pricePerKg, pigletAdjustment, carcassAdjustment]);

  // --- Submit ---
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await postBatchFinancialResult(batchId, {
        type,
        housed_count: Number(housedCount),
        mortality_count: Number(mortalityCount),
        total_feed: Number(totalFeed),
        piglet_weight: Number(pigletWeight),
        pig_weight: Number(pigWeight),
        days_housed: Number(daysHoused),
        cap: Number(cap),
        map_value: Number(mapValue),
        price_per_kg: Number(pricePerKg),
        piglet_adjustment: Number(pigletAdjustment),
        carcass_adjustment: Number(carcassAdjustment),
      });
      setSuccess(true);
      setTimeout(onSaved, 800);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const fmt = (v: number | undefined | null, decimals = 4) =>
    v != null ? formatNumber(v, decimals) : '—';

  const fmtCurrency = (v: number | undefined | null) =>
    v != null
      ? v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2 })
      : '—';

  return (
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '720px' }}>
        <h2 className="modal-title">
          {isEdit ? t('pigs.editBordero', 'Editar Borderô') : t('pigs.newBordero', 'Novo Borderô')}
        </h2>

        {success && <div className="alert alert-success">✓ {t('common.save')}</div>}
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          {/* Type selector */}
          <label className="form-label">
            {t('pigs.borderoType', 'Tipo')} *
            <select
              required
              value={type}
              onChange={(e) => setType(e.target.value as 'simulation' | 'actual')}
              className="form-input"
            >
              <option value="simulation">{t('pigs.simulation', 'Simulação')}</option>
              <option value="actual">{t('pigs.actual', 'Realizado')}</option>
            </select>
          </label>

          {/* Farm data section */}
          <h3 className="section-title" style={{ fontSize: '1rem', marginTop: '1rem' }}>
            {t('pigs.farmData', 'Dados da Granja')}
          </h3>

          <label className="form-label">
            {t('pigs.housedCount', 'Alojados')} *
            <input type="number" required min="1" step="1" value={housedCount} onChange={(e) => setHousedCount(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.mortalityCountField', 'Mortalidade (qtd)')} *
            <input type="number" required min="0" step="1" value={mortalityCount} onChange={(e) => setMortalityCount(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.totalFeed', 'Ração Total (kg)')} *
            <input type="number" required min="0" step="any" value={totalFeed} onChange={(e) => setTotalFeed(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.pigletWeightField', 'Peso Leitão (kg)')} *
            <input type="number" required min="0" step="any" value={pigletWeight} onChange={(e) => setPigletWeight(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.daysHousedField', 'Dias Alojados')} *
            <input type="number" required min="1" step="1" value={daysHoused} onChange={(e) => setDaysHoused(e.target.value)} className="form-input" />
          </label>

          {/* Integrator params section */}
          <h3 className="section-title" style={{ fontSize: '1rem', marginTop: '1rem' }}>
            {t('pigs.integratorParams', 'Dados da Integradora')}
          </h3>

          <label className="form-label">
            {t('pigs.capField', 'CAP')} *
            <input type="number" required step="any" value={cap} onChange={(e) => setCap(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.mapField', 'MAP')} *
            <input type="number" required step="any" value={mapValue} onChange={(e) => setMapValue(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.pricePerKgField', 'Preço/kg (R$)')} *
            <input type="number" required min="0" step="any" value={pricePerKg} onChange={(e) => setPricePerKg(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.grossIntegratorPct', '% Integrado Bruto')}
            <input type="text" readOnly value="5,1%" className="form-input" style={{ backgroundColor: '#f3f4f6' }} />
          </label>

          {/* Pig weight and adjustments */}
          <h3 className="section-title" style={{ fontSize: '1rem', marginTop: '1rem' }}>
            {t('pigs.weightAndAdjustments', 'Peso e Ajustes')}
          </h3>

          <label className="form-label">
            {t('pigs.pigWeightField', 'Peso Suíno (kg)')} *
            <input type="number" required min="0" step="any" value={pigWeight} onChange={(e) => setPigWeight(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.pigletAdjustmentField', 'Ajuste Leitão')}
            <input type="number" step="any" value={pigletAdjustment} onChange={(e) => setPigletAdjustment(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('pigs.carcassAdjustmentField', 'Ajuste Carcaça')}
            <input type="number" step="any" value={carcassAdjustment} onChange={(e) => setCarcassAdjustment(e.target.value)} className="form-input" />
          </label>

          {/* Live preview panel */}
          <h3 className="section-title" style={{ fontSize: '1rem', marginTop: '1rem' }}>
            {t('pigs.livePreview', 'Prévia')}
          </h3>

          <div style={{ background: '#f9fafb', borderRadius: '8px', padding: '0.75rem', fontSize: '0.9rem' }}>
            <PreviewRow label={t('pigs.pigCount', 'Suínos Entregues')} value={preview ? String(preview.pigCount) : '—'} />
            <PreviewRow label={t('pigs.carcassYieldFactor', 'Fator Rendimento')} value={fmt(preview?.carcassYieldFactor)} />
            <PreviewRow label={t('pigs.totalCarcassProduced', 'Carcaça Produzida (kg)')} value={fmt(preview?.totalCarcassProduced, 2)} />
            <PreviewRow label={t('pigs.realConversion', 'CA Real')} value={fmt(preview?.realConversion)} />
            <PreviewRow label={t('pigs.adjustedConversion', 'CA Ajustada')} value={fmt(preview?.adjustedConversion)} />
            <PreviewRow label={t('pigs.realMortalityPct', 'Mortalidade Real (%)')} value={fmt(preview?.realMortalityPct, 2)} />
            <PreviewRow label={t('pigs.dailyWeightGain', 'GPD (kg)')} value={fmt(preview?.dailyWeightGain)} />
            <PreviewRow label={t('pigs.integratorPct', '% Integrado')} value={fmt(preview?.integratorPct)} />
            <PreviewRow
              label={t('pigs.grossIncome', 'Receita Bruta')}
              value={fmtCurrency(preview?.grossIncome)}
              highlight={preview ? (preview.grossIncome >= 0 ? 'green' : 'red') : undefined}
            />
            <PreviewRow
              label={t('pigs.netIncome', 'Receita Líquida')}
              value={fmtCurrency(preview?.netIncome)}
              highlight={preview ? (preview.netIncome >= 0 ? 'green' : 'red') : undefined}
            />
            <PreviewRow label={t('pigs.grossIncomePerPig', 'Receita Bruta/Suíno')} value={fmtCurrency(preview?.grossIncomePerPig)} />
          </div>

          <div className="modal-btn-row">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              {t('common.cancel')}
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? t('common.loading') : t('common.submit')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function PreviewRow({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: 'green' | 'red';
}) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.2rem 0' }}>
      <span>{label}</span>
      <span style={highlight ? { color: highlight === 'green' ? '#16a34a' : '#dc2626', fontWeight: 600 } : undefined}>
        {value}
      </span>
    </div>
  );
}
