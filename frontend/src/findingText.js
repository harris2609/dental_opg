// Mirrors report_builder._render_template: only {side}, {tooth_number},
// {level} are substituted; whitespace collapsed.
const PLACEHOLDER = /\{(side|tooth_number|level)\}/g

export function renderTemplate(template, row) {
	const values = {
		side: (row.side || '').toLowerCase(),
		tooth_number: row.tooth_number || '',
		level: (row.level || '').toLowerCase(),
	}
	return (template || '').replace(PLACEHOLDER, (_, key) => values[key]).split(/\s+/).filter(Boolean).join(' ')
}

// Clinic finding texts carry a literal "(tooth number)" placeholder.
export function fillToothNumber(text, teeth) {
	return (text || '').replaceAll('(tooth number)', teeth.join(', '))
}
