import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth';
import { ChangeDetectorRef } from '@angular/core';

@Component({
  standalone: true,
  selector: 'app-login',
  templateUrl: './login.html',
  styleUrls: ['./login.css'],
  imports: [FormsModule, CommonModule, HttpClientModule],
})
export class LoginComponent {
  username = '';
  password = '';
  error = '';
  loading = false;

  private cdr = inject(ChangeDetectorRef);
  constructor(
    private router: Router,
    private authService: AuthService,
  ) {}

  // **************
  login() {
    this.error = '';
    this.loading = true;

    this.authService.login(this.username, this.password).subscribe({
      next: (res: any) => {
        console.log('RESPUESTA LOGIN:', res);

        if (res.ok) {
          this.authService.setSession(res.token, res.usuario);
          this.router.navigate(['/home']);
        } else {
          this.error = res.message || 'Error en login';
        }

        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('ERROR LOGIN:', err);

        this.error = err?.error?.message || 'Usuario o contraseña incorrectos';
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }
  // *************
}
