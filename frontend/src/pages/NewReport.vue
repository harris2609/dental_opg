<template>
	<div class="mx-auto max-w-md p-6">
		<h1 class="mb-4 text-xl font-semibold">New OPG Report</h1>
		<form class="space-y-3" @submit.prevent="submit">
			<div>
				<label class="mb-1 block text-sm font-medium">Patient Name</label>
				<input v-model="form.patient_name" required class="w-full rounded border px-3 py-1.5" />
			</div>
			<div class="flex gap-3">
				<div class="flex-1">
					<label class="mb-1 block text-sm font-medium">Age</label>
					<input v-model.number="form.age" type="number" class="w-full rounded border px-3 py-1.5" />
				</div>
				<div class="flex-1">
					<label class="mb-1 block text-sm font-medium">Sex</label>
					<select v-model="form.sex" class="w-full rounded border px-3 py-1.5">
						<option value=""></option>
						<option>Male</option>
						<option>Female</option>
						<option>Other</option>
					</select>
				</div>
			</div>
			<div>
				<label class="mb-1 block text-sm font-medium">Registration No</label>
				<input v-model="form.registration_no" class="w-full rounded border px-3 py-1.5" />
			</div>
			<button
				type="submit"
				:disabled="submitting"
				class="w-full rounded bg-gray-900 py-2 text-white hover:bg-gray-700 disabled:opacity-50"
			>
				{{ submitting ? 'Creating...' : 'Create Report' }}
			</button>
		</form>
	</div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createReport } from '../api'

const router = useRouter()
const submitting = ref(false)
const form = reactive({ patient_name: '', age: null, sex: '', registration_no: '' })

async function submit() {
	submitting.value = true
	try {
		const res = await createReport(form)
		router.push(`/dental_opg/${res.report}`)
	} finally {
		submitting.value = false
	}
}
</script>
