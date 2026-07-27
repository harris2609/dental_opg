import { createRouter, createWebHistory } from 'vue-router'
import ReportList from './pages/ReportList.vue'
import NewReport from './pages/NewReport.vue'
import ReportEditor from './pages/ReportEditor.vue'
import Login from './pages/Login.vue'

const routes = [
	{ path: '/dental_opg', name: 'ReportList', component: ReportList },
	{ path: '/dental_opg/new', name: 'NewReport', component: NewReport },
	{ path: '/dental_opg/login', name: 'Login', component: Login },
	{ path: '/dental_opg/:reportId', name: 'ReportEditor', component: ReportEditor, props: true },
]

export default createRouter({
	history: createWebHistory('/'),
	routes,
})
