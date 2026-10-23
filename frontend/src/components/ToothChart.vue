<template>
	<div>
		<div class="mb-2 flex flex-wrap items-center gap-2">
			<div class="flex overflow-hidden rounded border text-xs">
				<button
					v-for="m in CHART_MODES"
					:key="m"
					class="px-2 py-1"
					:class="chartMode === m ? 'bg-gray-900 text-white' : ''"
					@click="chartMode = m"
				>
					{{ m }}
				</button>
			</div>
			<span class="text-xs text-gray-500">{{ multiSelect ? 'Click teeth to select multiple' : 'Click a tooth' }}</span>
			<button
				class="ml-auto rounded border px-2 py-1 text-xs"
				:class="multiSelect ? 'border-gray-900 bg-gray-900 text-white' : 'border-gray-300'"
				@click="toggleMultiSelect"
			>
				{{ multiSelect ? 'Multi-select on' : 'Select multiple teeth' }}
			</button>
		</div>

		<div class="space-y-1">
			<div v-for="(toothRow, r) in toothRows" :key="r" class="flex flex-wrap justify-center gap-1">
				<button
					v-for="tooth in toothRow"
					:key="tooth"
					class="relative h-9 w-9 rounded border text-xs font-medium hover:bg-gray-100"
					:class="[
						isHighlighted(tooth) ? 'border-gray-900 ring-1 ring-gray-900' : 'border-gray-300',
						countFor(tooth) ? 'border-red-300 bg-red-50 text-red-700' : '',
					]"
					@click="onToothClick(tooth)"
				>
					{{ tooth }}
					<span
						v-if="countFor(tooth)"
						class="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-600 text-[9px] text-white"
					>
						{{ countFor(tooth) }}
					</span>
				</button>
			</div>
		</div>

		<div v-if="panelTeeth.length" class="mt-3 rounded border bg-gray-50 p-3">
			<div class="mb-2 text-sm font-medium">
				{{ panelTeeth.length > 1 ? `Teeth ${panelTeeth.join(', ')} findings` : `Tooth ${panelTeeth[0]} findings` }}
			</div>

			<div class="mb-3 space-y-3">
				<div v-for="tooth in panelTeeth" :key="tooth">
					<div v-if="panelTeeth.length > 1" class="mb-1 text-xs font-semibold text-gray-700">Tooth {{ tooth }}</div>
					<p v-if="!rowsFor(tooth).length" class="text-xs text-gray-400">No findings yet</p>
					<div v-for="(row, i) in rowsFor(tooth)" :key="i" class="mb-2 rounded border bg-white p-2 text-xs">
						<div class="mb-1 flex items-center justify-between gap-2">
							<span class="font-medium">{{ row.finding_name }}</span>
							<button class="text-red-600" @click="removeRow(row)">remove</button>
						</div>
						<textarea
							v-model="row.description"
							rows="5"
							class="w-full resize-y rounded border px-2 py-1 text-sm"
							@input="emitUpdate"
						></textarea>
					</div>
				</div>
			</div>

			<FindingPicker :items="toothFindingsMaster" label-field="finding_name" @pick="addFinding" />

			<div class="mt-3 space-y-1 border-t pt-3">
				<input v-model="customName" placeholder="Custom finding name" class="w-full rounded border px-2 py-1 text-xs" />
				<textarea
					v-model="customDescription"
					rows="3"
					placeholder="Description (leave empty to use the name)"
					class="w-full resize-y rounded border px-2 py-1 text-sm"
				></textarea>
				<div class="flex items-center justify-between">
					<span class="text-[11px] text-gray-500">Saved to the list for future reports.</span>
					<button class="rounded bg-gray-900 px-2 py-1 text-xs text-white" @click="addCustom">Add</button>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from 'vue'
import FindingPicker from './FindingPicker.vue'
import { fillToothNumber, dropToothNumber } from '../findingText'

