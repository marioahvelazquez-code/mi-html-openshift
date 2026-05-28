import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private apiUrl = '/api/catalogos';
  private readonly INACTIVITY_LIMIT = 30 * 60 * 1000; // 30 min de inactividad

  constructor(
    private http: HttpClient,
    private router: Router,
  ) {}

  login(username: string, password: string) {
    // return this.http.post<any>(`${this.apiUrl}/login/`, { username, password });
    // return this.http.get<any[]>(`${this.apiUrl}/areas/`);
    return this.http.post('/api/catalogos/login/', { usuario: username, contrasena: password });
  }

  setSession(token: string, usuario: string) {
    sessionStorage.setItem('token', token);
    sessionStorage.setItem('usuario', usuario);
    this.updateActivity(); // Iniciar tracking de actividad
  }

  // Actualizar timestamp de última actividad
  updateActivity() {
    sessionStorage.setItem('lastActivity', Date.now().toString());
  }

  // Obtener tiempo de inactividad actual
  getInactivityTime(): number {
    const lastActivity = sessionStorage.getItem('lastActivity');
    if (!lastActivity) return this.INACTIVITY_LIMIT;
    return Date.now() - parseInt(lastActivity);
  }

  logout() {
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('usuario');
    sessionStorage.removeItem('lastActivity');
    this.router.navigate(['/login']);
  }

  isLoggedIn(): boolean {
    const token = sessionStorage.getItem('token');
    if (!token) return false;

    // Verificar inactividad (no tiempo del token)
    const lastActivity = sessionStorage.getItem('lastActivity');
    if (lastActivity) {
      const inactiveTime = Date.now() - parseInt(lastActivity);
      if (inactiveTime > this.INACTIVITY_LIMIT) {
        this.logout();
        return false;
      }
      // Actualizar actividad en cada verificación
      this.updateActivity();
    }

    return true;
  }
}
