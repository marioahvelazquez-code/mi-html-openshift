import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  selector: 'app-menu-lateral',
  standalone: true,
  templateUrl: './menu-lateral.component.html',
  styleUrl: './menu-lateral.component.css'
})
export class MenuLateralComponent {
  private readonly usuarioStorageKey = 'usuarioAutenticado';
  @Input() abierto = false;
  @Output() cerrar = new EventEmitter<void>();

  constructor(private readonly router: Router) {}

  cerrarMenu(): void {
    this.cerrar.emit();
  }

  irA(ruta: string): void {
    this.cerrarMenu();
    if (ruta === '/login') {
      localStorage.removeItem(this.usuarioStorageKey);
    }
    void this.router.navigate([ruta]);
  }
}
