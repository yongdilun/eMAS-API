/**
 * Shared labels for RAG / citation chips (Linear-style: clear title · Source n).
 */

export function formatDocDisplayName(source, fallbackNum) {
  const raw = source?.title || source?.doc_id || ''
  const stripped = String(raw).replace(/\.[^/.]+$/, '').trim()
  if (stripped) return stripped
  return fallbackNum != null ? `Source ${fallbackNum}` : 'Source'
}

/** Full chip label for inline citations and source rows */
export function formatCitationChipLabel(source, sourceNumber) {
  const name = formatDocDisplayName(source, sourceNumber)
  return `${name} · Source ${sourceNumber}`
}

/** Subtitle under "Answer" — design copy */
export function formatBasedOnLine(sources = []) {
  if (!sources.length) return ''
  if (sources.length === 1) {
    return `Based on ${formatDocDisplayName(sources[0], sources[0].source_number)}`
  }
  const first = formatDocDisplayName(sources[0], sources[0].source_number)
  const rest = sources.length - 1
  return `Based on ${first} and ${rest} other source${rest === 1 ? '' : 's'}`
}
