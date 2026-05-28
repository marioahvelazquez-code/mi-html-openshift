import { Routes } from '@angular/router';
import { authGuard } from './guards/auth-guard';
import { noAuthGuard } from './guards/no-auth-guard';

export const routes: Routes = [
  {
    path: 'login',
    canActivate: [noAuthGuard],
    loadComponent: () => import('./components/login/login').then((m) => m.LoginComponent),
  },
  {
    path: 'home',
    canActivate: [authGuard], //  protegido
    loadComponent: () => import('./components/home/home').then((m) => m.Home),
  },
  {
    path: 'bitacora',
    canActivate: [authGuard], //  protegido
    loadComponent: () => import('./components/bitacora/bitacora').then((m) => m.BitacoraComponent),
  },
  {
    path: '',
    redirectTo: 'login',
    pathMatch: 'full',
  },

  {
    path: 'excel',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./components/carga-excel/carga-excel').then((m) => m.CargaExcelComponent),
  },
  {
    path: 'ficha-hospitalaria',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./components/ficha-hospitalaria/ficha-hospitalaria').then((m) => m.FichaHospitalaria),
  },
  {
    // Mario: nueva ruta para revisar fichas.
    path: 'revisar-fichas',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./components/revisar-ficha/revisar-ficha').then((m) => m.RevisarFichaComponent),
  },
];
