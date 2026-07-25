<template>
	<div v-if="loading" class="p-6 text-sm text-gray-500">Loading report...</div>
	<div v-else class="flex h-screen flex-col">
		<div class="flex flex-wrap items-center gap-3 border-b bg-white px-4 py-2">
			<router-link to="/dental_opg" class="text-sm text-gray-500 hover:underline">&larr; Reports</router-link>
			<h1 class="text-sm font-semibold">{{ report.name }}</h1>
			<span class="rounded bg-yellow-100 px-2 py-0.5 text-xs text-yellow-700">{{ report.status }}</span>
			<div class="ml-auto flex gap-2">
				<button class="actionbtn" :disabled="saving" @click="save">{{ saving ? 'Saving...' : 'Save Findings' }}</button>
				<button class="actionbtn" :disabled="generating" @click="onGenerate">
					{{ generating ? 'Generating...' : 'Generate Report' }}
				</button>
				<a class="actionbtn inline-block" :href="printUrl" target="_blank">Print</a>
			</div>
		</div>

		<div class="grid flex-1 gap-4 overflow-hidden p-4 md:grid-cols-2">
			<div class="sticky top-0 h-[45vh] overflow-hidden rounded border md:h-full">
				<ImageViewer :image-url="imageSrc" v-model:annotations="annotations" @upload="onUpload" />
			</div>

			<div class="space-y-4 overflow-y-auto pb-8 md:h-full">
				<div class="rounded border bg-white p-4">
					<h2 class="mb-2 text-sm font-semibold text-gray-800">Report Details</h2>
					<div class="grid grid-cols-2 gap-3 text-xs">
						<div>
							<label class="mb-1 block font-medium">Patient</label>
							<div class="rounded border bg-gray-50 px-2 py-1">{{ report.patient }}</div>
						</div>
						<div>
							<label class="mb-1 block font-medium">Report Date</label>
							<input v-model="report.report_date" type="date" class="w-full rounded border px-2 py-1" />
						</div>
						<div>
							<label class="mb-1 block font-medium">Referred By</label>
							<input v-model="report.referred_by" class="w-full rounded border px-2 py-1" />
						</div>
						<div>
							<label class="mb-1 block font-medium">Status</label>
							<select v-model="report.status" class="w-full rounded border px-2 py-1">
								<option>Draft</option>
								<option>Final</option>
							</select>
						</div>
						<div class="col-span-2">
							<label class="mb-1 block font-medium">Clinical Diagnosis</label>
							<textarea v-model="report.clinical_diagnosis" rows="2" class="w-full rounded border px-2 py-1"></textarea>
						</div>
						<div>
							<label class="mb-1 block font-medium">Reported By</label>
							<input v-model="report.reported_by" class="w-full rounded border px-2 py-1" />
						</div>
						<div>
							<label class="mb-1 block font-medium">Verified By</label>
							<input v-model="report.verified_by" class="w-full rounded border px-2 py-1" />
						</div>
					</div>
				</div>

				<template v-for="section in setup.section_order" :key="section">
					<SectionCard
						:section="section"
						:standard-findings="setup.standard_findings_by_section[section] || []"
						:rows="rowsForSection(section)"
						@update:rows="(rows) => updateSectionRows(section, rows)"
					/>
					<div v-if="section === 'Maxillary Arch' || section === 'Mandibular Arch'" class="rounded border bg-white p-4">
						<h3 class="mb-2 text-sm font-semibold text-gray-800">
							{{ section === 'Maxillary Arch' ? 'Upper' : 'Lower' }} Tooth Chart (FDI)
						</h3>
						<ToothChart
							:arch="section === 'Maxillary Arch' ? 'Maxillary' : 'Mandibular'"
							:tooth-findings="toothFindingsForArch(section === 'Maxillary Arch' ? 'Maxillary' : 'Mandibular')"
							:tooth-findings-master="setup.tooth_findings"
							@update:tooth-findings="(rows) => updateToothFindings(section === 'Maxillary Arch' ? 'Maxillary' : 'Mandibular', rows)"
						/>
					</div>
				</template>

				<IncidentalFindingsCard :report-name="report.name" />

				<div v-if="report.generated_report_text" class="rounded border bg-white p-4">
					<h2 class="mb-2 text-sm font-semibold text-gray-800">Generated Report Text</h2>
					<pre class="whitespace-pre-wrap text-xs text-gray-700">{{ report.generated_report_text }}</pre>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import ImageViewer from '../components/ImageViewer.vue'
import ToothChart from '../components/ToothChart.vue'
import SectionCard from '../components/SectionCard.vue'
import IncidentalFindingsCard from '../components/IncidentalFindingsCard.vue'
import {
	getReport,
	getSetupData,
	saveReportDetails,
	saveFindings,
	saveAnnotations,
	generateReport,
	uploadImage,
} from '../api'

const props = defineProps({ reportId: { type: String, required: true } })

const loading = ref(true)
const saving = ref(false)
const generating = ref(false)
const report = reactive({})
const setup = reactive({ section_order: [], standard_findings_by_section: {}, tooth_findings: [] })
const sectionFindings = ref([])
const toothFindings = ref([])
const annotations = ref([])

const imageSrc = computed(() => report.opg_image || '')
const printUrl = computed(
	() => `/printview?doctype=OPG%20Report&name=${encodeURIComponent(report.name || '')}&format=OPG%20Report`,
)

onMounted(async () => {
	const [reportData, setupData] = await Promise.all([getReport(props.reportId), getSetupData()])
	Object.assign(report, reportData)
	Object.assign(setup, setupData)
	sectionFindings.value = reportData.section_findings || []
	toothFindings.value = reportData.tooth_findings || []
	annotations.value = reportData.annotations || []
	loading.value = false
})

function rowsForSection(section) {
	return sectionFindings.value.filter((r) => r.section === section)
}
function updateSectionRows(section, rows) {
	sectionFindings.value = [...sectionFindings.value.filter((r) => r.section !== section), ...rows]
}

function toothFindingsForArch(arch) {
	return toothFindings.value.filter((r) => r.arch === arch)
}
function updateToothFindings(arch, rows) {
	toothFindings.value = [...toothFindings.value.filter((r) => r.arch !== arch), ...rows]
}

async function save() {
	saving.value = true
	try {
		await saveReportDetails(report.name, {
			report_date: report.report_date,
			referred_by: report.referred_by,
			clinical_diagnosis: report.clinical_diagnosis,
			status: report.status,
			reported_by: report.reported_by,
			verified_by: report.verified_by,
		})
		await saveFindings(report.name, sectionFindings.value, toothFindings.value)
		await saveAnnotations(report.name, annotations.value)
	} finally {
		saving.value = false
	}
}

async function onGenerate() {
	generating.value = true
	try {
		await save()
		report.generated_report_text = await generateReport(report.name)
	} finally {
		generating.value = false
	}
}

async function onUpload(file) {
	report.opg_image = await uploadImage(file, report.name)
}
</script>

<style scoped>
.actionbtn {
	@apply rounded bg-gray-900 px-3 py-1.5 text-xs text-white hover:bg-gray-700 disabled:opacity-50;
}
</style>
