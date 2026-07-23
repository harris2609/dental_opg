<template>
	<div>
		<div class="flex flex-wrap justify-center gap-1">
			<button
				v-for="tooth in teeth"
				:key="tooth"
				class="relative h-9 w-9 rounded border text-xs font-medium hover:bg-gray-100"
				:class="[
					selectedTooth === tooth ? 'border-gray-900 ring-1 ring-gray-900' : 'border-gray-300',
					countFor(tooth) ? 'bg-red-50 text-red-700 border-red-300' : '',
				]"
				@click="selectedTooth = selectedTooth === tooth ? null : tooth"
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

		<div v-if="selectedTooth" class="mt-3 rounded border bg-gray-50 p-3">
			<div class="mb-2 text-sm font-medium">Tooth {{ selectedTooth }} findings</div>
			<div class="mb-2 flex flex-wrap gap-2">
				<label
					v-for="mf in toothFindingsMaster"
					:key="mf.name"
					class="flex items-center gap-1 rounded border bg-white px-2 py-1 text-xs"
				>
					<input type="checkbox" :checked="hasFinding(mf.name)" @change="toggleFinding(mf.name)" />
					{{ mf.finding_name }}
				</label>
			</div>
			<div v-for="(row, idx) in customRows" :key="idx" class="mb-1 flex items-center gap-2 text-xs">
				<span class="rounded bg-white px-2 py-1">{{ row.custom_text }}</span>
				<button class="text-red-600" @click="removeRow(row)">remove</button>
			</div>
			<div class="flex gap-2">
				<input
					v-model="customText"
					placeholder="Add custom finding for this tooth"
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

const selectedTooth = ref(null)
const customText = ref('')

function rowsFor(tooth) {
	return props.toothFindings.filter((r) => r.tooth_number === tooth)
}
function countFor(tooth) {
	return rowsFor(tooth).length
}

const customRows = computed(() =>
	selectedTooth.value ? rowsFor(selectedTooth.value).filter((r) => r.is_custom) : [],
)

function hasFinding(findingName) {
	if (!selectedTooth.value) return false
	return rowsFor(selectedTooth.value).some((r) => !r.is_custom && r.finding === findingName)
}

function toggleFinding(findingName) {
	const tooth = selectedTooth.value
	const exists = props.toothFindings.some((r) => r.tooth_number === tooth && !r.is_custom && r.finding === findingName)
	let next
	if (exists) {
		next = props.toothFindings.filter((r) => !(r.tooth_number === tooth && !r.is_custom && r.finding === findingName))
	} else {
		next = [...props.toothFindings, { tooth_number: tooth, arch: props.arch, finding: findingName, is_custom: 0 }]
	}
	emit('update:toothFindings', next)
}

function addCustom() {
	if (!customText.value.trim() || !selectedTooth.value) return
	emit('update:toothFindings', [
		...props.toothFindings,
		{
			tooth_number: selectedTooth.value,
			arch: props.arch,
			is_custom: 1,
			custom_text: customText.value.trim(),
		},
	])
	customText.value = ''
}

function removeRow(row) {
	emit(
		'update:toothFindings',
		props.toothFindings.filter((r) => r !== row),
	)
}
</script>
