import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { formatNumber } from '../../i18n';
import type { BatchFinancialResult } from '../../types/models';

interface BorderoViewProps {
  results: BatchFinancialResult[];
}

function formatBRL(value: number): string {
  return value.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
  });
}

function netIncomeColor(value: number): string {
  return value >= 0 ? '#16a34a' : '#dc2626';
}

export default function BorderoView({ results }: BorderoViewProps) {
  const { t } = useTranslation();

  const simulation = useMemo(
    () => results.find((r) => r.type === 'simulation') ?? null,
    [results],
  );
  const actual = useMemo(
    () => results.find((r) => r.type === 'actual') ?? null,
    [results],
  );

  if (!simulation && !actual) {
    return (
      <div className="table-empty">
        {t('pigs.noFinancialResult', 'Nenhum resultado financeiro')}
      </div>
    );
  }

  const columns: (BatchFinancialResult | null)[] =
    simulation && actual ? [simulation, actual] : [simulation ?? actual];

  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="table" style={{ width: '100%' }}>
        <thead>
          <tr>
            <th style={{ minWidth: '200px' }}></th>
            {columns.map((col) => (
              <th key={col!.type} style={{ textAlign: 'right' }}>
                {col!.type === 'simulation'
                  ? t('pigs.simulation', 'Simulação')
                  : t('pigs.actual', 'Realizado')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {/* Dados da Granja */}
          <SectionHeader
            label={t('pigs.farmData', 'Dados da Granja')}
            colSpan={columns.length + 1}
          />
          <Row label={t('pigs.housedCount', 'Alojados')} columns={columns} render={(r) => String(r.housed_count)} />
          <Row label={t('pigs.mortalityCountField', 'Mortalidade (qtd)')} columns={columns} render={(r) => String(r.mortality_count)} />
          <Row label={t('pigs.pigCount', 'Suínos Entregues')} columns={columns} render={(r) => String(r.pig_count)} />
          <Row label={t('pigs.pigletWeightField', 'Peso Leitão (kg)')} columns={columns} render={(r) => formatNumber(r.piglet_weight, 2)} />
          <Row label={t('pigs.pigWeightField', 'Peso Suíno (kg)')} columns={columns} render={(r) => formatNumber(r.pig_weight, 2)} />
          <Row label={t('pigs.totalFeed', 'Ração Total (kg)')} columns={columns} render={(r) => formatNumber(r.total_feed, 2)} />
          <Row label={t('pigs.daysHousedField', 'Dias Alojados')} columns={columns} render={(r) => String(r.days_housed)} />

          {/* Dados da Integradora */}
          <SectionHeader
            label={t('pigs.integratorParams', 'Dados da Integradora')}
            colSpan={columns.length + 1}
          />
          <Row label={t('pigs.capField', 'CAP')} columns={columns} render={(r) => formatNumber(r.cap, 4)} />
          <Row label={t('pigs.mapField', 'MAP')} columns={columns} render={(r) => formatNumber(r.map_value, 4)} />
          <Row label={t('pigs.pricePerKgField', 'Preço/kg (R$)')} columns={columns} render={(r) => formatBRL(r.price_per_kg)} />
          <Row label={t('pigs.grossIntegratorPct', '% Integrado Bruto')} columns={columns} render={(r) => formatNumber(r.gross_integrator_pct, 1) + '%'} />

          {/* Carcaça */}
          <SectionHeader
            label={t('pigs.carcassSection', 'Carcaça')}
            colSpan={columns.length + 1}
          />
          <Row label={t('pigs.carcassYieldFactor', 'Fator Rendimento')} columns={columns} render={(r) => formatNumber(r.carcass_yield_factor, 4)} />
          <Row label={t('pigs.pigletCarcassWeight', 'Peso Carcaça Leitão (kg)')} columns={columns} render={(r) => formatNumber(r.piglet_carcass_weight, 4)} />
          <Row label={t('pigs.pigCarcassWeight', 'Peso Carcaça Suíno (kg)')} columns={columns} render={(r) => formatNumber(r.pig_carcass_weight, 4)} />
          <Row label={t('pigs.totalPigletCarcass', 'Total Carcaça Leitão (kg)')} columns={columns} render={(r) => formatNumber(r.total_piglet_carcass, 2)} />
          <Row label={t('pigs.totalPigCarcass', 'Total Carcaça Suíno (kg)')} columns={columns} render={(r) => formatNumber(r.total_pig_carcass, 2)} />
          <Row label={t('pigs.totalCarcassProduced', 'Carcaça Produzida (kg)')} columns={columns} render={(r) => formatNumber(r.total_carcass_produced, 2)} />

          {/* Conversão Alimentar */}
          <SectionHeader
            label={t('pigs.feedConversionSection', 'Conversão Alimentar')}
            colSpan={columns.length + 1}
          />
          <Row label={t('pigs.realConversion', 'CA Real')} columns={columns} render={(r) => formatNumber(r.real_conversion, 4)} />
          <Row label={t('pigs.pigletAdjustmentField', 'Ajuste Leitão')} columns={columns} render={(r) => formatNumber(r.piglet_adjustment, 4)} />
          <Row label={t('pigs.carcassAdjustmentField', 'Ajuste Carcaça')} columns={columns} render={(r) => formatNumber(r.carcass_adjustment, 4)} />
          <Row label={t('pigs.adjustedConversion', 'CA Ajustada')} columns={columns} render={(r) => formatNumber(r.adjusted_conversion, 4)} />

          {/* Desempenho */}
          <SectionHeader
            label={t('pigs.performanceSection', 'Desempenho')}
            colSpan={columns.length + 1}
          />
          <Row label={t('pigs.dailyWeightGain', 'GPD (kg)')} columns={columns} render={(r) => formatNumber(r.daily_weight_gain, 4)} />
          <Row label={t('pigs.dailyCarcassGain', 'GPD Carcaça (kg)')} columns={columns} render={(r) => formatNumber(r.daily_carcass_gain, 4)} />

          {/* Mortalidade */}
          <SectionHeader
            label={t('pigs.mortalitySection', 'Mortalidade')}
            colSpan={columns.length + 1}
          />
          <Row label={t('pigs.realMortalityPct', 'Mortalidade Real (%)')} columns={columns} render={(r) => formatNumber(r.real_mortality_pct, 2) + '%'} />
          <Row label={t('pigs.adjustedMortalityPct', 'Mortalidade Ajustada (%)')} columns={columns} render={(r) => formatNumber(r.adjusted_mortality_pct, 2) + '%'} />

          {/* Percentual do Integrado */}
          <SectionHeader
            label={t('pigs.integratorPctSection', 'Percentual do Integrado')}
            colSpan={columns.length + 1}
          />
          <Row label={t('pigs.grossIntegratorPct', '% Integrado Bruto')} columns={columns} render={(r) => formatNumber(r.gross_integrator_pct, 1) + '%'} />
          <Row label={t('pigs.mortalityAdjustmentPct', 'Ajuste Mortalidade (%)')} columns={columns} render={(r) => formatNumber(r.mortality_adjustment_pct, 4) + '%'} />
          <Row label={t('pigs.conversionAdjustmentPct', 'Ajuste Conversão (%)')} columns={columns} render={(r) => formatNumber(r.conversion_adjustment_pct, 4) + '%'} />
          <Row label={t('pigs.integratorPct', '% Integrado')} columns={columns} render={(r) => formatNumber(r.integrator_pct, 4) + '%'} />

          {/* Resultado Final */}
          <SectionHeader
            label={t('pigs.financialResultSection', 'Resultado Final')}
            colSpan={columns.length + 1}
          />
          <Row label={t('pigs.grossIncome', 'Receita Bruta')} columns={columns} render={(r) => formatBRL(r.gross_income)} />
          <Row
            label={t('pigs.netIncome', 'Receita Líquida')}
            columns={columns}
            render={(r) => formatBRL(r.net_income)}
            style={(r) => ({ color: netIncomeColor(r.net_income), fontWeight: 600 })}
          />
          <Row label={t('pigs.grossIncomePerPig', 'Receita Bruta/Suíno')} columns={columns} render={(r) => formatBRL(r.gross_income_per_pig)} />
          <Row
            label={t('pigs.netIncomePerPig', 'Receita Líquida/Suíno')}
            columns={columns}
            render={(r) => formatBRL(r.net_income_per_pig)}
            style={(r) => ({ color: netIncomeColor(r.net_income), fontWeight: 600 })}
          />
        </tbody>
      </table>
    </div>
  );
}

function SectionHeader({ label, colSpan }: { label: string; colSpan: number }) {
  return (
    <tr>
      <td
        colSpan={colSpan}
        style={{
          fontWeight: 700,
          backgroundColor: '#f3f4f6',
          padding: '0.5rem 0.75rem',
          fontSize: '0.9rem',
        }}
      >
        {label}
      </td>
    </tr>
  );
}

function Row({
  label,
  columns,
  render,
  style,
}: {
  label: string;
  columns: (BatchFinancialResult | null)[];
  render: (r: BatchFinancialResult) => string;
  style?: (r: BatchFinancialResult) => React.CSSProperties;
}) {
  return (
    <tr>
      <td style={{ paddingLeft: '1rem' }}>{label}</td>
      {columns.map((col) => (
        <td
          key={col!.type}
          style={{
            textAlign: 'right',
            ...(style && col ? style(col) : {}),
          }}
        >
          {col ? render(col) : '—'}
        </td>
      ))}
    </tr>
  );
}
