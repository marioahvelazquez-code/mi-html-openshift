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
    path: 'chatbot',
    canActivate: [authGuard],
    loadComponent: () => import('./components/chatbot/chatbot').then((m) => m.ChatComponent),
  },
  {
    path: 'chatbot_m',
    canActivate: [authGuard],
    loadComponent: () => import('./components/chatbot_/chatbot').then((m) => m.ChatbotComponent),
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
  {
    path: 'solicitud-acceso-bd',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./components/solicitud-acceso-bd/solicitud-acceso-bd').then(
        (m) => m.SolicitudAccesoBdComponent,
      ),
  },
  {
    path: 'solicitudes-pendientes',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./components/solicitudes-pendientes/solicitudes-pendientes').then(
        (m) => m.SolicitudesPendientesComponent,
      ),
  },
  {
    path: 'solicitudes-realizadas',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./components/solicitudes-realizadas/solicitudes-realizadas').then(
        (m) => m.SolicitudesRealizadasComponent,
      ),
  },
  {
    path: 'solicitud-especial-bd',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./components/solicitud-especial-bd/solicitud-especial-bd').then(
        (m) => m.SolicitudEspecialBdComponent,
      ),
  },
  {
    path: 'solicitudes-especiales-realizadas',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./components/solicitudes-especiales-realizadas/solicitudes-especiales-realizadas').then(
        (m) => m.SolicitudesEspecialesRealizadasComponent,
      ),
  },
];