const props = defineProps({
	arch: { type: String, required: true }, // 'Maxillary' | 'Mandibular'
	toothFindings: { type: Array, default: () => [] },
	toothFindingsMaster: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:toothFindings'])

const UPPER = ['18', '17', '16', '15', '14', '13', '12', '11', '21', '22', '23', '24', '25', '26', '27', '28']
const LOWER = ['48', '47', '46', '45', '44', '43', '42', '41', '31', '32', '33', '34', '35', '36', '37', '38']
const UPPER_CHILD = ['55', '54', '53', '52', '51', '61', '62', '63', '64', '65']
const LOWER_CHILD = ['85', '84', '83', '82', '81', '71', '72', '73', '74', '75']
const CHILD_TEETH = new Set([...UPPER_CHILD, ...LOWER_CHILD])
const CHART_MODES = ['Adult', 'Child', 'Mixed']

const chartMode = ref(props.toothFindings.some((r) => CHILD_TEETH.has(r.tooth_number)) ? 'Mixed' : 'Adult')

const toothRows = computed(() => {
	const adult = props.arch === 'Maxillary' ? UPPER : LOWER
	const child = props.arch === 'Maxillary' ? UPPER_CHILD : LOWER_CHILD
	if (chartMode.value === 'Adult') return [adult]
	if (chartMode.value === 'Child') return [child]
	// Deciduous row sits toward the occlusal plane: below upper, above lower.
	return props.arch === 'Maxillary' ? [adult, child] : [child, adult]
})

const multiSelect = ref(false)
const selectedTooth = ref(null)
const selectedTeeth = ref([])
const customName = ref('')
const customDescription = ref('')

const panelTeeth = computed(() =>
	multiSelect.value ? selectedTeeth.value : selectedTooth.value ? [selectedTooth.value] : [],
)

function toggleMultiSelect() {
	multiSelect.value = !multiSelect.value
	selectedTeeth.value = []
	selectedTooth.value = null
}

function onToothClick(tooth) {
	if (multiSelect.value) {
		const i = selectedTeeth.value.indexOf(tooth)
		if (i === -1) selectedTeeth.value = [...selectedTeeth.value, tooth]
		else selectedTeeth.value = selectedTeeth.value.filter((t) => t !== tooth)
	} else {
		selectedTooth.value = selectedTooth.value === tooth ? null : tooth
	}
}

function isHighlighted(tooth) {
	return multiSelect.value ? selectedTeeth.value.includes(tooth) : selectedTooth.value === tooth
}

function rowsFor(tooth) {
	return props.toothFindings.filter((r) => r.tooth_number === tooth)
}
function countFor(tooth) {
	return rowsFor(tooth).length
}

function emitUpdate() {
	emit('update:toothFindings', [...props.toothFindings])
}

function rowsForPanel(fields) {
	return panelTeeth.value.map((tooth) => ({ tooth_number: tooth, arch: props.arch, ...fields }))
}

function addFinding(masterFinding) {
	const newRows = rowsForPanel({
		finding: masterFinding.name,
		finding_name: masterFinding.finding_name,
		description: fillToothNumber(masterFinding.description_template, panelTeeth.value),
	})
	emit('update:toothFindings', [...props.toothFindings, ...newRows])
}

function addCustom() {
	const name = customName.value.trim()
	if (!name || !panelTeeth.value.length) return
	const newRows = rowsForPanel({
		finding: null,
		finding_name: name,
		description: customDescription.value.trim() || name,
	})
	emit('update:toothFindings', [...props.toothFindings, ...newRows])
	customName.value = ''
	customDescription.value = ''
}

function removeRow(row) {
	// The same finding added to several teeth at once lists all of them in
	// each tooth's text - take the removed tooth out of the others' lists.
	const template = row.finding
		? props.toothFindingsMaster.find((f) => f.name === row.finding)?.description_template
		: null
	const remaining = props.toothFindings.filter((r) => r !== row)
	if (template) {
		for (const r of remaining) {
			if (r.finding === row.finding) r.description = dropToothNumber(r.description, template, row.tooth_number)
		}
	}
	emit('update:toothFindings', remaining)
}
</script>
