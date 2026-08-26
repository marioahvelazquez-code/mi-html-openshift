import { Component, Input, Output, EventEmitter, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LucideAngularModule } from 'lucide-angular';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth';

export const VISTAS = {
  MENU: 'menu',
  INICIO: 'inicio',
  CHAT: 'chat',
  CHATBOT_M: 'chatbot_m',
  FICHA_PRESIDENCIAL: 'ficha-presidencial',
  EXCEL: 'excel',
  FICHAHOSPITALARIA: 'FichaHospitalaria',
  CONSULTAS_SQL: 'consultassql',
  REVISAPPTX: 'RevisaPPTx',
  BITACORA: 'bitacora',
  SOLICITUDACCESOBD: 'solicitud-acceso-bd',
  SOLICITUDESPENDIENTES: 'solicitudes-pendientes',
  SOLICITUDESREALIZADAS: 'solicitudes-realizadas',
  SOLICITUDESPECIALBD: 'solicitud-especial-bd',
  SOLICITUDESESPECIALESREALIZADAS: 'solicitudes-especiales-realizadas',
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
  mostrarChatbotV2 = false;
  submenuCambioBdAbierto = false;
  submenuEspecialBdAbierto = false;

  constructor(
    private router: Router,
    private authService: AuthService,
  ) {
    this.accesoRestringidoSolicitud = this.authService.hasRestrictedSolicitudAccess();
    this.esAdminSolicitudes = this.authService.isAdminSolicitudes();
    this.esChatbotUsuario = this.authService.isChatbotUsuario();
  }

  toggleSubmenuCambioBd(): void {
    this.submenuCambioBdAbierto = !this.submenuCambioBdAbierto;
  }

  toggleSubmenuEspecialBd(): void {
    this.submenuEspecialBdAbierto = !this.submenuEspecialBdAbierto;
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
      vista !== 'solicitudes-realizadas' &&
      vista !== 'solicitud-especial-bd' &&
      vista !== 'solicitudes-especiales-realizadas'
    ) {
      this.router.navigate(['/solicitud-acceso-bd']);
      this.hide.emit();
      return;
    }

    if (vista === 'chat') {
      this.router.navigate(['/chatbot']);
    }
    if (vista === 'chatbot_m') {
      this.router.navigate(['/chatbot_m']);
    }
    if (vista === 'ficha-presidencial') {
      this.router.navigate(['/ficha-presidencial']);
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
    if (vista === 'solicitud-especial-bd') {
      this.router.navigate(['/solicitud-especial-bd']);
    }
    if (vista === 'solicitudes-especiales-realizadas') {
      this.router.navigate(['/solicitudes-especiales-realizadas']);
    }
    this.submenuCambioBdAbierto = false;
    this.submenuEspecialBdAbierto = false;
    this.hide.emit(); // cerrar menú
  }
  cerrarSesion() {
    this.hide.emit();
    this.authService.logout();
  }
}
