<template>
	<div>
		<div class="mb-2 flex items-center justify-between">
			<span class="text-xs text-gray-500">{{ multiSelect ? 'Click teeth to select multiple' : 'Click a tooth' }}</span>
			<button
				class="rounded border px-2 py-1 text-xs"
				:class="multiSelect ? 'border-gray-900 bg-gray-900 text-white' : 'border-gray-300'"
				@click="toggleMultiSelect"
			>
				{{ multiSelect ? 'Multi-select on' : 'Select multiple teeth' }}
			</button>
		</div>

		<div class="flex flex-wrap justify-center gap-1">
			<button
				v-for="tooth in teeth"
				:key="tooth"
				class="relative h-9 w-9 rounded border text-xs font-medium hover:bg-gray-100"
				:class="[
					isHighlighted(tooth) ? 'border-gray-900 ring-1 ring-gray-900' : 'border-gray-300',
					countFor(tooth) ? 'bg-red-50 text-red-700 border-red-300' : '',
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

		<div v-if="panelTeeth.length" class="mt-3 rounded border bg-gray-50 p-3">
			<div class="mb-2 text-sm font-medium">
				{{ panelTeeth.length > 1 ? `Teeth ${panelTeeth.join(', ')} findings` : `Tooth ${panelTeeth[0]} findings` }}
			</div>

			<div v-if="!multiSelect" class="mb-3 space-y-2">
				<div v-for="(row, idx) in singleToothRows" :key="idx" class="rounded border bg-white p-2 text-xs">
					<div class="mb-1 flex items-center justify-between">
						<span class="font-medium">{{ row.finding_name }}</span>
						<button class="text-red-600" @click="removeRow(row)">remove</button>
					</div>
					<textarea
						v-model="row.description"
						rows="2"
						class="w-full rounded border px-2 py-1 text-xs"
						@input="emitUpdate"
					></textarea>
				</div>
			</div>

			<div class="mb-2 flex flex-wrap gap-1.5">
				<button
					v-for="mf in toothFindingsMaster"
					:key="mf.name"
					class="rounded-full border border-gray-300 px-2.5 py-1 text-xs hover:bg-gray-100"
					@click="addFinding(mf)"
				>
					+ {{ mf.finding_name }}
				</button>
			</div>

			<div class="flex gap-2">
				<input
					v-model="customText"
					placeholder="Add custom finding"
					class="flex-1 rounded border px-2 py-1 text-xs"
					@keyup.enter="addCustom"
				/>
				<button class="rounded bg-gray-900 px-2 py-1 text-xs text-white" @click="addCustom">Add</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
	arch: { type: String, required: true }, // 'Maxillary' | 'Mandibular'
	toothFindings: { type: Array, default: () => [] },
	toothFindingsMaster: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:toothFindings'])

const UPPER = ['18', '17', '16', '15', '14', '13', '12', '11', '21', '22', '23', '24', '25', '26', '27', '28']
const LOWER = ['48', '47', '46', '45', '44', '43', '42', '41', '31', '32', '33', '34', '35', '36', '37', '38']
const teeth = computed(() => (props.arch === 'Maxillary' ? UPPER : LOWER))

const multiSelect = ref(false)
const selectedTooth = ref(null)
const selectedTeeth = ref([])
const customText = ref('')

const panelTeeth = computed(() => (multiSelect.value ? selectedTeeth.value : selectedTooth.value ? [selectedTooth.value] : []))

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

const singleToothRows = computed(() => (selectedTooth.value ? rowsFor(selectedTooth.value) : []))

function emitUpdate() {
	emit('update:toothFindings', [...props.toothFindings])
}

function addFinding(masterFinding) {
	const newRows = panelTeeth.value.map((tooth) => ({
		tooth_number: tooth,
		arch: props.arch,
		finding: masterFinding.name,
		finding_name: masterFinding.finding_name,
		description: masterFinding.description_template,
	}))
	emit('update:toothFindings', [...props.toothFindings, ...newRows])
}

function addCustom() {
	if (!customText.value.trim() || !panelTeeth.value.length) return
	const newRows = panelTeeth.value.map((tooth) => ({
		tooth_number: tooth,
		arch: props.arch,
		finding: null,
		finding_name: customText.value.trim(),
		description: customText.value.trim(),
	}))
	emit('update:toothFindings', [...props.toothFindings, ...newRows])
	customText.value = ''
}

function removeRow(row) {
	emit(
		'update:toothFindings',
		props.toothFindings.filter((r) => r !== row),
	)
}
</script>
