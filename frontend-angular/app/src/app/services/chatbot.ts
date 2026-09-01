import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ChatbotRequest {
  pregunta: string;
}

export interface ChatbotResponse {
  respuesta?: string;
  error?: string;
}

export interface FechaCorteIfuResponse {
  anio: number | null;
  mes: number | null;
  mes_nombre: string | null;
  fecha_corte: string | null;
}

@Injectable({ providedIn: 'root' })
export class ChatbotService {
  private apiUrl = '/api/catalogos';

  constructor(private http: HttpClient) {}

  preguntar(pregunta: string): Observable<ChatbotResponse> {
    const payload: ChatbotRequest = { pregunta };
    return this.http.post<ChatbotResponse>(`${this.apiUrl}/chatbot/`, payload);
  }

  obtenerFechaCorteIfu(): Observable<FechaCorteIfuResponse> {
    return this.http.get<FechaCorteIfuResponse>(
      `${this.apiUrl}/fecha-corte-ifu/`,
    );
  }
}
