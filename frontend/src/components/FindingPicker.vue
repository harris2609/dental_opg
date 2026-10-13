<template>
	<div>
		<input
			v-model="query"
			:placeholder="`Search ${placeholder}...`"
			class="mb-2 w-full rounded border px-2 py-1 text-xs"
		/>
		<div class="flex max-h-48 flex-wrap gap-1.5 overflow-y-auto">
			<button
				v-for="item in visibleItems"
				:key="item.name"
				class="rounded-full border border-gray-300 px-2.5 py-1 text-xs hover:bg-gray-100"
				@click="emit('pick', item)"
			>
				+ {{ item[labelField] }}
			</button>
			<span v-if="!visibleItems.length" class="text-xs text-gray-400">No findings match "{{ query }}"</span>
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
	items: { type: Array, default: () => [] },
	labelField: { type: String, required: true },
	placeholder: { type: String, default: 'findings' },
})
const emit = defineEmits(['pick'])

const query = ref('')

const visibleItems = computed(() => {
	const q = query.value.trim().toLowerCase()
	const label = (item) => item[props.labelField] || ''
	return props.items
		.filter((item) => !q || label(item).toLowerCase().includes(q))
		.sort((a, b) => label(a).localeCompare(label(b), undefined, { sensitivity: 'base' }))
})
</script>
