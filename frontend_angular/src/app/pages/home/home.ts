import { Component } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  selector: 'app-home',
  standalone: true,
  templateUrl: './home.html',
  styleUrl: './home.css'
})
export class HomeComponent {
  private readonly usuarioStorageKey = 'usuarioAutenticado';

  constructor(private readonly router: Router) {}

  irARevisarFicha(): void {
    void this.router.navigate(['/revisar-ficha']);
  }

  irACargaExcel(): void {
    void this.router.navigate(['/carga-excel']);
  }

  cerrarSesion(): void {
    localStorage.removeItem(this.usuarioStorageKey);
    void this.router.navigate(['/login']);
  }
}
