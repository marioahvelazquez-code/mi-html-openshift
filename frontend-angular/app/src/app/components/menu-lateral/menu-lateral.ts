import { Component, Input, Output, EventEmitter, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LucideAngularModule } from 'lucide-angular';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth';

export const VISTAS = {
  MENU: 'menu',
  INICIO: 'inicio',
  CHATBOT: 'chatbot',
  EXCEL: 'excel',
  FICHAHOSPITALARIA: 'FichaHospitalaria',
  CONSULTAS_SQL: 'consultassql',
  REVISAPPTX: 'RevisaPPTx',
  BITACORA: 'bitacora',
  SOLICITUDACCESOBD: 'solicitud-acceso-bd',
  SOLICITUDESPENDIENTES: 'solicitudes-pendientes',
  SOLICITUDESREALIZADAS: 'solicitudes-realizadas',
} as const;

export type VistaActiva = (typeof VISTAS)[keyof typeof VISTAS];

@Component({
  selector: 'app-menu-lateral',
  standalone: true,
  templateUrl: './menu-lateral.html',
  imports: [CommonModule, LucideAngularModule],
})
export class MenuLateralComponent implements OnChanges {
  @Input() show: boolean = false;

  @Output() hide = new EventEmitter<void>();
  @Output() openCargaMenu = new EventEmitter<VistaActiva>();

  VISTAS = VISTAS;
  accesoRestringidoSolicitud = false;
  esAdminSolicitudes = false;
  esChatbotUsuario = false;

  constructor(
    private router: Router,
    private authService: AuthService,
  ) {
    this.accesoRestringidoSolicitud = this.authService.hasRestrictedSolicitudAccess();
    this.esAdminSolicitudes = this.authService.isAdminSolicitudes();
    this.esChatbotUsuario = this.authService.isChatbotUsuario();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['show']) {
      this.accesoRestringidoSolicitud = this.authService.hasRestrictedSolicitudAccess();
      this.esAdminSolicitudes = this.authService.isAdminSolicitudes();
      this.esChatbotUsuario = this.authService.isChatbotUsuario();
    }
  }

  seleccionar(vista: string) {
    if (
      this.accesoRestringidoSolicitud &&
      vista !== 'solicitud-acceso-bd' &&
      vista !== 'solicitudes-realizadas'
    ) {
      this.router.navigate(['/solicitud-acceso-bd']);
      this.hide.emit();
      return;
    }

    if (vista === 'chatbot') {
      this.router.navigate(['/chatbot']);
    }
    if (vista === 'excel') {
      this.router.navigate(['/excel']);
    }
    if (vista === 'bitacora') {
      this.router.navigate(['/bitacora']);
    }
    if (vista === 'FichaHospitalaria') {
      this.router.navigate(['/ficha-hospitalaria']);
    }
    // Mario: navegación habilitada para la nueva página de revisar fichas.
    if (vista === 'RevisaPPTx') {
      this.router.navigate(['/revisar-fichas']);
    }
    if (vista === 'inicio') {
      this.router.navigate(['/home']);
    }
    if (vista === 'solicitud-acceso-bd') {
      this.router.navigate(['/solicitud-acceso-bd']);
    }
    if (vista === 'solicitudes-pendientes') {
      this.router.navigate(['/solicitudes-pendientes']);
    }
    if (vista === 'solicitudes-realizadas') {
      this.router.navigate(['/solicitudes-realizadas']);
    }
    this.hide.emit(); // cerrar menú
  }
  cerrarSesion() {
    this.hide.emit();
    this.authService.logout();
  }
}
