import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { useApi } from '../../hooks/useApi';
import { getSell, createSell, updateSell, type SellPayload } from '../../api/client';
import Layout from '../../components/Layout';
import LoadingSpinner from '../../components/LoadingSpinner';
import ErrorMessage from '../../components/ErrorMessage';

function num(value: string): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function str(value: number | undefined | null): string {
  return value == null ? '' : String(value);
}

export default function SellFormView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { sellId } = useParams<{ sellId: string }>();
  const { user, logout } = useAuth();

  const isEdit = !!sellId;

  const [sellDate, setSellDate] = useState('');
  const [numberOfAnimals, setNumberOfAnimals] = useState('');
  const [animalAge, setAnimalAge] = useState('');
  const [sex, setSex] = useState<'' | 'M' | 'F'>('');
  const [batch, setBatch] = useState('');
  const [description, setDescription] = useState('');
  const [buyer, setBuyer] = useState('');
  const [averageWeight, setAverageWeight] = useState('');
  const [unitValue, setUnitValue] = useState('');
  const [totalValue, setTotalValue] = useState('');
  const [totalCommission, setTotalCommission] = useState('');
  const [totalTransportation, setTotalTransportation] = useState('');
  const [pricePerArroba, setPricePerArroba] = useState('');
  const [associatedTags, setAssociatedTags] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSell = useCallback(
    () => (isEdit && sellId ? getSell(sellId) : Promise.resolve(null)),
    [isEdit, sellId],
  );
  const { data: sell, loading, error: loadError } = useApi(fetchSell);

  useEffect(() => {
    if (!sell) return;
    setSellDate(sell.sell_date ?? '');
    setNumberOfAnimals(str(sell.number_of_animals));
    setAnimalAge(str(sell.animal_age));
    setSex((sell.sex as '' | 'M' | 'F') ?? '');
    setBatch(sell.batch ?? '');
    setDescription(sell.description ?? '');
    setBuyer(sell.buyer ?? '');
    setAverageWeight(str(sell.average_weight));
    setUnitValue(str(sell.unit_value));
    setTotalValue(str(sell.total_value));
    setTotalCommission(str(sell.total_commission));
    setTotalTransportation(str(sell.total_transportation));
    setPricePerArroba(str(sell.price_per_arroba));
    setAssociatedTags((sell.associated_ear_tags ?? []).join(', '));
  }, [sell]);

  // net_value = total_value - total_commission - total_transportation (live preview; server recomputes)
  const netValue = num(totalValue) - num(totalCommission) - num(totalTransportation);

  const orNull = (v: string): string | null => (v.trim() ? v.trim() : null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const tags = associatedTags
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    const payload: SellPayload = {
      sell_date: sellDate.replace(/-/g, ''),
      number_of_animals: num(numberOfAnimals),
      animal_age: animalAge.trim() ? num(animalAge) : null,
      sex: sex || null,
      batch: orNull(batch),
      description: orNull(description),
      buyer: orNull(buyer),
      average_weight: num(averageWeight),
      unit_value: num(unitValue),
      total_value: num(totalValue),
      total_commission: num(totalCommission),
      total_transportation: num(totalTransportation),
      price_per_arroba: num(pricePerArroba),
      associated_ear_tags: tags.length > 0 ? tags : null,
    };

    setSubmitting(true);
    try {
      if (isEdit && sellId) {
        await updateSell(sellId, payload);
      } else {
        await createSell(payload);
      }
      navigate('/cattle/sells');
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  };

  const title = isEdit ? t('cattle.editSell', 'Editar Venda') : t('cattle.newSell', 'Nova Venda');

  const breadcrumbs = [
    { label: t('nav.home'), to: '/' },
    { label: t('nav.cattle'), to: '/cattle' },
    { label: t('cattle.sells', 'Vendas'), to: '/cattle/sells' },
    { label: title },
  ];

  return (
    <Layout breadcrumbs={breadcrumbs} userName={user?.name} userEmail={user?.email} onLogout={logout}>
      <h1 className="page-title">{title}</h1>

      {isEdit && loading && <LoadingSpinner />}
      {isEdit && loadError && <ErrorMessage message={loadError} />}
      {error && <div className="alert alert-error">{error}</div>}

      {(!isEdit || (!loading && !loadError)) && (
        <form onSubmit={handleSubmit} style={{ maxWidth: '520px' }}>
          <label className="form-label">
            {t('cattle.sellDate', 'Data')} *
            <input type="date" required value={sellDate} onChange={(e) => setSellDate(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.numberOfAnimals', 'Nº de Animais')} *
            <input type="number" required min={0} value={numberOfAnimals} onChange={(e) => setNumberOfAnimals(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.animalAge', 'Idade dos Animais')}
            <input type="number" min={0} value={animalAge} onChange={(e) => setAnimalAge(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.sex', 'Sexo')}
            <select value={sex} onChange={(e) => setSex(e.target.value as '' | 'M' | 'F')} className="form-input">
              <option value="">—</option>
              <option value="F">{t('cattle.female', 'Fêmea')}</option>
              <option value="M">{t('cattle.male', 'Macho')}</option>
            </select>
          </label>

          <label className="form-label">
            {t('cattle.batch', 'Lote')}
            <input type="text" value={batch} onChange={(e) => setBatch(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.buyer', 'Comprador')}
            <input type="text" value={buyer} onChange={(e) => setBuyer(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.description', 'Descrição')}
            <textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.averageWeight', 'Peso Médio (kg)')}
            <input type="number" step="0.01" min={0} value={averageWeight} onChange={(e) => setAverageWeight(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.unitValue', 'Valor Unitário')}
            <input type="number" step="0.01" min={0} value={unitValue} onChange={(e) => setUnitValue(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.pricePerArroba', 'Preço por @')}
            <input type="number" step="0.01" min={0} value={pricePerArroba} onChange={(e) => setPricePerArroba(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.totalValue', 'Valor Total')}
            <input type="number" step="0.01" min={0} value={totalValue} onChange={(e) => setTotalValue(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.totalCommission', 'Comissão Total')}
            <input type="number" step="0.01" min={0} value={totalCommission} onChange={(e) => setTotalCommission(e.target.value)} className="form-input" />
          </label>

          <label className="form-label">
            {t('cattle.totalTransportation', 'Frete Total')}
            <input type="number" step="0.01" min={0} value={totalTransportation} onChange={(e) => setTotalTransportation(e.target.value)} className="form-input" />
          </label>

          <div className="form-label" style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600 }}>
            <span>{t('cattle.netValue', 'Valor Líquido')}</span>
            <span>R$ {netValue.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
          </div>

          <label className="form-label">
            {t('cattle.associatedAnimals', 'Animais Associados (brincos)')}
            <input
              type="text"
              value={associatedTags}
              onChange={(e) => setAssociatedTags(e.target.value)}
              className="form-input"
              placeholder={t('cattle.associatedAnimalsHint', 'Separe os brincos por vírgula. Ficarão com status Vendida.')}
            />
          </label>

          <div style={{ marginTop: 'var(--space-md)', display: 'flex', gap: 'var(--space-sm)' }}>
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/cattle/sells')}>
              {t('common.cancel')}
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? t('common.loading') : isEdit ? t('common.save') : t('common.create')}
            </button>
          </div>
        </form>
      )}
    </Layout>
  );
}
