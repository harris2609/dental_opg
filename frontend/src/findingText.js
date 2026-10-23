// Mirrors report_builder._render_template: only {side}, {tooth_number},
// {level} are substituted; whitespace collapsed.
const PLACEHOLDER = /\{(side|tooth_number|level)\}/g
const DANGLING_TOOTH_REF = /\s+(irt|wrt)\s*$/i

export function renderTemplate(template, row) {
	const values = {
		side: (row.side || '').toLowerCase(),
		tooth_number: row.tooth_number || '',
		level: (row.level || '').toLowerCase(),
	}
	return (template || '')
		.replace(PLACEHOLDER, (_, key) => values[key])
		.split(/\s+/)
		.filter(Boolean)
		.join(' ')
		.replace(DANGLING_TOOTH_REF, '')
}

// Clinic finding texts carry a literal "(tooth number)" placeholder.
export function fillToothNumber(text, teeth) {
	return (text || '').replaceAll('(tooth number)', teeth.join(', '))
}

const TOOTH_PLACEHOLDER = '(tooth number)'

function escapeRegExp(text) {
	return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// Undo one tooth of a multi-select fill: if `text` is still exactly
// `template` filled with a tooth list that contains `tooth`, return it
// refilled without that tooth. Hand-edited text is returned unchanged.
export function dropToothNumber(text, template, tooth) {
	if (!template || !template.includes(TOOTH_PLACEHOLDER)) return text
	const pattern = template
		.split(TOOTH_PLACEHOLDER)
		.map(escapeRegExp)
		.join('(\\d+(?:, \\d+)*)')
	const match = new RegExp(`^${pattern}$`).exec(text || '')
	if (!match) return text
	const teeth = match[1].split(', ')
	if (!teeth.includes(tooth) || match.slice(1).some((list) => list !== match[1])) return text
	return fillToothNumber(template, teeth.filter((t) => t !== tooth))
}
