export interface DeathReason {
  code: string;
  description: string;
}

export const DEATH_REASONS: DeathReason[] = [
  { code: '9', description: 'Artrite' },
  { code: '28', description: 'Briga' },
  { code: '31', description: 'Canibalismo' },
  { code: '21', description: 'Circovirose' },
  { code: '11', description: 'Diarréia' },
  { code: '27', description: 'Diarréia de Sangue' },
  { code: '36', description: 'Eliminado:Artrite' },
  { code: '41', description: 'Eliminado:Canibalismo' },
  { code: '37', description: 'Eliminado:Diarréia' },
  { code: '38', description: 'Eliminado:Fratura' },
  { code: '40', description: 'Eliminado:Hérnia' },
  { code: '39', description: 'Eliminado:Pneumonia' },
  { code: '42', description: 'Eliminado:Prolapso' },
  { code: '12', description: 'Encefalite' },
  { code: '13', description: 'Pneumonia' },
  { code: '29', description: 'Prolapso' },
  { code: '32', description: 'Refugagem:Artrite' },
  { code: '33', description: 'Refugagem:Diarréia' },
  { code: '34', description: 'Refugagem:Fratura' },
  { code: '35', description: 'Refugagem:Pneumonia' },
  { code: '22', description: 'Ruptura de Hérnia' },
  { code: '0', description: 'Subita' },
  { code: '23', description: 'Torção do Mesentério' },
  { code: '19', description: 'Ulcera' },
];

export function getDeathReasonDescription(code: string): string {
  const reason = DEATH_REASONS.find((r) => r.code === code);
  return reason ? reason.description : code;
}
