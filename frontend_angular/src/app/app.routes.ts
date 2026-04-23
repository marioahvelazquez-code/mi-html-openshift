import { Routes } from '@angular/router';
import { IniciaSesion } from './pages/login/login';
import { CambiarPasswordPrimerIngreso } from './pages/cambiar_password_primer_ingreso/cambiar-password-primer-ingreso';
import { HomeComponent } from './pages/home/home';
// importación de CargaExcelComponent eliminada
import { RevisarFichaComponent } from './pages/revisar_ficha/revisar-ficha';

export const routes: Routes = [
	{ path: 'login', component: IniciaSesion },
	{ path: 'cambiar-password-primer-ingreso', component: CambiarPasswordPrimerIngreso },
	{ path: 'home', component: HomeComponent },
	// ruta de carga-excel eliminada
	{ path: 'revisar-ficha', component: RevisarFichaComponent },
	{ path: '', pathMatch: 'full', redirectTo: 'login' },
	{ path: '**', redirectTo: 'home' }
];
