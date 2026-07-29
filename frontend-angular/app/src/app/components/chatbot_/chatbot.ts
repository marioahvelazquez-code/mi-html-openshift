import { Component } from '@angular/core';
import { ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { LucideAngularModule } from 'lucide-angular';
import { firstValueFrom, timeout } from 'rxjs';

@Component({
  standalone: true,
  selector: 'app-chatbot',
  templateUrl: './chatbot.html',
  styleUrl: './chatbot.css',
  imports: [CommonModule, FormsModule, LucideAngularModule],
})
export class ChatbotComponent {
  pregunta = '';
  respuesta = '';
  loading = false;
  error = '';

  constructor(
    private http: HttpClient,
    private cdr: ChangeDetectorRef,
  ) {}

  private construirTextoRespuesta(resp: any): string {
    const respuestaTexto = String(resp?.respuesta || resp?.mensaje || '').trim();
    if (respuestaTexto) return respuestaTexto;

    const datos = Array.isArray(resp?.datos) ? resp.datos : [];
    if (datos.length > 0) {
      return JSON.stringify(datos, null, 2);
    }

    const estadoHospital = String(resp?.hospital?.status || '').trim();
    const estadoVariable = String(resp?.variable?.status || '').trim();
    if (estadoHospital === 'ganador_claro' && estadoVariable !== 'ganador_claro') {
      return 'Identifiqué la unidad, pero me falta la variable a consultar. Ejemplo: camas censables en HGZ 30.';
    }
    if (estadoVariable === 'ganador_claro' && estadoHospital !== 'ganador_claro') {
      return 'Identifiqué la variable, pero me falta la unidad o ámbito. Ejemplo: camas censables en HGZ 30.';
    }

    const estado = String(resp?.status || '').trim();
    if (estado) {
      return `Estatus: ${estado}. No se encontraron datos para la consulta.`;
    }

    return 'No encontré una respuesta directa. Intenta con una consulta más específica, por ejemplo: camas censables en HGZ 30.';
  }

  async enviarPregunta() {
    const preguntaLimpia = this.pregunta.trim();
    if (!preguntaLimpia || this.loading) {
      return;
    }

    this.loading = true;
    this.error = '';
    this.respuesta = '';
    this.cdr.detectChanges();
    console.log('[Chatbot] Enviando pregunta:', preguntaLimpia);

    const safetyTimer = setTimeout(() => {
      if (this.loading) {
        this.loading = false;
        if (!this.error) {
          this.error = 'La consulta no finalizó correctamente. Intenta de nuevo.';
        }
        this.cdr.detectChanges();
        console.warn('[Chatbot] Safety timer liberó estado de carga');
      }
    }, 65000);

    try {
      const resp = await firstValueFrom(
        this.http
          .post<any>('/api/catalogos/chatbot-query/', { pregunta: preguntaLimpia })
          .pipe(timeout(60000)),
      );

      console.log('[Chatbot] Respuesta recibida:', resp);

      const textoRespuesta = this.construirTextoRespuesta(resp);
      this.respuesta = textoRespuesta;
      if (!this.respuesta) {
        this.error = String(resp?.error || 'No se recibió una respuesta del asistente.');
      }
    } catch (err: any) {
      console.error('[Chatbot] Error al consultar:', err);
      if (err?.name === 'TimeoutError') {
        this.error = 'El chatbot tardó demasiado en responder. Intenta de nuevo.';
      } else {
        this.error =
          err?.error?.error || err?.error?.detail || 'Ocurrió un error al consultar el chatbot.';
      }
    } finally {
      clearTimeout(safetyTimer);
      this.loading = false;
      this.cdr.detectChanges();
      console.log('[Chatbot] Finalizó consulta');
    }
  }
}
