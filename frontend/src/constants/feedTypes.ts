/**
 * Feed type code → description mapping.
 * Used to translate supplier product codes to human-readable names.
 */
export const FEED_TYPE_MAP: Record<string, string> = {
  '130867': 'ST01',
  '130871': 'ST02',
  '130887': 'ST03',
  '130888': 'ST04',
  '765668': 'ST05',
  '130906': 'ST06',
  '104278': 'Super Plus',
};

/** Get human-readable description for a feed type code, or the code itself if unknown. */
export function getFeedTypeDescription(code: string): string {
  return FEED_TYPE_MAP[code] ?? code;
}
