import { Component, signal } from '@angular/core';
import { RouterOutlet, Router, NavigationEnd } from '@angular/router';
import { CommonModule } from '@angular/common';

import { FooterComponent } from './components/footer/footer';
import { HeaderComponent } from './components/header/header';
import { MenuLateralComponent } from './components/menu-lateral/menu-lateral';
import { filter } from 'rxjs';
import { AuthService } from './services/auth';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, HeaderComponent, MenuLateralComponent, FooterComponent, CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  protected readonly title = signal('Probando');
  private inactivityTimer: any;

  private activityHandler = () => this.resetTimer();

  datoInfor = signal('Probando el dato de información');
  datoInfor1 = 'Hola';

  showMenu = false;
  isHome = signal(true);

  constructor(
    private router: Router,
    private auth: AuthService,
  ) {
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event: any) => {
        this.isHome.set(event.url === '/');

        if (event.url === '/login' || event.url === '/') {
          this.showMenu = false;
        }
      });
    this.initInactivityTimer();
  }

  toggleMenu() {
    this.showMenu = !this.showMenu;
  }

  cerrarMenu() {
    this.showMenu = false;
  }

  cambiarVista(vista: any) {
    console.log('Vista seleccionada:', vista);
  }

  initInactivityTimer() {
    const events = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'];

    events.forEach((event) => {
      window.addEventListener(event, this.activityHandler);
    });

    this.resetTimer();
  }

  resetTimer() {
    clearTimeout(this.inactivityTimer);

    this.inactivityTimer = setTimeout(
      () => {
        console.log('Sesión expirada por inactividad');
        this.auth.logout();
      },
      30 * 60 * 1000,
    ); // 30 min

    // Actualizar actividad en el servicio de auth
    this.auth.updateActivity();
  }

  ngOnDestroy() {
    const events = ['mousemove', 'keydown', 'click'];

    events.forEach((event) => {
      window.removeEventListener(event, this.activityHandler);
    });
  }
  isLogin(): boolean {
    return this.router.url === '/login';
  }
}
