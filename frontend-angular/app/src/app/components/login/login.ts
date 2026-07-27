import { ChangeDetectorRef, Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';

@Component({
  standalone: true,
  selector: 'app-login',
  templateUrl: './login.html',
  styleUrls: ['./login.css'],
  imports: [CommonModule],
})
export class LoginComponent {
  signalValue: 0 | 1 = 0;
  lastReading = 'Esperando integracion con la fuente de datos';
  private pollingId: ReturnType<typeof setInterval> | null = null;

  private readonly http = inject(HttpClient);
  private readonly cdr = inject(ChangeDetectorRef);

  constructor() {
    this.fetchBedStatus();
    this.pollingId = setInterval(() => this.fetchBedStatus(), 1000);
  }

  ngOnDestroy(): void {
    if (this.pollingId) {
      clearInterval(this.pollingId);
      this.pollingId = null;
    }
  }

  private fetchBedStatus(): void {
    this.http.get<any>('/api/catalogos/bed-status/').subscribe({
      next: (response) => {
        const rawValue = String(response?.value ?? '0').trim();
        this.signalValue = rawValue === '1' ? 1 : 0;

        if (response?.updated_at) {
          this.lastReading = `Ultima lectura: ${rawValue} (${response.updated_at})`;
        } else {
          this.lastReading = 'Esperando integracion con la fuente de datos';
        }

        this.cdr.detectChanges();
      },
      error: () => {
        this.lastReading = 'No se pudo consultar el estado actual';
        this.cdr.detectChanges();
      },
    });
  }

  get signalLabel(): string {
    return this.signalValue === 1 ? 'Recibiendo 1' : 'Recibiendo 0';
  }

  get occupancyLabel(): string {
    return this.signalValue === 1 ? 'Cama ocupada' : 'Cama disponible';
  }
}
